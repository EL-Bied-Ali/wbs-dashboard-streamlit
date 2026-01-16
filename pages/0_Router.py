# pages/0_Router.py
from pathlib import Path
import os
import streamlit as st
from auth_google import require_login
from backup_r2 import lazy_daily_backup
from runtime_checks import check_billing_db_integrity, validate_runtime_config

_icon_path = Path(__file__).resolve().parents[1] / "chronoplan_logo.png"
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
project_param = _query_value(params, "project")

# Use require_login to detect dev bypass or OIDC
user = require_login(force_login=False)

if _get_secret("ENABLE_R2_BACKUPS") == "1" and (user is None or _is_admin_user(user)):
    lazy_daily_backup()

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
