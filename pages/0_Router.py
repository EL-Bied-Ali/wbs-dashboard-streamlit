# pages/0_Router.py
from pathlib import Path
import streamlit as st
from auth_google import require_login

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

def _get_query_params() -> dict:
    return dict(st.query_params)

def _query_value(params: dict, key: str) -> str | None:
    val = params.get(key)
    return val

params = _get_query_params()
project_param = _query_value(params, "project")

# Use require_login to detect dev bypass or OIDC
user = require_login(force_login=False)

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
