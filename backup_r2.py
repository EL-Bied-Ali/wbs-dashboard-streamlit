from __future__ import annotations

import json
import logging
import os
import zipfile
import shutil
import sqlite3
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

import streamlit as st
from minio import Minio
from minio.error import S3Error

BACKUP_STATE_PATH = Path("artifacts") / "backup_state.json"
BACKUP_PREFIX = "backups/"
DEFAULT_KEEP = 14
GUARD_TTL_HOURS = 6  # minimum interval between guard backups
RESTORE_TTL_HOURS = 6  # minimum interval between auto-restores

_LOGGED_EVENTS: set[str] = set()
BACKUP_LOGGER = logging.getLogger("backup_r2")


def _ensure_logger() -> None:
    if not BACKUP_LOGGER.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s [backup_r2] %(levelname)s: %(message)s")
        )
        BACKUP_LOGGER.addHandler(handler)
    BACKUP_LOGGER.setLevel(logging.INFO)


def _safe_unlink(path: Path, *, retries: int = 8, base_delay: float = 0.15) -> None:
    for i in range(retries):
        try:
            path.unlink(missing_ok=True)
            return
        except PermissionError:
            time.sleep(base_delay * (i + 1))
        except FileNotFoundError:
            return
        except Exception:
            return


def _log_once(key: str, level: int, message: str) -> None:
    if key in _LOGGED_EVENTS:
        return
    _ensure_logger()
    BACKUP_LOGGER.log(level, message)
    _LOGGED_EVENTS.add(key)


def _log(level: int, message: str) -> None:
    _ensure_logger()
    BACKUP_LOGGER.log(level, message)


def _get_secret(key: str) -> str:
    value = os.environ.get(key, "")
    if not value:
        try:
            value = st.secrets.get(key, "")
        except Exception:
            value = ""
    return value


def _get_int_secret(key: str, default: int) -> int:
    raw = _get_secret(key)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def get_backup_keep() -> int:
    value = _get_int_secret("R2_BACKUP_KEEP", DEFAULT_KEEP)
    return value if value > 0 else DEFAULT_KEEP


def _get_guard_ttl_hours() -> int:
    value = _get_int_secret("R2_BACKUP_GUARD_TTL_HOURS", GUARD_TTL_HOURS)
    return value if value > 0 else GUARD_TTL_HOURS


def _get_restore_ttl_hours() -> int:
    value = _get_int_secret("R2_BACKUP_RESTORE_TTL_HOURS", RESTORE_TTL_HOURS)
    return value if value > 0 else RESTORE_TTL_HOURS


def get_backup_stats() -> dict[str, Any] | None:
    """
    Return backup stats pulled from R2 and local state.

    Keys:
    - configured: bool
    - last_backup_at: str | None
    - last_backup_key: str | None
    - last_backup_size_bytes: int | None
    - total_backups_count: int
    - total_backups_size_bytes: int
    - keep_limit: int
    - last_restore_at: str | None
    - last_restore_key: str | None
    - last_restore_status: str | None
    - error: str (optional)
    """
    client, bucket = _get_backup_client()
    if not client or not bucket:
        state = _load_state()
        return {
            "configured": False,
            "error": "R2 backup not configured",
            "last_backup_at": None,
            "last_backup_key": None,
            "last_backup_size_bytes": None,
            "total_backups_count": 0,
            "total_backups_size_bytes": 0,
            "keep_limit": get_backup_keep(),
            "last_restore_at": state.get("last_restore_at"),
            "last_restore_key": state.get("last_restore_key"),
            "last_restore_status": state.get("last_restore_status"),
        }

    state = _load_state()
    last_key = state.get("last_backup_key")
    last_at = state.get("last_backup_at")

    total_size = 0
    total_count = 0
    last_size = None

    try:
        objects = client.list_objects(bucket, prefix=BACKUP_PREFIX, recursive=True)
        for obj in objects:
            if not obj.object_name.endswith(".zip"):
                continue
            size = getattr(obj, "size", 0) or 0
            total_size += size
            total_count += 1
            if last_key and obj.object_name == last_key:
                last_size = size
    except Exception as err:
        _log(logging.WARNING, f"Failed to list backups: {err}")
        return {
            "configured": False,
            "error": f"Failed to list backups: {err}",
            "last_backup_at": last_at,
            "last_backup_key": last_key,
            "last_backup_size_bytes": last_size,
            "total_backups_count": total_count,
            "total_backups_size_bytes": total_size,
            "keep_limit": get_backup_keep(),
            "last_restore_at": state.get("last_restore_at"),
            "last_restore_key": state.get("last_restore_key"),
            "last_restore_status": state.get("last_restore_status"),
        }

    return {
        "configured": True,
        "last_backup_at": last_at,
        "last_backup_key": last_key,
        "last_backup_size_bytes": last_size,
        "total_backups_count": total_count,
        "total_backups_size_bytes": total_size,
        "keep_limit": get_backup_keep(),
        "last_restore_at": state.get("last_restore_at"),
        "last_restore_key": state.get("last_restore_key"),
        "last_restore_status": state.get("last_restore_status"),
    }


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_state() -> dict[str, Any]:
    if not BACKUP_STATE_PATH.exists():
        return {}
    try:
        return json.loads(BACKUP_STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(state: dict[str, Any]) -> None:
    BACKUP_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BACKUP_STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def _endpoint_from_account(account_id: str, override: str | None) -> str:
    if override:
        cleaned = override.strip().replace("https://", "").replace("http://", "")
        return cleaned.rstrip("/")
    return f"{account_id}.r2.cloudflarestorage.com"


def _get_backup_client() -> tuple[Minio | None, str | None]:
    account_id = _get_secret("R2_ACCOUNT_ID")
    access_key = _get_secret("R2_ACCESS_KEY_ID")
    secret_key = _get_secret("R2_SECRET_ACCESS_KEY")
    bucket = _get_secret("R2_BUCKET")
    endpoint_override = _get_secret("R2_ENDPOINT")
    missing = [
        key
        for key, value in [
            ("R2_ACCOUNT_ID", account_id),
            ("R2_ACCESS_KEY_ID", access_key),
            ("R2_SECRET_ACCESS_KEY", secret_key),
            ("R2_BUCKET", bucket),
        ]
        if not value
    ]
    if missing:
        _log_once("backup_missing_config", logging.WARNING, f"Backup config missing: {missing}")
        return None, None
    endpoint = _endpoint_from_account(account_id, endpoint_override or None)
    client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=True)
    return client, bucket


def _iter_backup_files() -> Iterable[Path]:
    artifacts = Path("artifacts")
    files = [
        artifacts / "projects.json",
        artifacts / "billing.sqlite",
        artifacts / "auth_sessions.json",
    ]
    for path in files:
        if path.exists():
            yield path
    projects_dir = artifacts / "projects"
    if projects_dir.exists():
        for path in projects_dir.rglob("*"):
            if path.is_file():
                yield path


def _create_backup_zip(zip_path: Path) -> None:
    artifacts = Path("artifacts")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in _iter_backup_files():
            try:
                arcname = path.relative_to(artifacts)
            except ValueError:
                arcname = path.name
            zf.write(path, arcname.as_posix())


def _prune_old_backups(client: Minio, bucket: str, keep: int) -> None:
    objects = list(client.list_objects(bucket, prefix=BACKUP_PREFIX, recursive=True))
    objects = [obj for obj in objects if obj.object_name.endswith(".zip")]
    objects.sort(key=lambda obj: obj.object_name, reverse=True)
    if len(objects) <= keep:
        return
    for obj in objects[keep:]:
        client.remove_object(bucket, obj.object_name)
        _log(logging.INFO, f"Removed old backup {obj.object_name}")


def _guard_recently_ran() -> bool:
    state = _load_state()
    last_raw = state.get("last_guard_backup_at")
    last = _parse_iso(last_raw if isinstance(last_raw, str) else None)
    if not last:
        return False
    ttl_hours = _get_guard_ttl_hours()
    return (datetime.now(timezone.utc) - last) < timedelta(hours=ttl_hours)


def _restore_recently_ran() -> bool:
    state = _load_state()
    last_raw = state.get("last_restore_at")
    last = _parse_iso(last_raw if isinstance(last_raw, str) else None)
    if not last:
        return False
    ttl_hours = _get_restore_ttl_hours()
    return (datetime.now(timezone.utc) - last) < timedelta(hours=ttl_hours)


def _list_backup_objects(client: Minio, bucket: str) -> list:
    objs = list(client.list_objects(bucket, prefix=BACKUP_PREFIX, recursive=True))
    return [o for o in objs if o.object_name.endswith(".zip")]


def list_backups(limit: int = 50) -> list[dict[str, Any]]:
    """
    Return a list of recent backups with metadata.
    """
    client, bucket = _get_backup_client()
    if not client or not bucket:
        return []
    objs = _list_backup_objects(client, bucket)
    objs.sort(key=lambda o: o.object_name, reverse=True)
    result: list[dict[str, Any]] = []
    for obj in objs[:limit]:
        result.append(
            {
                "key": obj.object_name,
                "size": getattr(obj, "size", 0),
                "last_modified": getattr(obj, "last_modified", None),
            }
        )
    return result


def guard_backup_on_data_loss() -> tuple[bool, str]:
    """
    Detect missing/empty critical data files and trigger an immediate backup.
    Returns (ok, message).
    - ok=True means the guard ran (even if files were missing) and attempted upload.
    - ok=False with message for why it skipped (e.g., configured off).
    """
    critical = [
        Path("artifacts") / "projects.json",
        Path("artifacts") / "billing.sqlite",
    ]
    issues: list[str] = []
    for path in critical:
        if not path.exists():
            issues.append(f"{path} missing")
        else:
            try:
                if path.stat().st_size <= 0:
                    issues.append(f"{path} empty")
            except OSError:
                issues.append(f"{path} unreadable")

    if not issues:
        return False, "Backup guard skipped: no data-loss indicators."

    client, bucket = _get_backup_client()
    if not client or not bucket:
        return False, "Backup guard skipped: R2 not configured."
    if _guard_recently_ran():
        return False, "Backup guard skipped: recent guard already ran."

    now = datetime.now(timezone.utc)
    key = f"{BACKUP_PREFIX}guard-{now.strftime('%Y%m%dT%H%M%SZ')}.zip"
    temp_dir = Path(tempfile.gettempdir()) / "chronoplan_backups_tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"{key.replace('/', '_')}"
    try:
        _create_backup_zip(temp_path)
        if not client.bucket_exists(bucket):
            return False, f"Bucket not found: {bucket}"
        client.fput_object(
            bucket,
            key,
            str(temp_path),
            content_type="application/zip",
        )
        _prune_old_backups(client, bucket, get_backup_keep())
        state = _load_state()
        state["last_backup_at"] = state.get("last_backup_at") or _iso(now)
        state["last_backup_key"] = state.get("last_backup_key") or key
        state["last_guard_backup_at"] = _iso(now)
        state["last_guard_issues"] = issues
        state["last_backup_reason"] = "data_guard"
        _save_state(state)
        _log(logging.WARNING, f"Backup guard triggered due to: {issues}")
        return True, f"Backup guard uploaded: {key}"
    except S3Error as err:
        _log(logging.ERROR, f"Backup guard failed: {err}")
        return False, f"Backup guard failed: {err}"
    except Exception as err:
        _log(logging.ERROR, f"Backup guard failed: {err}")
        return False, f"Backup guard failed: {err}"
    finally:
        if temp_path.exists():
            _safe_unlink(temp_path)


def run_backup_now(reason: str = "manual") -> tuple[bool, str]:
    client, bucket = _get_backup_client()
    if not client or not bucket:
        return False, "Missing R2 configuration."
    now = datetime.now(timezone.utc)
    key = f"{BACKUP_PREFIX}backup-{now.strftime('%Y%m%dT%H%M%SZ')}.zip"
    temp_dir = Path(tempfile.gettempdir()) / "chronoplan_backups_tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"{key.replace('/', '_')}"
    try:
        _create_backup_zip(temp_path)
        if not client.bucket_exists(bucket):
            return False, f"Bucket not found: {bucket}"
        client.fput_object(
            bucket,
            key,
            str(temp_path),
            content_type="application/zip",
        )
        _prune_old_backups(client, bucket, get_backup_keep())
        state = _load_state()
        state["last_backup_at"] = _iso(now)
        state["last_backup_key"] = key
        state["last_backup_reason"] = reason
        _save_state(state)
        _log(logging.INFO, f"Backup uploaded: {key}")
        return True, f"Backup uploaded: {key}"
    except S3Error as err:
        _log(logging.ERROR, f"Backup failed: {err}")
        return False, f"Backup failed: {err}"
    except Exception as err:
        _log(logging.ERROR, f"Backup failed: {err}")
        return False, f"Backup failed: {err}"
    finally:
        if temp_path.exists():
            _safe_unlink(temp_path)


def _validate_restored_artifacts(temp_dir: Path) -> tuple[bool, list[str]]:
    issues: list[str] = []
    pj = temp_dir / "projects.json"
    db = temp_dir / "billing.sqlite"
    if not pj.exists():
        issues.append("projects.json missing in backup")
    else:
        try:
            data = json.loads(pj.read_text(encoding="utf-8"))
            if not data:
                issues.append("projects.json empty")
        except Exception as err:
            issues.append(f"projects.json parse error: {err}")
    if not db.exists():
        issues.append("billing.sqlite missing in backup")
    else:
        try:
            conn = sqlite3.connect(db)
            check = conn.execute("PRAGMA integrity_check;").fetchone()
            if not check or check[0] != "ok":
                issues.append("billing.sqlite integrity_check failed")
            conn.close()
        except Exception as err:
            issues.append(f"billing.sqlite invalid: {err}")
    # Optional sanity: ensure at least one account row
    try:
        conn = sqlite3.connect(db)
        row = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()
        if not row or row[0] == 0:
            issues.append("billing.sqlite has no accounts")
        conn.close()
    except Exception:
        pass
    return (len(issues) == 0), issues


def _restore_from_backup(client: Minio, bucket: str, key: str) -> tuple[bool, str, list[str]]:
    temp_dir = Path("artifacts") / ".restore_tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_zip = temp_dir / key.replace("/", "_")
    issues: list[str] = []
    try:
        client.fget_object(bucket, key, str(temp_zip))
        with zipfile.ZipFile(temp_zip, "r") as zf:
            zf.extractall(temp_dir)
        ok, issues = _validate_restored_artifacts(temp_dir)
        if not ok:
            return False, "Backup validation failed", issues

        # Backup current files for rollback
        now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        artifacts = Path("artifacts")
        pj_live = artifacts / "projects.json"
        db_live = artifacts / "billing.sqlite"
        projects_dir_live = artifacts / "projects"
        if pj_live.exists():
            pj_live.rename(artifacts / f"projects.json.bak.{now}")
        if db_live.exists():
            db_live.rename(artifacts / f"billing.sqlite.bak.{now}")
        restored_pj = temp_dir / "projects.json"
        restored_db = temp_dir / "billing.sqlite"
        restored_projects_dir = temp_dir / "projects"
        artifacts.mkdir(parents=True, exist_ok=True)
        restored_pj.replace(pj_live)
        restored_db.replace(db_live)
        if restored_projects_dir.exists():
            if projects_dir_live.exists():
                shutil.rmtree(projects_dir_live, ignore_errors=True)
            shutil.copytree(restored_projects_dir, projects_dir_live)
        return True, "Restore applied", issues
    except Exception as err:
        issues.append(str(err))
        return False, f"Restore failed: {err}", issues
    finally:
        try:
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass


def auto_restore_on_data_loss() -> tuple[bool, str]:
    """
    When data-loss indicators exist, attempt an automatic restore from the latest backup.
    Returns (ok, message). ok=True only if restore attempted and applied.
    """
    critical = [
        Path("artifacts") / "projects.json",
        Path("artifacts") / "billing.sqlite",
    ]
    issues = []
    for path in critical:
        if not path.exists():
            issues.append(f"{path} missing")
        else:
            try:
                if path.stat().st_size <= 0:
                    issues.append(f"{path} empty")
            except OSError:
                issues.append(f"{path} unreadable")
    if not issues:
        return False, "Restore skipped: no data-loss indicators."
    if _restore_recently_ran():
        return False, "Restore skipped: recent auto-restore already ran."
    client, bucket = _get_backup_client()
    if not client or not bucket:
        return False, "Restore skipped: R2 not configured."
    objs = _list_backup_objects(client, bucket)
    if not objs:
        return False, "Restore skipped: no backups found."
    objs.sort(key=lambda o: o.object_name, reverse=True)

    ok = False
    message = "Restore skipped"
    val_issues: list[str] = []
    chosen_key = None
    for obj in objs:
        chosen_key = obj.object_name
        ok, message, val_issues = _restore_from_backup(client, bucket, chosen_key)
        if ok:
            break
    if not chosen_key:
        chosen_key = objs[0].object_name

    state = _load_state()
    state["last_restore_at"] = _iso(datetime.now(timezone.utc))
    state["last_restore_key"] = chosen_key
    state["last_restore_status"] = message
    state["last_restore_issues"] = val_issues
    _save_state(state)
    if ok:
        _log(logging.WARNING, f"Auto-restore applied from {chosen_key}")
    else:
        _log(logging.ERROR, f"Auto-restore failed: {message}")
    return ok, message


def restore_backup(key: str) -> tuple[bool, str, list[str]]:
    """
    Restore from a specific backup key (e.g., backups/backup-YYYYMMDDTHHMMSSZ.zip).
    Returns (ok, message, issues).
    """
    client, bucket = _get_backup_client()
    if not client or not bucket:
        return False, "Restore failed: R2 not configured", []
    ok, message, issues = _restore_from_backup(client, bucket, key)
    state = _load_state()
    state["last_restore_at"] = _iso(datetime.now(timezone.utc))
    state["last_restore_key"] = key
    state["last_restore_status"] = message
    state["last_restore_issues"] = issues
    _save_state(state)
    if ok:
        _log(logging.WARNING, f"Manual restore applied from {key}")
    else:
        _log(logging.ERROR, f"Manual restore failed from {key}: {message}")
    return ok, message, issues


def lazy_daily_backup() -> None:
    state = _load_state()
    last = _parse_iso(state.get("last_backup_at"))
    now = datetime.now(timezone.utc)
    if last and (now - last) < timedelta(hours=24):
        return
    ok, _ = run_backup_now(reason="daily")
    if not ok:
        _log_once("backup_daily_failed", logging.WARNING, "Daily backup failed or skipped.")
