from __future__ import annotations

import os

import streamlit as st
from auth_google import (
    forget_dev_user,
    list_dev_users,
    remember_dev_user,
    switch_dev_user,
)
from billing_store import delete_account_by_email
from projects_page.page import render_projects_page
from projects_page.routing import get_query_params, query_value


st.set_page_config(
    page_title="ChronoPlan Projects",
    page_icon="CP",
    layout="wide",
)


def _get_query_params() -> dict:
    return get_query_params()


def _query_value(params: dict, key: str) -> str | None:
    return query_value(params, key)


def _admin_emails() -> set[str]:
    emails = {"ali.el.bied9898@gmail.com"}
    raw = os.environ.get("ADMIN_EMAILS", "")
    if not raw:
        return emails

    for email in raw.split(","):
        cleaned = email.strip().lower()
        if cleaned:
            emails.add(cleaned)

    return {email.lower() for email in emails if email}


def _is_admin_user(user: dict | None) -> bool:
    if not user:
        return False
    email = (user.get("email") or "").lower()
    return email in _admin_emails()


def _is_localhost() -> bool:
    host = st.get_option("server.address") or "localhost"
    return host in {"localhost", "127.0.0.1", "0.0.0.0"}


def _render_dev_switcher_ui(prefix: str, user: dict | None) -> None:
    if not user:
        return

    email_current = (user.get("email") or "").strip()
    name_current = (user.get("name") or "").strip()
    if email_current:
        remember_dev_user(email_current, name_current)

    params_local = _get_query_params()

    email_input = st.text_input(
        "Dev email",
        value="",
        key=f"{prefix}_dev_email",
    )
    name_input = st.text_input(
        "Dev name",
        value="",
        key=f"{prefix}_dev_name",
    )
    ref_input = st.text_input(
        "Referral code (optional)",
        value=_query_value(params_local, "ref") or "",
        key=f"{prefix}_dev_ref",
    )

    if st.button("Switch user", key=f"{prefix}_dev_switch_btn"):
        if email_input.strip():
            switch_dev_user(email_input, name_input, ref_input)
        else:
            st.warning("Enter an email to switch.")

    if st.button("Clear dev user", key=f"{prefix}_dev_clear_btn"):
        try:
            st.query_params.clear()  # type: ignore[attr-defined]
        except AttributeError:
            st.experimental_set_query_params()
        st.rerun()

    saved_users = list_dev_users()
    if saved_users:
        st.markdown("**Saved accounts**")
        for idx, entry in enumerate(saved_users):
            email_value = entry.get("email", "")
            name_value = entry.get("name", "")
            label = name_value or email_value
            cols = st.columns([3, 1, 1], gap="small")

            if name_value:
                cols[0].markdown(f"**{label}**\n\n{email_value}")
            else:
                cols[0].markdown(f"**{label}**")

            if cols[1].button("Switch", key=f"{prefix}_saved_switch_{idx}"):
                switch_dev_user(email_value, name_value, ref_input)

            if cols[2].button("Forget", key=f"{prefix}_saved_forget_{idx}"):
                forget_dev_user(email_value)
                st.rerun()

        with st.expander("Reset account data", expanded=False):
            options = [u.get("email", "") for u in saved_users if u.get("email")]
            target = st.selectbox(
                "Account email",
                options,
                key=f"{prefix}_reset_email",
            )
            confirm = st.checkbox(
                "I understand this deletes billing data for this email.",
                key=f"{prefix}_reset_confirm",
            )
            if st.button("Delete billing data", key=f"{prefix}_reset_btn"):
                if not confirm:
                    st.warning("Confirm the delete first.")
                elif delete_account_by_email(target):
                    st.success("Billing data deleted.")
                else:
                    st.info("No billing account found for that email.")
    else:
        st.caption("No saved accounts yet.")


render_projects_page(
    is_admin_user_fn=_is_admin_user,
    is_localhost_fn=_is_localhost,
    render_dev_switcher_fn=_render_dev_switcher_ui,
)
