# projects_page/actions.py
from __future__ import annotations

import html

import streamlit as st

from billing_store import record_event
from projects import create_project, delete_project, update_project


def open_create_dialog(
    *,
    project_count: int,
    project_limit: int,
    owner_id: str | None,
    account_id: int | None,
    clear_query_params_fn,
) -> None:
    if not hasattr(st, "dialog"):
        st.info("Update Streamlit to use modal project creation.")
        return

    @st.dialog("Create project")
    def _dialog() -> None:
        with st.container(key="create_modal_root"):
            st.markdown('<div class="manage-modal-title">Create project</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="manage-modal-sub">Start a new workspace for a client or timeline.</div>',
                unsafe_allow_html=True,
            )
            with st.container(key="create_form_main"):
                if project_count >= project_limit:
                    st.warning(f"Project limit reached ({project_limit}).")
                    return

                name = st.text_input(
                    "Project name",
                    key="create_project_name",
                    placeholder="Project name",
                )

                if st.button("Create project", key="create_project_btn"):
                    project = create_project(name, owner_id=owner_id)
                    if project:
                        record_event(
                            account_id,
                            "project_created",
                            {"project_id": project["id"]},
                        )
                        st.session_state["active_project_id"] = project["id"]
                        st.session_state.pop("project_loaded_id", None)
                        st.session_state["navigate_to_app"] = True
                        clear_query_params_fn()
                        st.rerun()

                    st.error("Unable to create project.")

    _dialog()


def project_actions_popover(
    *,
    project_id: str,
    current_name: str,
    owner_id: str | None,
) -> None:
    if not hasattr(st, "popover"):
        return

    with st.popover("⚙︎", use_container_width=False):
        st.caption("Manage project")

        new_name = st.text_input(
            "Name",
            value=current_name,
            label_visibility="collapsed",
            key=f"rn_{project_id}",
        )

        cols = st.columns([1, 1], gap="small")
        with cols[0]:
            if st.button("Save", key=f"save_{project_id}", use_container_width=True):
                cleaned = (new_name or "").strip()
                if not cleaned:
                    st.warning("Project name cannot be empty.")
                else:
                    if update_project(project_id, owner_id=owner_id, name=cleaned):
                        st.session_state["project_flash"] = f'Project renamed to "{cleaned}".'
                        st.rerun()
                    else:
                        st.error("Unable to update project name.")

        st.divider()
        st.caption("Danger zone")

        if st.button(
            "Delete",
            key=f"askdel_{project_id}",
            type="primary",
            use_container_width=True,
        ):
            st.session_state[f"confirm_{project_id}"] = True

        if st.session_state.get(f"confirm_{project_id}"):
            confirm_cols = st.columns(2, gap="small")
            with confirm_cols[0]:
                if st.button("Confirm", key=f"del_{project_id}", use_container_width=True):
                    if delete_project(project_id, owner_id=owner_id):
                        st.session_state.pop(f"confirm_{project_id}", None)
                        st.session_state["project_flash"] = f'Project "{current_name}" deleted.'
                        st.rerun()
                    else:
                        st.error("Unable to delete project.")
            with confirm_cols[1]:
                if st.button("Cancel", key=f"canc_{project_id}", use_container_width=True):
                    st.session_state.pop(f"confirm_{project_id}", None)
