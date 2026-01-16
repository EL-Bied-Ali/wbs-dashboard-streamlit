from __future__ import annotations

import json
import logging
import os
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

import streamlit as st
from minio import Minio
from minio.error import S3Error

BACKUP_STATE_PATH = Path("artifacts") / "backup_state.json"
BACKUP_PREFIX = "backups/"
DEFAULT_KEEP = 14

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


def run_backup_now(reason: str = "manual") -> tuple[bool, str]:
    client, bucket = _get_backup_client()
    if not client or not bucket:
        return False, "Missing R2 configuration."
    now = datetime.now(timezone.utc)
    key = f"{BACKUP_PREFIX}backup-{now.strftime('%Y%m%dT%H%M%SZ')}.zip"
    temp_path = Path("artifacts") / f".tmp-{key.replace('/', '_')}"
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
            temp_path.unlink(missing_ok=True)


def lazy_daily_backup() -> None:
    state = _load_state()
    last = _parse_iso(state.get("last_backup_at"))
    now = datetime.now(timezone.utc)
    if last and (now - last) < timedelta(hours=24):
        return
    ok, _ = run_backup_now(reason="daily")
    if not ok:
        _log_once("backup_daily_failed", logging.WARNING, "Daily backup failed or skipped.")
