from __future__ import annotations

import os
import urllib.parse
from typing import Any

import streamlit as st


def get_query_params() -> dict[str, Any]:
    return dict(st.query_params)


def query_value(params: dict[str, Any], key: str) -> str | None:
    val = params.get(key)
    if val is None:
        return None
    return str(val)


def clear_query_params() -> None:
    st.query_params.clear()


def get_params() -> dict[str, str]:
    return dict(st.query_params)


def set_params_merge(**updates):
    for k, v in updates.items():
        if v is None:
            st.query_params.pop(k, None)
        else:
            st.query_params[k] = str(v)


def del_params(*keys):
    for k in keys:
        st.query_params.pop(k, None)


def is_truthy(value: str | None) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def base_url() -> str:
    raw = os.environ.get("APP_URL", "")
    if not raw:
        try:
            raw = st.secrets.get("APP_URL", "")
        except Exception:
            raw = ""

    if raw:
        return raw.rstrip("/")

    host = st.get_option("server.address") or "localhost"
    port = st.get_option("server.port") or 8501
    return f"http://{host}:{port}"


def redirect_to_project(project_id: str) -> None:
    safe_id = urllib.parse.quote(project_id, safe="")
    st.markdown(
        f"""
<script>
  window.location.replace("/?project={safe_id}");
</script>
""",
        unsafe_allow_html=True,
    )
    st.stop()
