from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
import uuid

import streamlit as st

PROJECT_LIMIT = 3
PROJECTS_PATH = Path("artifacts") / "projects.json"
PROJECTS_DIR = Path("artifacts") / "projects"


def _normalize_owner_id(value: object | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return f"acct:{int(value)}"
    text = str(value).strip()
    if not text:
        return None
    lowered = text.lower()
    if lowered.startswith("acct:") or lowered.startswith("email:"):
        return lowered
    if "@" in lowered:
        return f"email:{lowered}"
    return f"acct:{lowered}"


def owner_id_from_user(user: dict | None) -> str | None:
    if not user:
        return None
    account_id = user.get("billing_account_id")
    if account_id is not None:
        return _normalize_owner_id(account_id)
    email = (user.get("email") or "").strip()
    if email:
        return _normalize_owner_id(email)
    return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_projects() -> list[dict]:
    if not PROJECTS_PATH.exists():
        return []
    try:
        data = json.loads(PROJECTS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    if isinstance(data, dict):
        data = data.get("projects", [])
    if not isinstance(data, list):
        return []
    return [p for p in data if isinstance(p, dict)]


def _save_projects(projects: list[dict]) -> None:
    PROJECTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROJECTS_PATH.write_text(json.dumps(projects, indent=2), encoding="utf-8")


def _find_project_index(projects: list[dict], project_id: str) -> int | None:
    for idx, project in enumerate(projects):
        if project.get("id") == project_id:
            return idx
    return None


def _new_project_id(projects: list[dict]) -> str:
    existing = {p.get("id") for p in projects}
    while True:
        candidate = f"proj_{uuid.uuid4().hex[:8]}"
        if candidate not in existing:
            return candidate


def _project_path(project_id: str, suffix: str) -> Path:
    safe_suffix = suffix if suffix.startswith(".") else f".{suffix}"
    return PROJECTS_DIR / project_id / f"latest{safe_suffix}"


def project_mapping_key(project_id: str | None, file_key: str | None) -> str | None:
    if not project_id or not file_key:
        return None
    return f"{project_id}:{file_key}"


def list_projects(owner_id: str | int | None = None) -> list[dict]:
    projects = _load_projects()
    if owner_id is None:
        return []
    owner_key = _normalize_owner_id(owner_id)
    if not owner_key:
        return []
    return [
        project
        for project in projects
        if _normalize_owner_id(project.get("owner_id")) == owner_key
    ]


def create_project(name: str | None, owner_id: str | int | None = None) -> dict | None:
    owner_key = _normalize_owner_id(owner_id)
    if not owner_key:
        return None
    projects = _load_projects()
    owner_projects = [
        project
        for project in projects
        if _normalize_owner_id(project.get("owner_id")) == owner_key
    ]
    if len(owner_projects) >= PROJECT_LIMIT:
        return None
    clean_name = (name or "").strip()
    if not clean_name:
        clean_name = f"Project {len(owner_projects) + 1}"
    project = {
        "id": _new_project_id(projects),
        "owner_id": owner_key,
        "name": clean_name,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "file_path": None,
        "file_name": None,
        "file_key": None,
        "mapping": None,
        "mapping_key": None,
    }
    projects.append(project)
    _save_projects(projects)
    return project


def get_project(project_id: str | None, owner_id: str | int | None = None) -> dict | None:
    if not project_id:
        return None
    projects = _load_projects()
    idx = _find_project_index(projects, project_id)
    if idx is None:
        return None
    project = projects[idx]
    if owner_id is None:
        return project
    owner_key = _normalize_owner_id(owner_id)
    if not owner_key:
        return None
    if _normalize_owner_id(project.get("owner_id")) != owner_key:
        return None
    return project


def update_project(project_id: str, owner_id: str | int | None = None, **fields: object) -> dict | None:
    projects = _load_projects()
    idx = _find_project_index(projects, project_id)
    if idx is None:
        return None
    project = projects[idx]
    if owner_id is not None:
        owner_key = _normalize_owner_id(owner_id)
        if not owner_key or _normalize_owner_id(project.get("owner_id")) != owner_key:
            return None
    project.update(fields)
    project["updated_at"] = _now_iso()
    projects[idx] = project
    _save_projects(projects)
    return project


def delete_project(
    project_id: str,
    *,
    owner_id: str | int | None = None,
    remove_files: bool = True,
) -> bool:
    projects = _load_projects()
    idx = _find_project_index(projects, project_id)
    if idx is None:
        return False
    project = projects[idx]
    if owner_id is not None:
        owner_key = _normalize_owner_id(owner_id)
        if not owner_key or _normalize_owner_id(project.get("owner_id")) != owner_key:
            return False
    projects.pop(idx)
    _save_projects(projects)
    if remove_files:
        project_dir = PROJECTS_DIR / project_id
        if project_dir.exists():
            shutil.rmtree(project_dir, ignore_errors=True)
    return True


def assign_projects_to_owner(owner_id: str | int | None) -> int:
    owner_key = _normalize_owner_id(owner_id)
    if not owner_key:
        return 0
    projects = _load_projects()
    updated = 0
    for project in projects:
        if not project.get("owner_id"):
            project["owner_id"] = owner_key
            updated += 1
    if updated:
        _save_projects(projects)
    return updated


def render_project_selector(owner_id: str | int | None, show_create: bool = True) -> dict | None:
    st.sidebar.markdown("### Projects")
    projects = list_projects(owner_id)
    if not projects:
        project = create_project("Project 1", owner_id=owner_id)
        projects = list_projects(owner_id)
        if project and project not in projects:
            projects.append(project)
    if not projects:
        st.sidebar.caption("No projects available.")
        return None
    project_map = {p.get("id"): p for p in projects if p.get("id")}
    options = list(project_map)
    if not options:
        st.sidebar.caption("No projects available.")
        return None
    if st.session_state.get("active_project_id") not in project_map:
        st.session_state["active_project_id"] = options[0]
    active_id = st.sidebar.selectbox(
        "Active project",
        options,
        format_func=lambda pid: project_map.get(pid, {}).get("name", pid),
        key="active_project_id",
        label_visibility="collapsed",
    )
    if show_create:
        _render_create_project_ui(projects, owner_id)
    return project_map.get(active_id)


def _render_create_project_ui(projects: list[dict], owner_id: str | int | None) -> None:
    with st.sidebar.expander("Create project", expanded=False):
        if len(projects) >= PROJECT_LIMIT:
            st.caption(f"Project limit reached ({PROJECT_LIMIT}).")
            return
        name = st.text_input("Project name", key="new_project_name")
        if st.button("Create project", key="create_project_btn"):
            project = create_project(name, owner_id=owner_id)
            if project:
                st.session_state["active_project_id"] = project["id"]
                st.session_state.pop("project_loaded_id", None)
                st.session_state["new_project_name"] = ""
                st.rerun()


def apply_project_to_session(project: dict | None) -> None:
    if not project:
        return
    project_id = project.get("id")
    if st.session_state.get("project_loaded_id") != project_id:
        st.session_state["project_loaded_id"] = project_id
        st.session_state.pop("excel_upload_shared", None)
        _clear_excel_session()
        _apply_project_file(project)
        _apply_project_mapping(project)


def _clear_excel_session() -> None:
    st.session_state.pop("shared_excel_path", None)
    st.session_state.pop("shared_excel_name", None)
    st.session_state.pop("shared_excel_key", None)


def _apply_project_file(project: dict) -> None:
    raw_path = project.get("file_path")
    if not raw_path:
        return
    path = Path(raw_path)
    if not path.exists():
        return
    st.session_state["shared_excel_path"] = str(path)
    st.session_state["shared_excel_name"] = project.get("file_name") or path.name
    st.session_state["shared_excel_key"] = project.get("file_key") or f"{path.name}:{path.stat().st_size}"


def _apply_project_mapping(project: dict) -> None:
    mapping = project.get("mapping")
    mapping_key = project.get("mapping_key")
    if not isinstance(mapping, dict):
        st.session_state.pop("column_mapping", None)
        st.session_state.pop("mapping_source_key", None)
        st.session_state["mapping_open"] = False
        st.session_state["mapping_skipped"] = False
        return
    st.session_state["column_mapping"] = mapping
    st.session_state["mapping_source_key"] = mapping_key
    st.session_state["mapping_open"] = False
    st.session_state["mapping_skipped"] = False


def store_project_upload(project: dict | None, uploaded) -> str | None:
    if project is None:
        return st.session_state.get("shared_excel_path")
    if uploaded is None:
        return st.session_state.get("shared_excel_path")
    file_key = f"{uploaded.name}:{uploaded.size}"
    if st.session_state.get("shared_excel_key") == file_key:
        return st.session_state.get("shared_excel_path")
    suffix = Path(uploaded.name).suffix or ".xlsx"
    project_id = project.get("id")
    if not project_id:
        return st.session_state.get("shared_excel_path")
    target_path = _project_path(project_id, suffix)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    data = uploaded.getvalue()
    target_path.write_bytes(data)
    prior_path = project.get("file_path")
    if prior_path and prior_path != str(target_path):
        try:
            prior = Path(prior_path)
            if prior.exists():
                prior.unlink()
        except OSError:
            pass
    st.session_state["shared_excel_path"] = str(target_path)
    st.session_state["shared_excel_key"] = file_key
    st.session_state["shared_excel_name"] = uploaded.name
    mapping_key = project_mapping_key(project_id, file_key)
    update_project(
        project_id,
        file_path=str(target_path),
        file_name=uploaded.name,
        file_key=file_key,
        mapping={"activity_summary": {}, "resource_assignments": {}},
        mapping_key=mapping_key,
    )
    st.session_state["column_mapping"] = {"activity_summary": {}, "resource_assignments": {}}
    st.session_state["mapping_source_key"] = mapping_key
    st.session_state["mapping_open"] = False
    st.session_state["mapping_skipped"] = False
    return str(target_path)


def persist_project_mapping(project_id: str | None, mapping: dict, mapping_key: str | None) -> None:
    if not project_id:
        return
    update_project(project_id, mapping=mapping, mapping_key=mapping_key)
