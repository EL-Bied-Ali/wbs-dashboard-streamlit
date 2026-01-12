from pathlib import Path

import streamlit as st
from auth_google import require_login


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

st.session_state["_current_page"] = "Home"
user = require_login()

# IMPORTANT: si on arrive avec /?project=XXX, on ouvre directement le dashboard
params = _get_query_params()
project_param = _query_value(params, "project")
if user and project_param:
    st.session_state["active_project_id"] = project_param
    st.switch_page("app.py")
    st.stop()

# Sinon, Home sert juste de “landing” et renvoie une seule fois vers Projects
if user and not st.session_state.get("_did_home_redirect"):
    st.session_state["_did_home_redirect"] = True
    st.switch_page("pages/0_Projects.py")
    st.stop()
