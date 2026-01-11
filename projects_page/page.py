from __future__ import annotations

import html
from pathlib import Path
from typing import Callable

import streamlit as st

from auth_google import _get_logo_data_uri, logout, require_login
from billing_store import access_status, get_account_by_email
from projects import PROJECT_LIMIT, assign_projects_to_owner, list_projects, owner_id_from_user
from projects_page.actions import open_create_dialog, project_actions_popover
from projects_page.debug_tools import debug_enabled, debug_log, timeit
from projects_page.routing import (
    base_url,
    clear_query_params,
    get_query_params,
    is_truthy,
    query_value,
    redirect_to_project,
)
from projects_page.status import file_exists, format_updated, project_action, project_status, sort_projects
from projects_page.styles import clean_html_block, inject_global_css, render_html
from projects_page.ui import render_admin_sidebar_left, render_hero, render_top_bar


def render_projects_page(
    *,
    is_admin_user_fn: Callable[[dict | None], bool],
    is_localhost_fn: Callable[[], bool],
    render_dev_switcher_fn: Callable[[str, dict | None], None] | None = None,
) -> None:
    st.session_state["_current_page"] = "Projects"
    inject_global_css()

    _debug = debug_enabled()
    _timings: list[tuple[str, float]] = []

    user = require_login()
    owner_id = owner_id_from_user(user)

    is_admin = is_admin_user_fn(user)
    if is_admin and owner_id:
        migrated_key = f"_projects_owner_migrated_{owner_id}"
        if not st.session_state.get(migrated_key):
            assign_projects_to_owner(owner_id)
            st.session_state[migrated_key] = True

    projects = list_projects(owner_id) or []
    project_count = len(projects)

    params = get_query_params()
    logout_param = query_value(params, "logout")
    project_param = query_value(params, "project")
    create_param = query_value(params, "create") or query_value(params, "new")

    if is_truthy(logout_param):
        logout()

    if st.session_state.pop("navigate_to_app", False):
        st.switch_page("app.py")

    if project_param:
        project_map = {p.get("id"): p for p in projects if p.get("id")}
        if project_param in project_map:
            redirect_to_project(project_param)
        clear_query_params()
        st.warning("Project not found.")

    account = get_account_by_email(user.get("email", ""))
    plan_state = access_status(account)
    is_locked = not plan_state.get("allowed", True)

    logo_uri = _get_logo_data_uri()
    if logo_uri:
        logo_html = f'<img class="top-logo" src="{logo_uri}" alt="ChronoPlan logo" />'
    else:
        logo_html = '<div class="top-logo-text">ChronoPlan</div>'

    user_name = user.get("name") or user.get("email") or "User"
    user_email = user.get("email") or ""
    user_picture = user.get("picture")
    initial = (user_name.strip()[:1] or "?").upper()

    plan_status = (plan_state.get("status") or "trialing").lower()
    trial_end = plan_state.get("trial_end")
    days_left = plan_state.get("days_left")
    plan_end = plan_state.get("plan_end")

    plan_label = "Premium"
    plan_class = "premium"
    plan_meta = ""

    if plan_status == "active":
        if is_locked:
            plan_label = "Subscription ended"
            plan_class = "locked"
            if plan_end:
                plan_meta = f"Ended {plan_end.strftime('%b %d, %Y')}"
            else:
                plan_meta = "Subscription required"
        elif plan_end:
            plan_meta = f"Ends {plan_end.strftime('%b %d, %Y')}"
    elif plan_status == "trialing":
        if is_locked:
            plan_label = "Trial ended"
            plan_class = "locked"
            if trial_end:
                plan_meta = f"Ended {trial_end.strftime('%b %d, %Y')}"
        else:
            plan_label = "Trial"
            plan_class = "trial"
            if days_left is not None:
                plan_meta = f"{days_left} days left"
            elif trial_end:
                plan_meta = f"Ends {trial_end.strftime('%b %d, %Y')}"
    elif plan_status != "active":
        if is_locked:
            plan_label = "Locked"
            plan_class = "locked"
            plan_meta = "Subscription required"
        else:
            plan_label = "Trial"
            plan_class = "trial"

    plan_badge_html = f'<div class="plan-badge {plan_class}">{html.escape(plan_label)}</div>'
    plan_meta_html = f'<div class="plan-meta">{html.escape(plan_meta)}</div>' if plan_meta else ""

    if user_picture:
        avatar_html = (
            '<div class="user-avatar-wrap">'
            f'<img class="user-avatar" src="{html.escape(user_picture)}" alt="avatar" '
            'onerror="this.style.display=\\"none\\";'
            'this.nextElementSibling.style.display=\\"flex\\";" />'
            f'<div class="user-avatar placeholder user-avatar-fallback">{html.escape(initial)}</div>'
            "</div>"
        )
    else:
        avatar_html = f'<div class="user-avatar placeholder">{html.escape(initial)}</div>'

    render_top_bar(
        logo_html=logo_html,
        avatar_html=avatar_html,
        user_name=user_name,
        user_email=user_email,
        plan_badge_html=plan_badge_html,
        plan_meta_html=plan_meta_html,
    )

    show_admin_sidebar = bool(is_admin or (bool(user.get("bypass")) and is_localhost_fn()))
    render_admin_sidebar_left(
        show=show_admin_sidebar,
        is_admin=is_admin,
        is_localhost=is_localhost_fn(),
        user_name=user_name,
        user_email=user_email,
        user_picture=user_picture,
        initial=initial,
        project_count=project_count,
        project_limit=PROJECT_LIMIT,
        on_render_dev_switcher=(
            (lambda: render_dev_switcher_fn("admin_sidebar", user))
            if render_dev_switcher_fn and is_localhost_fn()
            else None
        ),
    )

    if plan_status == "trialing":
        locked_cta_label = "Start subscription"
    elif plan_status == "active":
        locked_cta_label = "Renew subscription"
    else:
        locked_cta_label = "Subscription required"

    if is_locked:
        cta_button_html = f'<a class="cta-button" href="/Billing">{locked_cta_label}</a>'
    else:
        cta_button_html = '<a class="cta-button" href="?create=1">Create project</a>'

    render_hero(
        cta_button_html=cta_button_html,
        project_count=project_count,
        project_limit=PROJECT_LIMIT,
    )

    flash_message = st.session_state.pop("project_flash", None)
    if flash_message:
        st.success(flash_message)

    if account and account.get("referral_code"):
        referral_link = f"{base_url()}/?ref={account['referral_code']}"
        with st.expander("Referral link", expanded=False):
            st.caption("Share this link to grant a bonus month on the first paid month.")
            st.code(referral_link)

    if is_truthy(create_param):
        if is_locked:
            st.warning("Subscription required to create projects.")
        else:
            open_create_dialog(
                project_count=project_count,
                project_limit=PROJECT_LIMIT,
                owner_id=owner_id,
                account_id=user.get("billing_account_id"),
                clear_query_params_fn=clear_query_params,
            )

    grid_placeholder = st.empty()
    cards: list[str] = []
    filtered: list[dict] = []
    for p in projects:
        pid = p.get("id")
        if not pid:
            continue

        name_html = html.escape(p.get("name", "Untitled"))
        updated_label_html = html.escape(format_updated(p.get("updated_at")))

        file_path_value = p.get("file_path")
        file_name = (p.get("file_name") or "").strip()
        if not file_name and file_path_value:
            file_name = Path(file_path_value).name

        file_chip_html = (
            f'<div class="project-file-chip" title="{html.escape(file_name)}">'
            f'{html.escape(file_name)}'
            "</div>"
            if file_name
            else '<div class="project-file-chip empty">No file uploaded</div>'
        )

        card_html = clean_html_block(
            f"""
<div class="project-card">
  <a class="project-card-link" href="/?project={html.escape(pid)}" aria-label="Open project"></a>
  <div class="project-card-content">
    <div class="project-name">{name_html}</div>
    {file_chip_html}
    <div class="project-meta">Updated {updated_label_html}</div>
  </div>
</div>
"""
        )
        cards.append(card_html)
        filtered.append(p)

    render_html(grid_placeholder, f'<div class="project-grid">{"".join(cards)}</div>')
    debug_log("projects: rendered placeholder grid")

    status_cache: dict[str | None, tuple[str, str, str | None]] = {}
    for p in projects:
        fp = p.get("file_path")
        if not file_exists(fp):
            status_cache[p.get("id")] = ("Needs upload", "warn", None)
            continue
        status_cache[p.get("id")] = ("Unchecked", "warn", "Validation not run.")

    filtered = sort_projects(filtered, "Recently updated")

    if is_locked and plan_status == "trialing":
        locked_label = "Trial ended"
    elif is_locked and plan_status == "active":
        locked_label = "Subscription ended"
    else:
        locked_label = "Subscription required"

    with grid_placeholder.container():
        grid_columns = 3
        cols = st.columns(grid_columns, gap="large")
        card_index = 0

        for p in filtered:
            pid = p.get("id")
            if not pid:
                continue

            current_name = p.get("name", "Untitled")
            name_html = html.escape(current_name)
            updated_label_html = html.escape(format_updated(p.get("updated_at")))

            status_label, status_class, status_detail = status_cache.get(pid, project_status(p))

            file_path_value = p.get("file_path")
            file_name = (p.get("file_name") or "").strip()
            if not file_name and file_path_value:
                file_name = Path(file_path_value).name

            file_chip_html = (
                f'<div class="project-file-chip" title="{html.escape(file_name)}">'
                f'{html.escape(file_name)}'
                "</div>"
                if file_name
                else '<div class="project-file-chip empty">No file uploaded</div>'
            )

            detail_line_html = f'<div class="project-meta">{html.escape(status_detail)}</div>' if status_detail else ""
            badge_class = f"project-badge {status_class}".strip()

            card_class = "project-card is-locked" if is_locked else "project-card"
            card_link = (
                f'<a class="project-card-link" href="/?project={html.escape(pid)}" aria-label="Open project"></a>'
                if not is_locked
                else ""
            )
            lock_html = f'<div class="project-card-lock">{locked_label}</div>' if is_locked else ""
            action_label = "Locked" if is_locked else project_action(status_label)

            card_html = clean_html_block(
                f"""
<div class="{card_class}">
  {card_link}
  {lock_html}
  <div class="project-card-content">
    <div class="project-name">{name_html}</div>
    {file_chip_html}
    <div class="project-meta">Updated {updated_label_html}</div>
  </div>
</div>
"""
            )

            col = cols[card_index % grid_columns]
            with col:
                with st.container(key=f"wrap_{pid}"):
                    with st.container(key=f"card_{pid}"):
                        if not is_locked:
                            with st.container(key=f"actions_{pid}"):
                                project_actions_popover(
                                    project_id=pid,
                                    current_name=current_name,
                                    owner_id=owner_id,
                                )
                        st.markdown(card_html, unsafe_allow_html=True)
            card_index += 1

        col = cols[card_index % grid_columns]
        with col:
            with st.container(key="card_create"):
                if project_count < PROJECT_LIMIT:
                    if is_locked:
                        create_html = clean_html_block(
                            f"""
<div class="project-card create-card is-disabled is-locked">
  <div class="project-card-lock">{locked_label}</div>
  <div class="project-card-content">
    <div class="project-name">Create new project</div>
    <div class="project-meta">Subscription required</div>
  </div>
</div>
"""
                        )
                        st.markdown(create_html, unsafe_allow_html=True)
                    else:
                        create_link = (
                            '<div class="project-card-toolbar">'
                            '<a class="project-card-tool" href="?create=1">Create</a>'
                            "</div>"
                        )
                        create_html = clean_html_block(
                            f"""
<div class="project-card create-card">
  <a class="project-card-link" href="?create=1" aria-label="Create project"></a>
  {create_link}
  <div class="project-card-content">
    <div class="project-name">Create new project</div>
    <div class="project-meta">Limit {PROJECT_LIMIT} projects</div>
    <div class="project-action">Launch builder</div>
  </div>
</div>
"""
                        )
                        st.markdown(create_html, unsafe_allow_html=True)
                else:
                    limit_html = clean_html_block(
                        f"""
<div class="project-card create-card is-disabled">
  <div class="project-name">Project limit reached</div>
  <div class="project-meta">Limit {PROJECT_LIMIT} projects</div>
</div>
"""
                    )
                    st.markdown(limit_html, unsafe_allow_html=True)

    if _debug:
        st.caption("Debug enabled.")
