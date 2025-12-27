import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

import streamlit as st

st.session_state["_page_override"] = "S-Curve"
st.session_state["_page_source"] = "S-Curve"
runpy.run_path(ROOT / "app.py", run_name="__main__")
st.session_state.pop("_page_override", None)
st.session_state.pop("_page_source", None)
