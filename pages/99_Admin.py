from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone

import streamlit as st

from auth_google import require_login
from billing_store import (
    delete_account_by_email,
    list_accounts,
    list_events,
    list_referrals,
    update_account_plan,
)


st.set_page_config(
    page_title="ChronoPlan Admin",
    page_icon="CP",
    layout="wide",
)
st.markdown(
    "<style>[data-testid='stSidebarNav']{display:none !important;}</style>",
    unsafe_allow_html=True,
)


def _admin_emails() -> set[str]:
    emails = {"ali.el.bied9898@gmail.com"}
    raw = os.environ.get("ADMIN_EMAILS", "")
    if not raw:
        try:
            raw = st.secrets.get("ADMIN_EMAILS", "")
        except Exception:
            raw = ""
    for email in raw.split(","):
        cleaned = email.strip().lower()
        if cleaned:
            emails.add(cleaned)
    return {email.lower() for email in emails if email}


def _is_admin(user: dict | None) -> bool:
    if not user:
        return False
    if user.get("bypass"):
        return True
    email = (user.get("email") or "").lower()
    return email in _admin_emails()


def _base_url() -> str:
    raw = os.environ.get("APP_URL", "")
    if not raw:
        try:
            raw = st.secrets.get("APP_URL", "")
        except Exception:
            raw = ""
    if raw:
        return raw.rstrip("/")
    host = st.get_option("server.address") or "localhost"
    port = st.get_option("server.port") or 8501
    return f"http://{host}:{port}"


user = require_login()
if not _is_admin(user):
    st.warning("Admin access required.")
    st.stop()

accounts = list_accounts()
referrals = list_referrals()
events = list_events()

total_accounts = len(accounts)
trialing = sum(1 for a in accounts if a.get("plan_status") == "trialing")
active = sum(1 for a in accounts if a.get("plan_status") == "active")
total_referrals = len(referrals)
total_events = len(events)

st.markdown("# Admin stats")
metric_cols = st.columns(5)
metric_cols[0].metric("Accounts", total_accounts)
metric_cols[1].metric("Trialing", trialing)
metric_cols[2].metric("Active", active)
metric_cols[3].metric("Referrals", total_referrals)
metric_cols[4].metric("Events", total_events)

st.markdown("### Plan controls")
if accounts:
    email_options = [a.get("email") for a in accounts if a.get("email")]
    selected_email = st.selectbox(
        "Account email",
        email_options,
        key="admin_plan_email",
    )
    action = st.radio(
        "Plan action",
        [
            "Activate (premium)",
            "End subscription (yesterday)",
            "Custom subscription end",
            "Start trial (15 days)",
            "End trial (yesterday)",
            "Custom trial end",
        ],
        key="admin_plan_action",
        horizontal=True,
    )
    trial_date = None
    plan_date = None
    if action == "Custom trial end":
        trial_date = st.date_input(
            "Trial end date (UTC)",
            value=date.today() + timedelta(days=15),
            key="admin_plan_date",
        )
    elif action == "Custom subscription end":
        plan_date = st.date_input(
            "Subscription end date (UTC)",
            value=date.today() + timedelta(days=30),
            key="admin_plan_end_date",
        )
    if st.button("Apply plan", key="admin_plan_apply"):
        now = datetime.now(timezone.utc).replace(microsecond=0)
        ok = False
        if action == "Activate (premium)":
            ok = update_account_plan(selected_email, "active", None, now + timedelta(days=30))
        elif action == "End subscription (yesterday)":
            ok = update_account_plan(selected_email, "active", None, now - timedelta(days=1))
        elif action == "Custom subscription end" and plan_date:
            plan_end = datetime.combine(plan_date, datetime.min.time(), tzinfo=timezone.utc)
            ok = update_account_plan(selected_email, "active", None, plan_end)
        elif action == "Start trial (15 days)":
            ok = update_account_plan(selected_email, "trialing", now + timedelta(days=15))
        elif action == "End trial (yesterday)":
            ok = update_account_plan(selected_email, "trialing", now - timedelta(days=1))
        elif action == "Custom trial end" and trial_date:
            trial_end = datetime.combine(trial_date, datetime.min.time(), tzinfo=timezone.utc)
            ok = update_account_plan(selected_email, "trialing", trial_end)
        if ok:
            st.success("Plan updated.")
            st.rerun()
        else:
            st.warning("No billing account found for that email.")
else:
    st.caption("No accounts yet.")

st.markdown("### Reset billing data")
st.warning(
    "This permanently deletes billing, referral, and subscription data for the email. "
    "Projects owned by this account will become inaccessible."
)
reset_email = st.text_input("Account email", key="admin_reset_email")
confirm_text = st.text_input("Type DELETE to confirm", key="admin_reset_confirm")
if st.button("Delete billing data", key="admin_reset_btn"):
    if not reset_email.strip():
        st.warning("Enter an email to delete.")
    elif confirm_text.strip() != "DELETE":
        st.warning("Type DELETE to confirm.")
    elif delete_account_by_email(reset_email):
        st.success("Billing data deleted.")
    else:
        st.info("No billing account found for that email.")

if user and user.get("email"):
    user_account = next((a for a in accounts if a.get("email") == user.get("email")), None)
    if user_account and user_account.get("referral_code"):
        link = f"{_base_url()}/?ref={user_account['referral_code']}"
        st.markdown("### Your referral link")
        st.code(link)

st.markdown("### Accounts")
st.dataframe(
    [
        {
            "id": a.get("id"),
            "email": a.get("email"),
            "name": a.get("name"),
            "plan_status": a.get("plan_status"),
            "trial_end": a.get("trial_end"),
            "plan_end": a.get("plan_end"),
            "referral_code": a.get("referral_code"),
            "referrer_code": a.get("referrer_code"),
            "created_at": a.get("created_at"),
            "last_seen": a.get("last_seen"),
        }
        for a in accounts
    ],
    use_container_width=True,
    hide_index=True,
)

st.markdown("### Referrals")
st.dataframe(
    [
        {
            "referrer": r.get("referrer_email"),
            "referee": r.get("referee_email"),
            "referral_code": r.get("referral_code"),
            "created_at": r.get("created_at"),
            "activated_at": r.get("activated_at"),
            "reward_months": r.get("reward_months"),
        }
        for r in referrals
    ],
    use_container_width=True,
    hide_index=True,
)

st.markdown("### Recent events")
st.dataframe(
    [
        {
            "account_id": e.get("account_id"),
            "event_type": e.get("event_type"),
            "created_at": e.get("created_at"),
            "metadata": e.get("metadata"),
        }
        for e in events
    ],
    use_container_width=True,
    hide_index=True,
)
