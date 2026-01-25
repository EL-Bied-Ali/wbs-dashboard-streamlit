from __future__ import annotations

import gzip
import hashlib
import json
import os
import pickle
import tempfile
import time
from datetime import date
from pathlib import Path
from typing import Any, Optional

import pandas as pd

# ============================================================
# ChronoPlan Disk Cache (Fast + Robust)
#
# - DataFrame -> Parquet (fast)
# - Complex Python objects (datetime/numpy/pandas scalars) -> Pickle
#   - optionally gzip compress large pickles (level 1) for space
# - Metadata -> JSON.gz (small)
#
# Atomicity / partial writes:
# - We write files, then create a COMMIT marker last.
# - Load requires COMMIT + required files, so partial dirs are ignored.
#
# Cleanup / pruning (optional env vars):
#   CHRONOPLAN_CACHE_DIR                     custom cache directory
#   CHRONOPLAN_CACHE_DISABLE                 1/true/yes/on disables disk cache
#   CHRONOPLAN_CACHE_MAX_MB                  max total cache size (best-effort)
#   CHRONOPLAN_CACHE_MAX_AGE_DAYS            delete entries older than N days
#   CHRONOPLAN_CACHE_CLEANUP_EVERY_N_WRITES  run cleanup every N writes (default 20)
#   CHRONOPLAN_CACHE_PICKLE_GZIP_MIN_MB      compress pickle blobs >= N MB (default 5)
# ============================================================

CACHE_VERSION = 5

_DEFAULT_CACHE_DIR = Path(tempfile.gettempdir()) / "chronoplan_cache"
_CACHE_DIR = Path(os.getenv("CHRONOPLAN_CACHE_DIR") or _DEFAULT_CACHE_DIR)
_CACHE_DISABLED = (os.getenv("CHRONOPLAN_CACHE_DISABLE") or "").strip().lower() in {"1", "true", "yes", "on"}

_META_GZIP_LEVEL = 1

_COMMIT_FILE = ".commit"
_WRITE_COUNT = 0


def _env_int(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _max_cache_mb() -> int:
    return max(_env_int("CHRONOPLAN_CACHE_MAX_MB", 0), 0)


def _max_age_days() -> int:
    return max(_env_int("CHRONOPLAN_CACHE_MAX_AGE_DAYS", 0), 0)


def _cleanup_every_n_writes() -> int:
    return max(_env_int("CHRONOPLAN_CACHE_CLEANUP_EVERY_N_WRITES", 20), 1)


def _pickle_gzip_min_mb() -> int:
    return max(_env_int("CHRONOPLAN_CACHE_PICKLE_GZIP_MIN_MB", 5), 0)


def _ensure_cache_dir() -> Path:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return _CACHE_DIR


def _is_cache_enabled() -> bool:
    return not _CACHE_DISABLED


def _now_ts() -> float:
    return time.time()


def _safe_stem(text: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in text).strip("._")[:80]


def _mapping_json(mapping: dict | None) -> str:
    if not mapping:
        return ""
    return json.dumps(mapping, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def mapping_digest(mapping: dict | None) -> str:
    raw = _mapping_json(mapping).encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:12]


def file_fingerprint(path: str) -> str:
    st = os.stat(path)
    mtime_ns = getattr(st, "st_mtime_ns", int(st.st_mtime * 1_000_000_000))
    return f"{st.st_size}_{mtime_ns}"


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    finally:
        try:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
        except Exception:
            pass


def _gzip_json_dumps(obj: Any) -> bytes:
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return gzip.compress(raw, compresslevel=_META_GZIP_LEVEL)


def _gzip_json_loads(blob: bytes) -> Any:
    raw = gzip.decompress(blob)
    return json.loads(raw.decode("utf-8"))


def _pickle_dumps(obj: Any) -> bytes:
    return pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)


def _pickle_loads(blob: bytes) -> Any:
    return pickle.loads(blob)


def _maybe_gzip(blob: bytes) -> tuple[bytes, bool]:
    min_mb = _pickle_gzip_min_mb()
    if min_mb <= 0:
        return blob, False
    if len(blob) < min_mb * 1024 * 1024:
        return blob, False
    return gzip.compress(blob, compresslevel=1), True


def _write_pickle_maybe_compress(path_base: Path, obj: Any) -> Path:
    blob = _pickle_dumps(obj)
    blob2, gz = _maybe_gzip(blob)
    out = path_base.with_suffix(".pkl.gz" if gz else ".pkl")
    _atomic_write_bytes(out, blob2)
    return out


def _read_pickle_auto(path_base: Path) -> Any:
    gz = path_base.with_suffix(".pkl.gz")
    raw = path_base.with_suffix(".pkl")
    if gz.exists():
        data = gzip.decompress(gz.read_bytes())
        return _pickle_loads(data)
    return _pickle_loads(raw.read_bytes())


def _commit_path(cache_dir: Path) -> Path:
    return cache_dir / _COMMIT_FILE


def _is_committed(cache_dir: Path) -> bool:
    return _commit_path(cache_dir).exists()


def _commit(cache_dir: Path) -> None:
    _atomic_write_bytes(_commit_path(cache_dir), b"ok")


def _dir_for_dashboard(path: str) -> Path:
    fp = file_fingerprint(path)
    stem = _safe_stem(Path(path).name)
    return _ensure_cache_dir() / f"{stem}.{fp}.v{CACHE_VERSION}.dashboard"


def _dir_for_headers(path: str, mapping: dict | None) -> Path:
    fp = file_fingerprint(path)
    stem = _safe_stem(Path(path).name)
    md = mapping_digest(mapping)
    return _ensure_cache_dir() / f"{stem}.{fp}.v{CACHE_VERSION}.headers.{md}"


def _dir_for_schedprev(path: str, mapping: dict | None, today: date) -> Path:
    fp = file_fingerprint(path)
    stem = _safe_stem(Path(path).name)
    md = mapping_digest(mapping)
    return _ensure_cache_dir() / f"{stem}.{fp}.v{CACHE_VERSION}.schedprev.{md}.{today.isoformat()}"


def _dir_for_wbs(path: str, mapping: dict | None, today: date) -> Path:
    fp = file_fingerprint(path)
    stem = _safe_stem(Path(path).name)
    md = mapping_digest(mapping)
    return _ensure_cache_dir() / f"{stem}.{fp}.v{CACHE_VERSION}.wbs.{md}.{today.isoformat()}"


def _meta_path(cache_dir: Path) -> Path:
    return cache_dir / "meta.json.gz"


def _df_path(cache_dir: Path) -> Path:
    return cache_dir / "df.parquet"


def _dir_mtime_ts(p: Path) -> float:
    try:
        return p.stat().st_mtime
    except Exception:
        return 0.0


def _dir_size_bytes(p: Path) -> int:
    total = 0
    try:
        for f in p.rglob("*"):
            if f.is_file():
                try:
                    total += f.stat().st_size
                except Exception:
                    pass
    except Exception:
        pass
    return total


def _rm_tree(p: Path) -> None:
    try:
        if p.is_file():
            p.unlink(missing_ok=True)
            return
        if not p.exists():
            return
        for sub in sorted(p.rglob("*"), reverse=True):
            try:
                if sub.is_file():
                    sub.unlink(missing_ok=True)
                elif sub.is_dir():
                    sub.rmdir()
            except Exception:
                pass
        try:
            p.rmdir()
        except Exception:
            pass
    except Exception:
        pass


def _cleanup_cache_dir_best_effort() -> None:
    cache_root = _ensure_cache_dir()
    max_age_days = _max_age_days()
    max_mb = _max_cache_mb()

    dirs: list[Path] = []
    try:
        for p in cache_root.iterdir():
            if p.is_dir():
                dirs.append(p)
    except Exception:
        return

    for d in dirs:
        if not _is_committed(d):
            _rm_tree(d)

    dirs = [d for d in dirs if d.exists() and d.is_dir()]

    if max_age_days > 0:
        cutoff = _now_ts() - (max_age_days * 86400)
        for d in dirs:
            if _dir_mtime_ts(d) < cutoff:
                _rm_tree(d)

    dirs = [d for d in dirs if d.exists() and d.is_dir()]

    if max_mb > 0:
        limit = max_mb * 1024 * 1024
        entries = []
        total = 0
        for d in dirs:
            sz = _dir_size_bytes(d)
            total += sz
            entries.append((_dir_mtime_ts(d), sz, d))
        if total > limit:
            entries.sort(key=lambda x: x[0])
            for _, sz, d in entries:
                _rm_tree(d)
                total -= sz
                if total <= limit:
                    break


def _maybe_periodic_cleanup() -> None:
    global _WRITE_COUNT
    _WRITE_COUNT += 1
    if _WRITE_COUNT % _cleanup_every_n_writes() == 0:
        _cleanup_cache_dir_best_effort()


_SERIES_KEYS = ("weekly_actual", "weekly_forecast", "cum_planned", "cum_actual", "cum_forecast")


def save_dashboard_cache(path: str, excel_data: dict[str, Any]) -> None:
    if not _is_cache_enabled():
        return
    try:
        fp = file_fingerprint(path)
    except Exception:
        return

    cache_dir = _dir_for_dashboard(path)
    cache_dir.mkdir(parents=True, exist_ok=True)

    df = excel_data.get("df")
    if not isinstance(df, pd.DataFrame):
        return

    try:
        df_file = _df_path(cache_dir)
        tmp_df = df_file.with_suffix(df_file.suffix + ".tmp")
        df.to_parquet(tmp_df, index=False)
        os.replace(tmp_df, df_file)
    except Exception:
        return

    series_meta: dict[str, Any] = {}
    series_sidecar: dict[str, Any] = {}

    for k in _SERIES_KEYS:
        v = excel_data.get(k)
        if v is None:
            series_meta[k] = None
            continue
        try:
            name = getattr(v, "name", None)
            if name is not None and name in df.columns and len(df[name]) == len(v):
                series_meta[k] = {"__type__": "df_col", "name": str(name)}
                continue
        except Exception:
            pass
        series_meta[k] = {"__type__": "pickle_sidecar", "key": k}
        series_sidecar[k] = v

    if series_sidecar:
        _write_pickle_maybe_compress(cache_dir / "series", series_sidecar)
    else:
        try:
            (cache_dir / "series.pkl").unlink(missing_ok=True)
            (cache_dir / "series.pkl.gz").unlink(missing_ok=True)
        except Exception:
            pass

    meta = {
        "cache_version": CACHE_VERSION,
        "kind": "dashboard",
        "created_at_ts": _now_ts(),
        "path": path,
        "fingerprint": fp,
        "sheet_names": excel_data.get("sheet_names"),
        "chosen_sheet": excel_data.get("chosen_sheet"),
        "has_date": excel_data.get("has_date"),
        "colmap": excel_data.get("colmap"),
        "series_meta": series_meta,
    }
    _atomic_write_bytes(_meta_path(cache_dir), _gzip_json_dumps(meta))

    _commit(cache_dir)
    _maybe_periodic_cleanup()


def load_dashboard_cache(path: str) -> Optional[dict[str, Any]]:
    if not _is_cache_enabled():
        return None
    try:
        fp = file_fingerprint(path)
    except Exception:
        return None

    cache_dir = _dir_for_dashboard(path)
    if not cache_dir.exists() or not _is_committed(cache_dir):
        return None

    meta_file = _meta_path(cache_dir)
    df_file = _df_path(cache_dir)
    if not meta_file.exists() or not df_file.exists():
        return None

    try:
        meta = _gzip_json_loads(meta_file.read_bytes())
        if (
            not isinstance(meta, dict)
            or meta.get("cache_version") != CACHE_VERSION
            or meta.get("kind") != "dashboard"
            or meta.get("path") != path
            or meta.get("fingerprint") != fp
        ):
            return None

        df = pd.read_parquet(df_file)

        excel_data: dict[str, Any] = {
            "df": df,
            "sheet_names": meta.get("sheet_names"),
            "chosen_sheet": meta.get("chosen_sheet"),
            "has_date": meta.get("has_date"),
            "colmap": meta.get("colmap"),
        }

        series_meta = meta.get("series_meta") or {}
        sidecar: dict[str, Any] = {}
        try:
            if (cache_dir / "series.pkl").exists() or (cache_dir / "series.pkl.gz").exists():
                sidecar = _read_pickle_auto(cache_dir / "series")
                if not isinstance(sidecar, dict):
                    sidecar = {}
        except Exception:
            sidecar = {}

        for k in _SERIES_KEYS:
            spec = series_meta.get(k)
            if spec is None:
                excel_data[k] = None
                continue
            if isinstance(spec, dict) and spec.get("__type__") == "df_col":
                name = spec.get("name")
                excel_data[k] = df[name] if isinstance(name, str) and name in df.columns else None
                continue
            if isinstance(spec, dict) and spec.get("__type__") == "pickle_sidecar":
                excel_data[k] = sidecar.get(k)
                continue
            excel_data[k] = None

        return {"path": path, "fingerprint": fp, "data": excel_data}
    except Exception:
        return None


def save_headers_cache(
    path: str,
    mapping: dict | None,
    *,
    summary_headers: tuple[list[Any], dict[str, Any]] | None,
    assign_headers: tuple[list[Any], dict[str, Any]] | None,
) -> None:
    if not _is_cache_enabled():
        return
    try:
        fp = file_fingerprint(path)
    except Exception:
        return

    cache_dir = _dir_for_headers(path, mapping)
    cache_dir.mkdir(parents=True, exist_ok=True)

    meta = {
        "cache_version": CACHE_VERSION,
        "kind": "headers",
        "created_at_ts": _now_ts(),
        "path": path,
        "fingerprint": fp,
        "mapping_digest": mapping_digest(mapping),
    }
    _atomic_write_bytes(_meta_path(cache_dir), _gzip_json_dumps(meta))

    payload = {"summary_headers": summary_headers, "assign_headers": assign_headers}
    _write_pickle_maybe_compress(cache_dir / "headers", payload)

    _commit(cache_dir)
    _maybe_periodic_cleanup()


def load_headers_cache(path: str, mapping: dict | None) -> Optional[dict[str, Any]]:
    if not _is_cache_enabled():
        return None
    try:
        fp = file_fingerprint(path)
    except Exception:
        return None

    cache_dir = _dir_for_headers(path, mapping)
    if not cache_dir.exists() or not _is_committed(cache_dir):
        return None

    meta_path = _meta_path(cache_dir)
    if not meta_path.exists():
        return None

    try:
        meta = _gzip_json_loads(meta_path.read_bytes())
        if (
            not isinstance(meta, dict)
            or meta.get("cache_version") != CACHE_VERSION
            or meta.get("kind") != "headers"
            or meta.get("path") != path
            or meta.get("fingerprint") != fp
            or meta.get("mapping_digest") != mapping_digest(mapping)
        ):
            return None

        payload = _read_pickle_auto(cache_dir / "headers")
        if not isinstance(payload, dict):
            return None

        return {**meta, **payload}
    except Exception:
        return None


def save_schedule_preview_cache(
    path: str,
    mapping: dict | None,
    today: date,
    *,
    schedule_lookup: dict,
    schedule_info: dict,
    preview_rows: list,
) -> None:
    if not _is_cache_enabled():
        return
    try:
        fp = file_fingerprint(path)
    except Exception:
        return

    cache_dir = _dir_for_schedprev(path, mapping, today)
    cache_dir.mkdir(parents=True, exist_ok=True)

    meta = {
        "cache_version": CACHE_VERSION,
        "kind": "schedprev",
        "created_at_ts": _now_ts(),
        "path": path,
        "fingerprint": fp,
        "mapping_digest": mapping_digest(mapping),
        "today": today.isoformat(),
    }
    _atomic_write_bytes(_meta_path(cache_dir), _gzip_json_dumps(meta))

    _write_pickle_maybe_compress(cache_dir / "schedule", {"schedule_lookup": schedule_lookup, "schedule_info": schedule_info})
    _write_pickle_maybe_compress(cache_dir / "preview", preview_rows)

    _commit(cache_dir)
    _maybe_periodic_cleanup()


def load_schedule_preview_cache(path: str, mapping: dict | None, today: date) -> Optional[dict[str, Any]]:
    if not _is_cache_enabled():
        return None
    try:
        fp = file_fingerprint(path)
    except Exception:
        return None

    cache_dir = _dir_for_schedprev(path, mapping, today)
    if not cache_dir.exists() or not _is_committed(cache_dir):
        return None

    meta_path = _meta_path(cache_dir)
    if not meta_path.exists():
        return None

    try:
        meta = _gzip_json_loads(meta_path.read_bytes())
        if (
            not isinstance(meta, dict)
            or meta.get("cache_version") != CACHE_VERSION
            or meta.get("kind") != "schedprev"
            or meta.get("path") != path
            or meta.get("fingerprint") != fp
            or meta.get("mapping_digest") != mapping_digest(mapping)
            or meta.get("today") != today.isoformat()
        ):
            return None

        schedule = _read_pickle_auto(cache_dir / "schedule")
        preview_rows = _read_pickle_auto(cache_dir / "preview")
        if not isinstance(schedule, dict):
            return None

        return {
            **meta,
            "schedule_lookup": schedule.get("schedule_lookup"),
            "schedule_info": schedule.get("schedule_info"),
            "preview_rows": preview_rows,
        }
    except Exception:
        return None


def save_wbs_cache(
    path: str,
    mapping: dict | None,
    today: date,
    *,
    packs: list,
    schedule_lookup: dict,
    schedule_info: dict,
    preview_rows: list,
    detected_tables: list,
) -> None:
    if not _is_cache_enabled():
        return
    try:
        fp = file_fingerprint(path)
    except Exception:
        return

    cache_dir = _dir_for_wbs(path, mapping, today)
    cache_dir.mkdir(parents=True, exist_ok=True)

    meta = {
        "cache_version": CACHE_VERSION,
        "kind": "wbs",
        "created_at_ts": _now_ts(),
        "path": path,
        "fingerprint": fp,
        "mapping_digest": mapping_digest(mapping),
        "today": today.isoformat(),
    }
    _atomic_write_bytes(_meta_path(cache_dir), _gzip_json_dumps(meta))

    _write_pickle_maybe_compress(cache_dir / "wbs", {"packs": packs, "detected_tables": detected_tables})
    _write_pickle_maybe_compress(cache_dir / "preview", preview_rows)
    _write_pickle_maybe_compress(cache_dir / "schedule", {"schedule_lookup": schedule_lookup, "schedule_info": schedule_info})

    _commit(cache_dir)
    _maybe_periodic_cleanup()


def load_wbs_cache(path: str, mapping: dict | None, today: date) -> Optional[dict[str, Any]]:
    if not _is_cache_enabled():
        return None
    try:
        fp = file_fingerprint(path)
    except Exception:
        return None

    cache_dir = _dir_for_wbs(path, mapping, today)
    if not cache_dir.exists() or not _is_committed(cache_dir):
        return None

    meta_path = _meta_path(cache_dir)
    if not meta_path.exists():
        return None

    try:
        meta = _gzip_json_loads(meta_path.read_bytes())
        if (
            not isinstance(meta, dict)
            or meta.get("cache_version") != CACHE_VERSION
            or meta.get("kind") != "wbs"
            or meta.get("path") != path
            or meta.get("fingerprint") != fp
            or meta.get("mapping_digest") != mapping_digest(mapping)
            or meta.get("today") != today.isoformat()
        ):
            return None

        wbs = _read_pickle_auto(cache_dir / "wbs")
        preview_rows = _read_pickle_auto(cache_dir / "preview")
        schedule = _read_pickle_auto(cache_dir / "schedule")
        if not isinstance(wbs, dict) or not isinstance(schedule, dict):
            return None

        return {
            **meta,
            "packs": wbs.get("packs"),
            "detected_tables": wbs.get("detected_tables"),
            "preview_rows": preview_rows,
            "schedule_lookup": schedule.get("schedule_lookup"),
            "schedule_info": schedule.get("schedule_info"),
        }
    except Exception:
        return None


def clear_cache_dir() -> None:
    _rm_tree(_ensure_cache_dir())
    _ensure_cache_dir()


def dashboard_cache_path(path: str) -> Path:
    return _meta_path(_dir_for_dashboard(path))


def headers_cache_path(path: str, mapping: dict | None) -> Path:
    return _meta_path(_dir_for_headers(path, mapping))


def schedule_preview_cache_path(path: str, mapping: dict | None, today: date) -> Path:
    return _meta_path(_dir_for_schedprev(path, mapping, today))


def wbs_cache_path(path: str, mapping: dict | None, today: date) -> Path:
    return _meta_path(_dir_for_wbs(path, mapping, today))
