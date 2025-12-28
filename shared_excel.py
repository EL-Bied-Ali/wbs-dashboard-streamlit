from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

_MANIFEST_PATH = Path(".streamlit") / "shared_excel.json"
_DEFAULT_CANDIDATES = [
    Path("artifacts") / "Chronoplan_Template.xlsx",
    Path("artifacts") / "W_example.xlsx",
    Path("artifacts") / "wbs_sample.xlsx",
    Path("Progress.xlsx"),
]


def _manifest_data() -> dict | None:
    if not _MANIFEST_PATH.exists():
        return None
    try:
        return json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None


def _infer_key(path: Path) -> str:
    size = path.stat().st_size if path.exists() else 0
    return f"{path.name}:{size}"


def restore_shared_excel_state() -> None:
    if st.session_state.get("shared_excel_path"):
        return
    data = _manifest_data()
    if not data:
        return
    raw_path = data.get("path")
    if not raw_path:
        return
    path = Path(raw_path)
    if not path.exists():
        return
    st.session_state["shared_excel_path"] = str(path)
    st.session_state["shared_excel_name"] = data.get("name") or path.name
    st.session_state["shared_excel_key"] = data.get("key") or _infer_key(path)


def persist_shared_excel_state(path: str, name: str | None, key: str | None) -> None:
    if not path:
        return
    _MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "path": path,
        "name": name or Path(path).name,
        "key": key or _infer_key(Path(path)),
    }
    _MANIFEST_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def set_default_excel_if_missing() -> str | None:
    if st.session_state.get("shared_excel_path"):
        return st.session_state.get("shared_excel_path")
    for path in _DEFAULT_CANDIDATES:
        if path.exists():
            file_key = f"default:{path.name}:{path.stat().st_mtime}"
            if st.session_state.get("shared_excel_key") == file_key:
                return st.session_state.get("shared_excel_path")
            data = path.read_bytes()
            # Keep temp alongside the OS temp dir if available.
            temp_path = Path(Path.cwd()) / path.name
            try:
                import tempfile

                tmp_file = tempfile.NamedTemporaryFile(
                    delete=False, suffix=path.suffix or ".xlsx"
                )
                tmp_file.write(data)
                tmp_file.close()
                temp_path = Path(tmp_file.name)
            except Exception:
                temp_path.write_bytes(data)
            st.session_state["shared_excel_path"] = str(temp_path)
            st.session_state["shared_excel_key"] = file_key
            st.session_state["shared_excel_name"] = path.name
            persist_shared_excel_state(str(temp_path), path.name, file_key)
            return str(temp_path)
    return None
