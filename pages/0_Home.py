from pathlib import Path

import streamlit as st

from auth_google import require_login


_icon_path = Path(__file__).resolve().parents[1] / "chronoplan_logo.png"
st.set_page_config(
    page_title="Wibis",
    page_icon=str(_icon_path) if _icon_path.exists() else "胑臝",
    layout="wide",
)
st.markdown(
    "<style>[data-testid='stSidebarNav']{display:none !important;}</style>",
    unsafe_allow_html=True,
)

st.session_state.pop("_force_home", None)
user = require_login()

if user:
    st.markdown(
        "<script>window.location.replace('/');</script>",
        unsafe_allow_html=True,
    )
    st.stop()
