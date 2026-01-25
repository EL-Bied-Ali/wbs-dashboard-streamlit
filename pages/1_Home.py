from pathlib import Path
import streamlit as st
from auth_google import _render_home_screen, _stash_referral_code, require_login
from projects_page.styles import inject_global_css

_icon_path = Path(__file__).resolve().parents[1] / "Chronoplan_ico.png"
st.set_page_config(
    page_title="ChronoPlan",
    page_icon=str(_icon_path) if _icon_path.exists() else "CP",
    layout="wide",
)
inject_global_css()

st.session_state["_current_page"] = "Home"

def _get_query_params() -> dict:
    return dict(st.query_params)

def _query_value(params: dict, key: str) -> str | None:
    val = params.get(key)
    return val

def _clear_query_params() -> None:
    st.query_params.clear()

params = _get_query_params()
print("[HOME] incoming query params:", params)
_stash_referral_code(params)
print("[HOME] stashed referral (if any)")

# Check if user is logged in (dev or OIDC)
user = require_login(force_login=False)
if user:
    st.switch_page("pages/0_Projects.py")
    st.stop()

# Handle login click (same tab)
login_param = _query_value(params, "login")
if login_param == "1":
    ref = _query_value(params, "ref")
    print("[HOME] login clicked, ref in URL =", ref)
    st.query_params.clear()
    if ref:
        st.query_params["ref"] = ref
        print("[HOME] restored ref in URL before login:", ref)
    else:
        print("[HOME] NO ref to restore before login")
    print("[HOME] calling st.login('google')")
    st.login("google")
    st.stop()

# Render styled home with HTML CTA that calls ?login=1
ref = _query_value(params, "ref")
auth_url = f"?login=1&ref={ref}" if ref else "?login=1"
_render_home_screen(auth_url=auth_url, user=None)
