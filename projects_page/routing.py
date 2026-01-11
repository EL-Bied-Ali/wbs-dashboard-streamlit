from __future__ import annotations

import os
import urllib.parse
from typing import Any

import streamlit as st


def get_query_params() -> dict[str, Any]:
    try:
        return dict(st.query_params)  # type: ignore[attr-defined]
    except Exception:
        return st.experimental_get_query_params()


def query_value(params: dict[str, Any], key: str) -> str | None:
    val = params.get(key)
    if isinstance(val, list):
        return val[0] if val else None
    if val is None:
        return None
    return str(val)


def clear_query_params() -> None:
    try:
        st.query_params.clear()  # type: ignore[attr-defined]
    except Exception:
        st.experimental_set_query_params()


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
