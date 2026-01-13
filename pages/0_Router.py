# pages/0_Router.py
from pathlib import Path
import streamlit as st

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
    try:
        return st.query_params  # type: ignore[attr-defined]
    except AttributeError:
        return st.experimental_get_query_params()

def _query_value(params: dict, key: str) -> str | None:
    val = params.get(key)
    if isinstance(val, list):
        return val[0] if val else None
    return val

params = _get_query_params()
project_param = _query_value(params, "project")

user_obj = getattr(st, "user", None)
is_logged_in = bool(user_obj and getattr(user_obj, "is_logged_in", False))

if is_logged_in and project_param:
    st.session_state["active_project_id"] = project_param
    st.switch_page("pages/10_Dashboard.py")
    st.stop()

if is_logged_in:
    st.switch_page("pages/0_Projects.py")
    st.stop()

st.switch_page("pages/1_Home.py")
st.stop()
