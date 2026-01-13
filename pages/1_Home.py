from pathlib import Path
import streamlit as st
from auth_google import _render_home_screen, require_login

_icon_path = Path(__file__).resolve().parents[1] / "chronoplan_logo.png"
st.set_page_config(
    page_title="ChronoPlan",
    page_icon=str(_icon_path) if _icon_path.exists() else "CP",
    layout="wide",
)

st.session_state["_current_page"] = "Home"

def _get_query_params() -> dict:
    return dict(st.query_params)

def _query_value(params: dict, key: str) -> str | None:
    val = params.get(key)
    return val

def _clear_query_params() -> None:
    st.query_params.clear()

# Check if user is logged in (dev or OIDC)
user = require_login(force_login=False)
if user:
    st.switch_page("pages/0_Projects.py")
    st.stop()

# Handle login click (same tab)
params = _get_query_params()
login_param = _query_value(params, "login")
if login_param == "1":
    _clear_query_params()
    st.login("google")
    st.stop()

# Render styled home with HTML CTA that calls ?login=1
_render_home_screen(auth_url="?login=1", user=None)
