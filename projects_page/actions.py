# projects_page/actions.py
from __future__ import annotations

import html

import streamlit as st

from billing_store import record_event
from projects import create_project, delete_project, update_project

def _clear_flow_params_preserve_dev() -> None:
    from projects_page.routing import del_params
    del_params("create", "new", "project", "logout")


def open_create_dialog(
    *,
    project_count: int,
    project_limit: int,
    owner_id: str | None,
    org_id: str | None,
    account_id: int | None,
    clear_query_params_fn,
    user: dict | None = None,
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
                    try:
                        project = create_project(name, owner_id=owner_id, org_id=org_id, user=user)
                        if project:
                            record_event(
                                account_id,
                                "project_created",
                                {"project_id": project["id"]},
                            )
                            st.session_state["active_project_id"] = project["id"]
                            st.session_state.pop("project_loaded_id", None)
                            st.session_state["navigate_to_app"] = True
                            _clear_flow_params_preserve_dev()
                            st.rerun()
                        else:
                            st.error("Unable to create project.")
                    except PermissionError as e:
                        st.error(f"🔒 {str(e)}")
                        st.page_link("pages/4_Billing.py", label="Go to Billing")

    _dialog()


def open_create_popover(
    *,
    project_count: int,
    project_limit: int,
    owner_id: str | None,
    org_id: str | None,
    account_id: int | None,
    can_edit: bool = True,
    user: dict | None = None,
) -> None:
    """Render a small floating create project panel using st.popover.

    This is UI-only: it does not modify query params or perform navigation. On
    successful creation it sets a flash message and reruns so the project list
    refreshes.
    """
    if not hasattr(st, "popover"):
        # Fallback to dialog for older Streamlit versions
        open_create_dialog(
            project_count=project_count,
            project_limit=project_limit,
            owner_id=owner_id,
            org_id=org_id,
            account_id=account_id,
            clear_query_params_fn=lambda *a, **k: None,
            user=user,
        )
        return

    if not can_edit:
        st.button("Create project", disabled=True, key="create_btn_disabled", help="Your plan is expired. Upgrade to create projects.")
        return
 
    with st.popover("Create project", width="content"):
        with st.container(key="cp_popover_create"):
            with st.container(key="create_form_popover"):
                if project_count >= project_limit:
                    st.warning(f"Project limit reached ({project_limit}).")
                    return
 
                if not owner_id and not org_id:
                    st.warning("Unable to create project: missing owner information.")
                    return
 
                with st.form("create_project_form_popover", clear_on_submit=True):
                    name = st.text_input(
                        "Project name",
                        key="create_project_name_popover",
                        placeholder="New project name",
                        label_visibility="collapsed",
                    )
 
                    # Subtitle moved UNDER the input
                    st.markdown(
                        '<div class="create-project-helper">'
                        'Start a new workspace for a client or timeline.'
                        '</div>',
                        unsafe_allow_html=True,
                    )
 
                    # Required submit button (hidden via CSS)
                    submitted = st.form_submit_button("Create project")
 
                if submitted:
                    cleaned = (name or "").strip()
                    if not cleaned:
                        st.warning("Project name cannot be empty.")
                    else:
                        try:
                            project = create_project(cleaned, owner_id=owner_id, org_id=org_id, user=user)
                            if project:
                                record_event(
                                    account_id,
                                    "project_created",
                                    {"project_id": project["id"]},
                                )
                                st.session_state["project_flash"] = f'Project "{cleaned}" created.'
                                st.rerun()
                            else:
                                st.error("Unable to create project.")
                        except PermissionError as e:
                            st.error(f"🔒 {str(e)}")
                            st.page_link("pages/4_Billing.py", label="Go to Billing")


def project_actions_popover(
    *,
    project_id: str,
    current_name: str,
    owner_id: str | None,
    can_edit: bool = True,
    user: dict | None = None,
) -> None:
    if not hasattr(st, "popover"):
        return
    
    if not can_edit:
        st.button("⚙︎", disabled=True, key=f"actions_btn_disabled_{project_id}", help="Your plan is expired. Upgrade to modify projects.")
        return
 
    with st.popover("⚙︎", width="content"):
        with st.container(key=f"cp_popover_manage_{project_id}"):
            st.caption("Manage project")
 
            new_name = st.text_input(
                "Name",
                value=current_name,
                label_visibility="collapsed",
                key=f"rn_{project_id}",
            )
 
            cols = st.columns([1, 1], gap="small")
            with cols[0]:
                if st.button("Save", key=f"save_{project_id}", width="stretch"):
                    cleaned = (new_name or "").strip()
                    if not cleaned:
                        st.warning("Project name cannot be empty.")
                    else:
                        try:
                            if update_project(project_id, owner_id=owner_id, name=cleaned, user=user):
                                st.session_state["project_flash"] = f'Project renamed to "{cleaned}".'
                                st.rerun()
                            else:
                                st.error("Unable to update project name.")
                        except PermissionError as e:
                            st.error(f"🔒 {str(e)}")
                            st.page_link("pages/4_Billing.py", label="Go to Billing")
 
            st.divider()
            st.markdown(
                '<div class="manage-danger-title">Danger zone</div>',
                unsafe_allow_html=True,
            )
 
            if st.button(
                "Delete",
                key=f"askdel_{project_id}",
                type="primary",
                width="stretch",
            ):
                st.session_state[f"confirm_{project_id}"] = True
 
            if st.session_state.get(f"confirm_{project_id}"):
                confirm_cols = st.columns(2, gap="small")
                with confirm_cols[0]:
                    if st.button("Confirm", key=f"del_{project_id}", width="stretch"):
                        try:
                            if delete_project(project_id, owner_id=owner_id, user=user):
                                st.session_state.pop(f"confirm_{project_id}", None)
                                st.session_state["project_flash"] = f'Project "{current_name}" deleted.'
                                st.rerun()
                            else:
                                st.error("Unable to delete project.")
                        except PermissionError as e:
                            st.error(f"🔒 {str(e)}")
                            st.page_link("pages/4_Billing.py", label="Go to Billing")
                with confirm_cols[1]:
                    if st.button("Cancel", key=f"canc_{project_id}", width="stretch"):
                        st.session_state.pop(f"confirm_{project_id}", None)
