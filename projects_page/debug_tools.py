from __future__ import annotations

import os
import time
from time import perf_counter

import streamlit as st


def debug_enabled() -> bool:
    try:
        params = st.query_params  # type: ignore[attr-defined]
    except Exception:
        params = st.experimental_get_query_params()

    raw = params.get("debug")
    if isinstance(raw, list):
        raw = raw[0] if raw else None

    raw = (raw or os.getenv("CP_DEBUG", "")).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def debug_log(message: str) -> None:
    if not st.session_state.get("_debug_logs"):
        st.session_state["_debug_logs"] = []

    ts = time.strftime("%H:%M:%S")
    line = f"{ts} {message}"
    st.session_state["_debug_logs"].append(line)
    st.session_state["_debug_logs"] = st.session_state["_debug_logs"][-200:]


def timeit(label: str, fn, timings: list[tuple[str, float]]):
    start = perf_counter()
    out = fn()
    timings.append((label, (perf_counter() - start) * 1000.0))
    return out
