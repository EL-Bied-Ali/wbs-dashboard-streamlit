from pathlib import Path

import streamlit as st

from auth_google import (
    SESSION_KEY,
    _build_login_url,
    _clear_query_params,
    _exchange_code_for_user,
    _get_cookie_manager,
    _get_query_params,
    _load_config,
    _query_value,
    _rerun,
    _render_home_screen,
    _save_cookies,
    _store_user_cookie,
    get_current_user,
)

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
cookies = _get_cookie_manager(refresh=True)

params = _get_query_params()
code = _query_value(params, "code")
state = _query_value(params, "state")
if code:
    user = _exchange_code_for_user(cfg, code, state, cookies)
    _clear_query_params()
    if user:
        st.session_state[SESSION_KEY] = user
        _store_user_cookie(cookies, cfg, user, save=False)
        _save_cookies(cookies)
        try:
            st.switch_page("app.py")  # type: ignore[attr-defined]
        except Exception:
            _rerun()
        st.stop()
    _save_cookies(cookies)

user = get_current_user()
if user:
    try:
        st.switch_page("app.py")  # type: ignore[attr-defined]
    except Exception:
        _rerun()
    st.stop()

auth_url = _build_login_url(cfg, cookies)
_render_home_screen(auth_url, user=user)

if st.secrets.get("AUTH_DEBUG", "").lower() == "true":
    st.sidebar.markdown("### Auth debug")
    st.sidebar.json(st.session_state.get("_auth_debug", {}))
