from pathlib import Path
import streamlit as st
from auth_google import _render_home_screen

_icon_path = Path(__file__).resolve().parents[1] / "chronoplan_logo.png"
st.set_page_config(
    page_title="ChronoPlan",
    page_icon=str(_icon_path) if _icon_path.exists() else "CP",
    layout="wide",
)

st.session_state["_current_page"] = "Home"

def _get_query_params() -> dict:
    try:
        return st.query_params  # type: ignore[attr-defined]
    except AttributeError:
        return st.experimental_get_query_params()

def _query_value(params: dict, key: str) -> str | None:
    val = params.get(key)
    if isinstance(val, list):
        return val[0] if val else None
    return val

def _clear_query_params() -> None:
    try:
        st.query_params.clear()  # type: ignore[attr-defined]
    except Exception:
        st.experimental_set_query_params()

# If already logged in via OIDC, skip Home
user_obj = getattr(st, "user", None)
is_logged_in = bool(user_obj and getattr(user_obj, "is_logged_in", False))
if is_logged_in:
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
