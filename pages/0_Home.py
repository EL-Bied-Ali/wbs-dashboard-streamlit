from pathlib import Path

import streamlit as st

from auth_google import _load_config, get_current_user, _render_home_screen, _build_start_oauth_url

_icon_path = Path(__file__).resolve().parents[1] / "chronoplan_logo.png"
st.set_page_config(
    page_title="Wibis",
    page_icon=str(_icon_path) if _icon_path.exists() else "🧭",
    layout="wide",
)
st.markdown(
    "<style>[data-testid='stSidebarNav']{display:none !important;}</style>",
    unsafe_allow_html=True,
)

cfg = _load_config()
auth_url = _build_start_oauth_url(cfg)
user = get_current_user()

_render_home_screen(auth_url, user=user)

if st.secrets.get("AUTH_DEBUG", "").lower() == "true":
    st.sidebar.markdown("### Auth debug")
    st.sidebar.json(st.session_state.get("_auth_debug", {}))
