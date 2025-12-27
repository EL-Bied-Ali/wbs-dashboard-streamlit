import streamlit as st

from auth_google import _build_login_url, _get_cookie_manager, _load_config, get_current_user, _render_home_screen

st.set_page_config(page_title="Home", layout="wide")
st.markdown(
    "<style>[data-testid='stSidebarNav']{display:none !important;}</style>",
    unsafe_allow_html=True,
)

cfg = _load_config()
cookies = _get_cookie_manager(refresh=True)
auth_url = _build_login_url(cfg, cookies)
user = get_current_user()

_render_home_screen(auth_url, user=user)

if st.secrets.get("AUTH_DEBUG", "").lower() == "true":
    st.sidebar.markdown("### Auth debug")
    st.sidebar.json(st.session_state.get("_auth_debug", {}))
