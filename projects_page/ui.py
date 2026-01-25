from __future__ import annotations

import html as _html
from typing import Callable, Optional

import streamlit as st


def render_top_bar(
    *,
    logo_html: str,
    avatar_html: str,
    user_name: str,
    user_email: str,
    plan_badge_html: str,
    plan_meta_html: str,
) -> None:
    email_html = f'<div class="user-email">{_html.escape(user_email)}</div>' if user_email else ""

    top_bar_html = f"""
<div class="top-bar">
  {logo_html}
  <div class="top-account">
    <div class="top-account-info">
      {avatar_html}
      <div class="user-info">
        <div class="user-name">{_html.escape(user_name)}</div>
        {email_html}
        {plan_badge_html}
        {plan_meta_html}
      </div>
    </div>
    <div class="top-actions">
      <a class="top-link" href="/Billing">Billing</a>
      <a class="signout-btn" href="?logout=1" title="Sign out" aria-label="Sign out">⏻</a>
    </div>
  </div>
</div>
"""
    st.html(top_bar_html)


def render_hero(*, cta_button_html: str = "", project_count: int, project_limit: int, on_render_cta: Optional[Callable[[], None]] = None) -> None:
    """Render the hero area.

    If on_render_cta is provided, it will be called to render the CTA widget
    (e.g. a popover trigger) inside the CTA column. Otherwise the provided
    raw `cta_button_html` string will be used.
    """
    cols = st.columns([3, 1])
    with cols[0]:
        st.markdown("<h1 class=\"project-title\">Pick your next project</h1>", unsafe_allow_html=True)
        st.markdown("<div class=\"project-sub\">Build dashboards per client or per timeline.</div>", unsafe_allow_html=True)
    with cols[1]:
        if on_render_cta:
            # Let the caller render an interactive CTA (e.g., st.popover)
            on_render_cta()
        else:
            # Fallback to raw HTML CTA for older code paths
            if cta_button_html:
                st.html(cta_button_html)
        st.markdown(f"<div class=\"ghost-chip\">Projects {project_count}/{project_limit}</div>", unsafe_allow_html=True)


def render_admin_sidebar_left(
    *,
    show: bool,
    is_admin: bool,
    is_localhost: bool,
    user_name: str,
    user_email: str,
    user_picture: str | None,
    initial: str,
    project_count: int,
    project_limit: int,
    admin_stats_href: str = "/Admin",
    on_render_dev_switcher: Callable[[], None] | None = None,
) -> None:
    if not show:
        return

    if user_picture:
        avatar_html = (
            '<div class="admin-avatar-wrap">'
            f'<img class="admin-avatar" src="{_html.escape(user_picture)}" alt="avatar" '
            'onerror="this.style.display=\\"none\\";'
            'this.nextElementSibling.style.display=\\"flex\\";" />'
            f'<div class="admin-avatar placeholder admin-avatar-fallback">{_html.escape(initial)}</div>'
            "</div>"
        )
    else:
        avatar_html = f'<div class="admin-avatar placeholder">{_html.escape(initial)}</div>'

    email_html = f'<div class="admin-email">{_html.escape(user_email)}</div>' if user_email else ""
    access_label = "Admin access" if is_admin else "Dev access"
    badge_label = "Admin" if is_admin else "Dev"
    tools_label = "Admin tools" if is_admin else "Dev tools"
    admin_sidebar_html = f"""
<div class="admin-sidebar">
  <div class="admin-card">
    <div class="admin-card-title">{access_label}</div>
    <div class="admin-user">
      {avatar_html}
      <div class="admin-user-info">
        <div class="admin-name-row">
          <div class="admin-name">{_html.escape(user_name)}</div>
          <span class="admin-badge">{badge_label}</span>
        </div>
        {email_html}
      </div>
    </div>
    <div class="admin-meta">Projects {project_count}/{project_limit}</div>
  </div>

  <div class="admin-card">
    <div class="admin-card-title">{tools_label}</div>
    <div class="admin-actions">
      <a class="admin-button" href="{admin_stats_href}">Open admin stats</a>
      <!-- Create project popover is rendered separately in page.py to provide owner/org context -->
    </div>
  </div>
</div>
"""

    with st.sidebar:
        st.html(admin_sidebar_html)
        if is_localhost and on_render_dev_switcher:
            with st.expander("Dev user switcher", expanded=False):
                on_render_dev_switcher()
