# pages/0_Router.py
from pathlib import Path
import os
import streamlit as st
from auth_google import _stash_referral_code, require_login
from backup_r2 import lazy_daily_backup, guard_backup_on_data_loss, auto_restore_on_data_loss
from runtime_checks import check_billing_db_integrity, validate_runtime_config

_icon_path = Path(__file__).resolve().parents[1] / "Chronoplan_ico.png"
st.set_page_config(
    page_title="ChronoPlan",
    page_icon=str(_icon_path) if _icon_path.exists() else "CP",
    layout="wide",
)

st.markdown(
    "<style>[data-testid='stSidebarNav']{display:none !important;}</style>",
    unsafe_allow_html=True,
)

st.session_state["_current_page"] = "Router"

def _get_secret(key: str) -> str:
    raw = os.environ.get(key, "")
    if not raw:
        try:
            raw = st.secrets.get(key, "")
        except Exception:
            raw = ""
    return raw


def _admin_emails() -> set[str]:
    emails = {"ali.el.bied9898@gmail.com"}
    raw = _get_secret("ADMIN_EMAILS")
    if raw:
        emails.update({e.strip().lower() for e in raw.split(",") if e.strip()})
    return emails


def _is_admin_user(user: dict | None) -> bool:
    if not user:
        return False
    email = (user.get("email") or "").strip().lower()
    return bool(email) and email in _admin_emails()

validate_runtime_config(checkout_enabled=False)
check_billing_db_integrity()

def _get_query_params() -> dict:
    return dict(st.query_params)

def _query_value(params: dict, key: str) -> str | None:
    val = params.get(key)
    return val

params = _get_query_params()
_stash_referral_code(params)
project_param = _query_value(params, "project")

# Use require_login to detect dev bypass or OIDC
user = require_login(force_login=False)

if _get_secret("ENABLE_R2_BACKUPS") == "1":
    # If data loss detected, try auto-restore before taking a guard backup.
    auto_restore_on_data_loss()
    guard_backup_on_data_loss()
    if user is None or _is_admin_user(user):
        try:
            lazy_daily_backup()
        except Exception as err:
            import logging
            logging.getLogger("backup_r2").warning(f"lazy_daily_backup failed: {err}")

# Debug: uncomment to validate auth source
# st.info(f"Auth debug: {get_auth_debug_info(user)}")

# If logged in and project specified, go to Dashboard
if user and project_param:
    st.session_state["active_project_id"] = project_param
    st.switch_page("pages/10_Dashboard.py")
    st.stop()

# If logged in, go to Projects
if user:
    st.switch_page("pages/0_Projects.py")
    st.stop()

# Not logged in, go to Home
st.switch_page("pages/1_Home.py")
st.stop()
