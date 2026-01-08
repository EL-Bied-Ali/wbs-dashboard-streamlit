from __future__ import annotations
from datetime import datetime
from pathlib import Path
import html
import os
import time
import textwrap
from time import perf_counter
import urllib.parse
import streamlit as st

from auth_google import (
    logout,
    require_login,
    _get_logo_data_uri,
    switch_dev_user,
    list_dev_users,
    forget_dev_user,
    remember_dev_user,
)
from billing_store import access_status, get_account_by_email, record_event, delete_account_by_email
from projects import (
    PROJECT_LIMIT,
    assign_projects_to_owner,
    create_project,
    delete_project,
    list_projects,
    owner_id_from_user,
    project_mapping_key,
    update_project,
)
from wbs_app.extract_wbs_json_calamine import (
    get_table_headers,
    suggest_column_mapping,
    SUMMARY_REQUIRED_FIELDS,
    ASSIGN_REQUIRED_FIELDS,
)

from excel_cache import load_headers_cache, save_headers_cache


# =============================
# PAGE CONFIG
# =============================
st.set_page_config(
    page_title="ChronoPlan Projects",
    page_icon="CP",
    layout="wide",
)
st.session_state["_current_page"] = "Projects"

def _debug_enabled() -> bool:
    try:
        params = st.query_params  # type: ignore[attr-defined]
    except Exception:
        params = st.experimental_get_query_params()
    raw = params.get("debug")
    if isinstance(raw, list):
        raw = raw[0] if raw else None
    raw = (raw or os.getenv("CP_DEBUG", "")).strip().lower()
    return raw in {"1", "true", "yes", "on"}

_debug = _debug_enabled()
_timings: list[tuple[str, float]] = []

def _debug_log(message: str) -> None:
    if not st.session_state.get("_debug_logs"):
        st.session_state["_debug_logs"] = []
    ts = time.strftime("%H:%M:%S")
    line = f"{ts} {message}"
    st.session_state["_debug_logs"].append(line)
    st.session_state["_debug_logs"] = st.session_state["_debug_logs"][-200:]
    # Note: do not write to local files here; Streamlit's file watcher can
    # trigger infinite reruns when files change (making the UI feel "stuck").

def _timeit(label: str, fn):
    start = perf_counter()
    out = fn()
    _timings.append((label, (perf_counter() - start) * 1000.0))
    return out

def _file_cache_key(path: str | None) -> tuple[float, int] | None:
    if not path:
        return None
    try:
        stat = os.stat(path)
    except OSError:
        return None
    return (stat.st_mtime, stat.st_size)

def _mapping_cache_key(mapping: dict | None) -> str:
    if not mapping:
        return ""
    try:
        import json

        return json.dumps(mapping, sort_keys=True, separators=(",", ":"))
    except Exception:
        return str(mapping)

@st.cache_data(show_spinner=False)
def _cached_table_headers(
    file_path: str,
    file_key: tuple[float, int] | None,
    table_type: str,
    mapping_key: str,
    mapping: dict[str, dict[str, str]] | None,
):
    _ = file_key
    _ = mapping_key
    return get_table_headers(
        file_path,
        table_type,
        column_mapping=mapping,
    )


def _clean_html_block(markup: str) -> str:
    cleaned = textwrap.dedent(markup).strip()
    return "\n".join(line.lstrip() for line in cleaned.splitlines())


def _render_html(container, markup: str) -> None:
    # Streamlit's markdown renderer can interpret some HTML blocks as code fences,
    # causing raw tags to show up. Use st.html for reliable rendering.
    try:
        empty_fn = getattr(container, "empty", None)
        if callable(empty_fn):
            empty_fn()
        container_fn = getattr(container, "container", None)
        if callable(container_fn):
            with container_fn():
                st.html(markup)
                return
    except Exception:
        pass

    st.html(markup)

# =============================
# GLOBAL BACKGROUND + CSS
# =============================
if not st.session_state.get("_projects_css_loaded"):
    st.markdown(
"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:wght@500;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');

:root {
  --bg: #05060B;
  --card: rgba(20, 27, 46, 0.88);
  --card-border: rgba(148, 163, 184, 0.18);
  --text: #e5e7eb;
  --muted: #8b98b4;
  --accent: #6dd5ed;
  --accent-2: #b47cff;
}

/* ===== GLOBAL ===== */
html, body {
  background: var(--bg);
}

.stApp {
  background: transparent;
  color: var(--text);
  font-family: "Space Grotesk", sans-serif;
}

/* ===== HERO BACKGROUND (FAKE PARTICLES STYLE) ===== */
body::before {
  content: "";
  position: fixed;
  inset: 0;
  background:
    radial-gradient(800px 300px at 20% 0%, rgba(109,213,237,.35), transparent 60%),
    radial-gradient(700px 260px at 80% 0%, rgba(180,124,255,.35), transparent 60%),
    radial-gradient(600px 400px at 50% 40%, rgba(109,213,237,.08), transparent 70%),
    var(--bg);
  z-index: 0;
}

/* ===== LAYERING ===== */
.stApp > header,
.stApp > div {
  position: relative;
  z-index: 1;
}

[data-testid="stHeader"] {
  background: transparent;
}

/* Hide the default page nav on the projects page */
[data-testid="stSidebarNav"] {
  display: none !important;
}

/* ===== LAYOUT ===== */
.block-container {
  max-width: 1200px;
  padding: 48px 24px 96px;
}

/* ===== HERO ===== */
.project-hero {
  display: flex;
  flex-wrap: wrap;
  gap: 32px;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 40px;
}

.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 28px;
}

.top-logo {
  height: 120px;
  width: auto;
  display: block;
}

.top-logo-text {
  font-family: "Fraunces", serif;
  font-size: 40px;
  font-weight: 700;
  color: var(--text);
}

.top-account {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 22px;
  border-radius: 18px;
  border: 1px solid rgba(148,163,184,0.2);
  background: rgba(15,23,42,0.6);
}

.top-account-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.top-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.top-link {
  font-size: 12px;
  font-weight: 600;
  color: var(--text);
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid rgba(148,163,184,0.35);
  background: rgba(15,23,42,0.45);
  text-decoration: none;
}

.top-link:hover {
  border-color: rgba(109,213,237,0.6);
}

.signout-btn {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  border: 1px solid rgba(148,163,184,0.35);
  background: rgba(15,23,42,0.5);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--muted);
  text-decoration: none;
  font-size: 18px;
}

.signout-btn:hover {
  border-color: rgba(109,213,237,0.6);
  color: var(--text);
}

.user-avatar {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  object-fit: cover;
  border: 1px solid rgba(148,163,184,0.35);
}

.user-avatar-wrap {
  position: relative;
  width: 56px;
  height: 56px;
  flex: 0 0 auto;
}

.user-avatar-wrap .user-avatar,
.user-avatar-wrap .user-avatar-fallback {
  width: 56px;
  height: 56px;
}

.user-avatar-fallback {
  position: absolute;
  inset: 0;
  display: none;
}

.user-avatar.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(109,213,237,0.12);
  color: var(--accent);
  font-weight: 700;
}

.user-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.user-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
}

.user-email {
  font-size: 14px;
  color: var(--muted);
}

.project-title {
  font-family: "Fraunces", serif;
  font-size: clamp(32px, 5vw, 54px);
  margin: 0 0 12px;
}

.project-sub {
  font-size: 16px;
  color: var(--muted);
  max-width: 520px;
}

/* ===== PLAN BADGE ===== */
.plan-badge {
  align-self: flex-start;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid rgba(148,163,184,0.25);
  background: rgba(15,23,42,0.45);
  color: var(--text);
}

.plan-badge.premium {
  border-color: rgba(34,197,94,0.35);
  background: rgba(34,197,94,0.12);
  color: #22c55e;
}

.plan-badge.trial {
  border-color: rgba(251,191,36,0.35);
  background: rgba(251,191,36,0.12);
  color: #fbbf24;
}

.plan-badge.locked {
  border-color: rgba(248,113,113,0.35);
  background: rgba(248,113,113,0.12);
  color: #f87171;
}

.plan-meta {
  font-size: 12px;
  color: var(--muted);
}

/* ===== CTA ===== */
.project-cta {
  display: flex;
  gap: 14px;
  align-items: center;
}

.cta-button {
  font-size: 14px;
  font-weight: 600;
  padding: 10px 20px;
  border-radius: 999px;
  background: linear-gradient(120deg, var(--accent), var(--accent-2));
  color: #0b0f18;
  text-decoration: none;
  box-shadow: 0 14px 36px rgba(109,213,237,.35);
}

.cta-button.is-disabled {
  opacity: 0.65;
  box-shadow: none;
  pointer-events: none;
  background: rgba(148,163,184,0.35);
  color: rgba(15,23,42,0.8);
}

.ghost-chip {
  font-size: 13px;
  color: var(--muted);
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid rgba(148,163,184,.25);
  background: rgba(15,23,42,.35);
}

#st-key-open_create_dialog_btn button {
  font-size: 14px;
  font-weight: 600;
  padding: 10px 20px;
  border-radius: 999px;
  border: none;
  background: linear-gradient(120deg, var(--accent), var(--accent-2));
  color: #0b0f18;
  box-shadow: 0 14px 36px rgba(109,213,237,.35);
}

#st-key-open_create_dialog_btn button:hover {
  filter: brightness(1.05);
}

#st-key-open_create_dialog_btn button:disabled {
  opacity: 0.65;
  box-shadow: none;
  background: rgba(148,163,184,0.35);
  color: rgba(15,23,42,0.8);
}

/* ===== GRID ===== */
.project-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 20px;
}

/* ===============================
   PREMIUM SAAS CARDS
   =============================== */

.project-card {
  position: relative;
  background: linear-gradient(
    180deg,
    rgba(30, 41, 59, 0.9),
    rgba(15, 23, 42, 0.9)
  );
  border-radius: 18px;
  padding: 18px 18px 16px 22px;
  min-height: 180px;

  border: 1px solid rgba(148,163,184,0.14);
  color: var(--text);
  text-decoration: none;

  box-shadow:
    0 4px 10px rgba(0,0,0,0.25),
    inset 0 1px 0 rgba(255,255,255,0.03);

  transition: all 0.25s ease;
}

.project-card-link {
  position: absolute;
  inset: 0;
  z-index: 1;
  border-radius: 18px;
}

.project-card-content {
  position: relative;
  z-index: 2;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 100%;
  pointer-events: none;
}

/* left status bar */
.project-card::before {
  content: "";
  position: absolute;
  top: 12px;
  bottom: 12px;
  left: 8px;
  width: 3px;
  border-radius: 2px;
  background: linear-gradient(
    180deg,
    #6dd5ed,
    #b47cff
  );
  opacity: 0.85;
}

.project-card-toolbar {
  position: absolute;
  top: 12px;
  right: 14px;
  display: flex;
  gap: 8px;
  z-index: 3;
  pointer-events: auto;
}

.project-card-tool {
  font-size: 11px;
  font-weight: 600;
  color: var(--muted);
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid rgba(148,163,184,0.25);
  background: rgba(15,23,42,0.6);
  text-decoration: none;
  pointer-events: auto;
}

.project-card-tool:hover {
  border-color: rgba(109,213,237,0.55);
  color: var(--text);
}

div[id^="st-key-card_"] {
  position: relative;
}

div[id^="st-key-card_"] div[data-testid="stButton"] {
  position: absolute;
  top: 12px;
  right: 14px;
  z-index: 4;
}

div[id^="st-key-card_"] div[data-testid="stButton"] > button {
  font-size: 11px;
  font-weight: 600;
  color: var(--muted);
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid rgba(148,163,184,0.25);
  background: rgba(15,23,42,0.6);
  box-shadow: none;
}

div[id^="st-key-card_"] div[data-testid="stButton"] > button:hover {
  border-color: rgba(109,213,237,0.55);
  color: var(--text);
}

div[id^="st-key-card_"] div[data-testid="stButton"] > button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* hover */
.project-card:hover {
  transform: translateY(-4px);
  border-color: rgba(109,213,237,0.45);
  box-shadow:
    0 12px 32px rgba(0,0,0,0.45),
    0 0 0 1px rgba(109,213,237,0.15);
}

/* title */
.project-name {
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 0.2px;
}

/* subtle metadata */
.project-meta {
  font-size: 12.5px;
  color: var(--muted);
}

/* badge – DISCREET */
.project-badge {
  align-self: flex-start;
  font-size: 11px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(109,213,237,0.12);
  color: var(--accent);
  border: 1px solid rgba(109,213,237,0.25);
}

.project-badge.warn {
  background: rgba(251,191,36,0.12);
  color: #fbbf24;
  border-color: rgba(251,191,36,0.3);
}

.project-badge.ok {
  background: rgba(34,197,94,0.12);
  color: #22c55e;
  border-color: rgba(34,197,94,0.3);
}

/* bottom action */
.project-action {
  margin-top: auto;
  font-size: 13px;
  font-weight: 600;
  color: var(--accent);
  opacity: 0.9;
  text-decoration: none;
}

.project-action:visited {
  color: var(--accent);
}

.project-action:hover {
  text-decoration: underline;
}

/* modal */
.manage-modal-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--text);
}

.manage-modal-sub {
  color: var(--muted);
  font-size: 13px;
}

.manage-modal-label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  color: var(--muted);
}

#st-key-manage_modal_root {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

#st-key-create_modal_root {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

div[id^="st-key-manage_rename_"],
div[id^="st-key-manage_danger_"] {
  padding: 14px;
  border-radius: 14px;
  border: 1px solid rgba(148,163,184,0.2);
  background: rgba(15,23,42,0.55);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

div[id^="st-key-manage_danger_"] {
  border-color: rgba(248,113,113,0.35);
  background: rgba(127,29,29,0.15);
}

div[id^="st-key-create_form_"] {
  padding: 14px;
  border-radius: 14px;
  border: 1px solid rgba(148,163,184,0.2);
  background: rgba(15,23,42,0.55);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

div[id^="st-key-manage_rename_"] .stTextInput input {
  background: rgba(10,15,28,0.65);
  border: 1px solid rgba(148,163,184,0.3);
  color: var(--text);
  border-radius: 10px;
}

div[id^="st-key-create_form_"] .stTextInput input {
  background: rgba(10,15,28,0.65);
  border: 1px solid rgba(148,163,184,0.3);
  color: var(--text);
  border-radius: 10px;
}

div[id^="st-key-manage_rename_"] .stButton > button,
div[id^="st-key-manage_danger_"] .stButton > button {
  border-radius: 10px;
  border: 1px solid rgba(148,163,184,0.3);
  background: rgba(15,23,42,0.6);
  color: var(--text);
  font-weight: 600;
  padding: 6px 16px;
}

div[id^="st-key-create_form_"] .stButton > button {
  border-radius: 10px;
  border: none;
  background: linear-gradient(120deg, var(--accent), var(--accent-2));
  color: #0b0f18;
  font-weight: 600;
  padding: 6px 16px;
  box-shadow: 0 10px 26px rgba(109,213,237,.3);
}

div[id^="st-key-create_form_"] .stButton > button:hover {
  filter: brightness(1.08);
}
div[id^="st-key-manage_rename_"] .stButton > button:hover,
div[id^="st-key-manage_danger_"] .stButton > button:hover {
  border-color: rgba(109,213,237,0.6);
}

div[id^="st-key-manage_save_"] .stButton > button {
  border: none;
  background: linear-gradient(120deg, var(--accent), var(--accent-2));
  color: #0b0f18;
  box-shadow: 0 10px 26px rgba(109,213,237,.3);
}

div[id^="st-key-manage_save_"] .stButton > button:hover {
  filter: brightness(1.08);
}

div[id^="st-key-manage_delete_"] .stButton > button {
  border-color: rgba(248,113,113,0.45);
  color: #fecaca;
  background: rgba(127,29,29,0.08);
}

div[id^="st-key-manage_delete_"] .stButton > button:hover {
  border-color: rgba(248,113,113,0.75);
}

div[id^="st-key-manage_confirm_"] .stButton > button,
div[id^="st-key-manage_cancel_"] .stButton > button {
  width: 36px;
  height: 36px;
  padding: 0;
  border-radius: 10px;
  border-color: rgba(148,163,184,0.35);
  background: rgba(15,23,42,0.5);
  color: var(--text);
  font-size: 12px;
  letter-spacing: 0.08em;
}

div[id^="st-key-manage_confirm_"] .stButton > button {
  border-color: rgba(248,113,113,0.75);
  color: #fecaca;
  background: rgba(248,113,113,0.18);
}

.manage-alert {
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(248,113,113,0.35);
  background: rgba(248,113,113,0.12);
  color: #fecaca;
  font-size: 12.5px;
}

div[data-testid="stDialog"] button[aria-label="Close"] {
  background: rgba(15,23,42,0.7);
  border: 1px solid rgba(148,163,184,0.3);
  color: var(--text);
  border-radius: 8px;
  box-shadow: none;
}

div[data-testid="stDialog"] button[aria-label="Close"]:hover {
  border-color: rgba(109,213,237,0.6);
  color: var(--text);
}

/* create card special */
.create-card {
  background:
    linear-gradient(
      180deg,
      rgba(15,23,42,0.75),
      rgba(15,23,42,0.55)
    );
  border-style: dashed;
}

.create-card::before {
  background: linear-gradient(
    180deg,
    rgba(148,163,184,0.4),
    rgba(148,163,184,0.1)
  );
}

.project-card.is-disabled {
  cursor: not-allowed;
  opacity: 0.7;
}

.project-card.is-locked {
  cursor: not-allowed;
  opacity: 0.75;
}

.project-card.is-locked:hover {
  transform: none;
  border-color: rgba(148,163,184,0.14);
  box-shadow:
    0 4px 10px rgba(0,0,0,0.25),
    inset 0 1px 0 rgba(255,255,255,0.03);
}

.project-card-lock {
  position: absolute;
  inset: 0;
  border-radius: 18px;
  background: rgba(5, 8, 16, 0.68);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  color: #fbbf24;
  z-index: 2;
  pointer-events: none;
}

.project-card.is-locked .project-action {
  color: var(--muted);
}

.project-card.is-disabled:hover {
  transform: none;
  border-color: rgba(148,163,184,0.14);
  box-shadow:
    0 4px 10px rgba(0,0,0,0.25),
    inset 0 1px 0 rgba(255,255,255,0.03);
}

.project-meta + .project-meta {
  margin-top: 2px;
}

.empty-state {
  grid-column: 1 / -1;
  padding: 28px;
  border-radius: 16px;
  border: 1px dashed rgba(148,163,184,0.25);
  background: rgba(15,23,42,0.45);
  color: var(--muted);
  text-align: center;
}

.empty-state h3 {
  margin: 0 0 6px;
  color: var(--text);
  font-size: 18px;
}

/* ===== ADMIN SIDEBAR ===== */
section[data-testid="stSidebar"] {
  background: rgba(6, 10, 20, 0.97);
  border-right: 1px solid rgba(148,163,184,0.18);
  height: 100vh;
  overflow-y: auto;
}

section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
  padding: 24px 18px 32px;
  height: auto;
  max-height: 100vh;
  overflow-y: auto;
}

section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"],
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] > div,
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] [data-testid="stVerticalBlock"] {
  height: auto !important;
  min-height: 0;
}

.admin-sidebar {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.admin-card {
  border-radius: 16px;
  padding: 16px;
  border: 1px solid rgba(148,163,184,0.18);
  background: linear-gradient(180deg, rgba(13,18,35,0.92), rgba(8,12,24,0.88));
  box-shadow: 0 18px 36px rgba(0,0,0,0.35);
}

.admin-card-title {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: rgba(157,168,198,0.85);
}

.admin-user {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
}

.admin-avatar {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  border: 1px solid rgba(148,163,184,0.35);
  object-fit: cover;
}

.admin-avatar-wrap {
  position: relative;
  width: 42px;
  height: 42px;
  flex: 0 0 auto;
}

.admin-avatar-wrap .admin-avatar,
.admin-avatar-wrap .admin-avatar-fallback {
  width: 42px;
  height: 42px;
}

.admin-avatar-fallback {
  position: absolute;
  inset: 0;
  display: none;
}

.admin-avatar.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(109,213,237,0.12);
  color: var(--accent);
  font-weight: 700;
}

.admin-user-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.admin-name-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.admin-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
}

.admin-badge {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid rgba(109,213,237,0.4);
  background: rgba(109,213,237,0.12);
  color: var(--accent);
}

.admin-email {
  font-size: 12px;
  color: var(--muted);
  word-break: break-word;
}

.admin-meta {
  margin-top: 12px;
  font-size: 12px;
  color: var(--muted);
}

.admin-note {
  margin-top: 10px;
  font-size: 12px;
  color: var(--muted);
}

.admin-actions {
  display: grid;
  gap: 10px;
  margin-top: 12px;
}

.admin-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(148,163,184,0.25);
  background: rgba(15,23,42,0.55);
  color: var(--text);
  text-decoration: none;
  font-weight: 600;
  transition: border-color 0.2s ease, background 0.2s ease, box-shadow 0.2s ease;
}

.admin-button:hover {
  border-color: rgba(109,213,237,0.7);
  background: rgba(25,34,55,0.8);
  box-shadow: 0 10px 22px rgba(0,0,0,0.25);
}

.admin-button.ghost {
  background: transparent;
  color: var(--muted);
}

#st-key-admin_create_btn button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(148,163,184,0.25);
  background: transparent;
  color: var(--muted);
  font-weight: 600;
  box-shadow: none;
}

#st-key-admin_create_btn button:hover {
  border-color: rgba(109,213,237,0.7);
  color: var(--text);
}

#st-key-admin_create_btn button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}


</style>
""",
unsafe_allow_html=True
    )
    st.session_state["_projects_css_loaded"] = True

# =============================
# HELPERS
# =============================
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


def _clear_query_params() -> None:
    try:
        st.query_params.clear()  # type: ignore[attr-defined]
    except AttributeError:
        st.experimental_set_query_params()

def _is_truthy(value: str | None) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _base_url() -> str:
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

params = _get_query_params()
ptxn = _query_value(params, "_ptxn")
if ptxn:
    st.session_state["checkout_returned"] = True
    st.session_state["checkout_txn"] = ptxn
    _clear_query_params()
    st.switch_page("pages/4_Billing.py")
    st.stop()


def _admin_emails() -> set[str]:
    emails = {"ali.el.bied9898@gmail.com"}
    raw = os.environ.get("ADMIN_EMAILS", "")
    if not raw:
        try:
            raw = st.secrets.get("ADMIN_EMAILS", "")
        except Exception:
            raw = ""
    for email in raw.split(","):
        cleaned = email.strip().lower()
        if cleaned:
            emails.add(cleaned)
    return {email.lower() for email in emails if email}


def _is_admin_user(user: dict | None) -> bool:
    if not user:
        return False
    email = (user.get("email") or "").lower()
    return email in _admin_emails()

def _is_localhost() -> bool:
    host = st.get_option("server.address") or "localhost"
    return host in {"localhost", "127.0.0.1", "0.0.0.0"}


def _render_dev_switcher_ui(prefix: str, user: dict | None) -> None:
    if not user:
        return
    email_current = (user.get("email") or "").strip()
    name_current = (user.get("name") or "").strip()
    if email_current:
        remember_dev_user(email_current, name_current)
    params = _get_query_params()
    email_input = st.text_input(
        "Dev email",
        value="",
        key=f"{prefix}_dev_email",
    )
    name_input = st.text_input(
        "Dev name",
        value="",
        key=f"{prefix}_dev_name",
    )
    ref_input = st.text_input(
        "Referral code (optional)",
        value=_query_value(params, "ref") or "",
        key=f"{prefix}_dev_ref",
    )
    if st.button("Switch user", key=f"{prefix}_dev_switch_btn"):
        if email_input.strip():
            switch_dev_user(email_input, name_input, ref_input)
        else:
            st.warning("Enter an email to switch.")
    if st.button("Clear dev user", key=f"{prefix}_dev_clear_btn"):
        try:
            st.query_params.clear()  # type: ignore[attr-defined]
        except AttributeError:
            st.experimental_set_query_params()
        st.rerun()
    saved_users = list_dev_users()
    if saved_users:
        st.markdown("**Saved accounts**")
        for idx, entry in enumerate(saved_users):
            email_value = entry.get("email", "")
            name_value = entry.get("name", "")
            label = name_value or email_value
            cols = st.columns([3, 1, 1], gap="small")
            if name_value:
                cols[0].markdown(f"**{label}**\n\n{email_value}")
            else:
                cols[0].markdown(f"**{label}**")
            if cols[1].button("Switch", key=f"{prefix}_saved_switch_{idx}"):
                switch_dev_user(email_value, name_value, ref_input)
            if cols[2].button("Forget", key=f"{prefix}_saved_forget_{idx}"):
                forget_dev_user(email_value)
                st.rerun()
        with st.expander("Reset account data", expanded=False):
            options = [u.get("email", "") for u in saved_users if u.get("email")]
            target = st.selectbox(
                "Account email",
                options,
                key=f"{prefix}_reset_email",
            )
            confirm = st.checkbox(
                "I understand this deletes billing data for this email.",
                key=f"{prefix}_reset_confirm",
            )
            if st.button("Delete billing data", key=f"{prefix}_reset_btn"):
                if not confirm:
                    st.warning("Confirm the delete first.")
                elif delete_account_by_email(target):
                    st.success("Billing data deleted.")
                else:
                    st.info("No billing account found for that email.")
    else:
        st.caption("No saved accounts yet.")


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _format_updated(value: str | None) -> str:
    parsed = _parse_dt(value)
    if parsed is None:
        return value or "--"
    return parsed.strftime("%b %d, %Y")


def _file_exists(path_value: str | None) -> bool:
    if not path_value:
        return False
    try:
        return Path(path_value).exists()
    except OSError:
        return False


def _redirect_to_project(project_id: str) -> None:
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


def _open_create_dialog(
    project_count: int,
    owner_id: str | None,
    account_id: int | None,
) -> None:
    if not hasattr(st, "dialog"):
        st.info("Update Streamlit to use modal project creation.")
        return

    @st.dialog("Create project")
    def _dialog() -> None:
        with st.container(key="create_modal_root"):
            st.markdown('<div class="manage-modal-title">Create project</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="manage-modal-sub">Start a new workspace for a client or timeline.</div>',
                unsafe_allow_html=True,
            )
            if project_count >= PROJECT_LIMIT:
                st.warning(f"Project limit reached ({PROJECT_LIMIT}).")
                return

            with st.form("create_project_form", clear_on_submit=False):
                name = st.text_input(
                    "Project name",
                    key="create_project_name",
                    placeholder="Project name",
                )
                submitted = st.form_submit_button("Create project")

            if not submitted:
                return

            cleaned = (name or "").strip()
            if not cleaned:
                st.warning("Project name cannot be empty.")
                return

            with st.spinner("Creating your project…"):
                project = create_project(cleaned, owner_id=owner_id)

            if not project:
                st.error("Unable to create project.")
                return

            record_event(account_id, "project_created", {"project_id": project["id"]})
            st.session_state["active_project_id"] = project["id"]
            st.session_state.pop("project_loaded_id", None)

            st.toast("Project created", icon="✅")
            _clear_query_params()
            st.switch_page("app.py")

    _dialog()


def _open_manage_dialog(project: dict, owner_id: str | None) -> None:
    project_id = project.get("id")
    if not project_id:
        return
    name = project.get("name") or project_id
    if hasattr(st, "dialog"):
        @st.dialog("Manage project")
        def _dialog() -> None:
            with st.container(key="manage_modal_root"):
                st.markdown(f'<div class="manage-modal-title">{html.escape(name)}</div>', unsafe_allow_html=True)
                st.markdown('<div class="manage-modal-sub">Edit project details and data.</div>', unsafe_allow_html=True)
                _render_project_actions(project_id, name, owner_id)
        _dialog()
    else:
        st.info("Update Streamlit to use modal project actions.")
        _render_project_actions(project_id, name, owner_id)


def _render_project_actions(project_id: str, current_name: str, owner_id: str | None) -> None:
    with st.container(key=f"manage_rename_{project_id}"):
        st.markdown('<div class="manage-modal-label">Rename project</div>', unsafe_allow_html=True)
        rename_key = f"rename_input_{project_id}"
        new_name = st.text_input(
            "Project name",
            value=current_name,
            key=rename_key,
            label_visibility="collapsed",
        )
        with st.container(key=f"manage_save_{project_id}"):
            if st.button("Save name", key=f"rename_save_{project_id}"):
                cleaned = (new_name or "").strip()
                if not cleaned:
                    st.warning("Project name cannot be empty.")
                else:
                    updated = update_project(project_id, owner_id=owner_id, name=cleaned)
                    if updated:
                        st.session_state["project_flash"] = f'Project renamed to "{cleaned}".'
                        _clear_query_params()
                        st.rerun()
                    else:
                        st.error("Unable to update project name.")

    with st.container(key=f"manage_danger_{project_id}"):
        st.markdown('<div class="manage-modal-label">Danger zone</div>', unsafe_allow_html=True)
        st.caption("Deletes the project and its uploaded data.")
        confirm_key = f"confirm_delete_state_{project_id}"
        delete_col, confirm_col = st.columns([3, 1])
        with delete_col:
            with st.container(key=f"manage_delete_{project_id}"):
                if st.button("Delete project", key=f"delete_project_{project_id}"):
                    st.session_state[confirm_key] = True
        with confirm_col:
            if st.session_state.get(confirm_key):
                icon_cols = st.columns(2, gap="small")
                with icon_cols[0]:
                    with st.container(key=f"manage_confirm_{project_id}"):
                        if st.button("✔", key=f"confirm_delete_{project_id}", help="Confirm delete"):
                            if delete_project(project_id, owner_id=owner_id):
                                st.session_state.pop(confirm_key, None)
                                st.session_state["project_flash"] = f'Project "{current_name}" deleted.'
                                _clear_query_params()
                                st.rerun()
                            else:
                                st.error("Unable to delete project.")
                with icon_cols[1]:
                    with st.container(key=f"manage_cancel_{project_id}"):
                        if st.button("✖", key=f"cancel_delete_{project_id}", help="Cancel delete"):
                            st.session_state.pop(confirm_key, None)
        if st.session_state.get(confirm_key):
            st.markdown(
                '<div class="manage-alert">Confirm delete to permanently remove this project.</div>',
                unsafe_allow_html=True,
            )


def _missing_required_fields(
    headers: list[object] | None,
    table_type: str,
    mapping: dict[str, dict[str, str]],
) -> list[str]:
    if table_type == "activity_summary":
        required_fields = SUMMARY_REQUIRED_FIELDS
    else:
        required_fields = ASSIGN_REQUIRED_FIELDS
    if not headers:
        return list(required_fields)
    header_list = [str(h).strip() for h in headers if str(h or "").strip()]
    suggested = suggest_column_mapping(headers, table_type)
    table_mapping = mapping.get(table_type, {})
    missing: list[str] = []
    for field in required_fields:
        mapped = table_mapping.get(field)
        if mapped and mapped in header_list:
            continue
        if field in suggested:
            continue
        missing.append(field)
    return missing


def _project_status(project: dict) -> tuple[str, str, str | None]:
    file_path = project.get("file_path")
    if not _file_exists(file_path):
        return "Needs upload", "warn", None
    project_id = project.get("id")
    file_key = project.get("file_key")
    mapping_key = project.get("mapping_key")
    expected_key = project_mapping_key(project_id, file_key)
    if expected_key and mapping_key and mapping_key != expected_key:
        return "Needs mapping (Stale)", "warn", "Mapping is for a different upload."
    mapping = project.get("mapping")
    mapping = mapping if isinstance(mapping, dict) else {}
    try:
        persisted = load_headers_cache(file_path, mapping)
        if persisted:
            summary_headers = persisted.get("summary_headers")
            assign_headers = persisted.get("assign_headers")
        else:
            file_cache_key = _file_cache_key(file_path)
            mapping_cache_key = _mapping_cache_key(mapping)
            summary_headers = _cached_table_headers(
                file_path,
                file_cache_key,
                "activity_summary",
                mapping_cache_key,
                mapping,
            )
            assign_headers = _cached_table_headers(
                file_path,
                file_cache_key,
                "resource_assignments",
                mapping_cache_key,
                mapping,
            )
            try:
                save_headers_cache(
                    file_path,
                    mapping,
                    summary_headers=summary_headers,
                    assign_headers=assign_headers,
                )
            except Exception:
                pass
    except Exception:
        return "File error", "warn", "Unreadable Excel file."
    summary_missing = _missing_required_fields(
        summary_headers[0] if summary_headers else None,
        "activity_summary",
        mapping,
    )
    if summary_missing:
        return "Needs mapping (Summary)", "warn", None
    assign_missing = _missing_required_fields(
        assign_headers[0] if assign_headers else None,
        "resource_assignments",
        mapping,
    )
    if assign_missing:
        return "Ready (Dashboard)", "ok", "Schedule needs assignments."
    return "Ready (Schedule)", "ok", None


def _project_action(status_label: str) -> str:
    if status_label == "Needs upload":
        return "Upload data"
    if status_label.startswith("Needs mapping"):
        return "Finish mapping"
    if status_label == "Ready (Dashboard)":
        return "Open dashboard"
    if status_label == "File error":
        return "Re-upload file"
    return "Open project"


def _sort_projects(items: list[dict], sort_mode: str) -> list[dict]:
    if sort_mode == "Name A-Z":
        return sorted(items, key=lambda p: (p.get("name") or "").lower())
    if sort_mode == "Created (newest)":
        return sorted(items, key=lambda p: _parse_dt(p.get("created_at")) or datetime.min, reverse=True)
    return sorted(items, key=lambda p: _parse_dt(p.get("updated_at")) or datetime.min, reverse=True)


# =============================
# AUTH + DATA
# =============================
_debug_log("projects: start")
user = _timeit("auth.require_login", require_login)
owner_id = owner_id_from_user(user)
is_admin = _is_admin_user(user)
if is_admin and owner_id:
    migrated_key = f"_projects_owner_migrated_{owner_id}"
    if not st.session_state.get(migrated_key):
        assign_projects_to_owner(owner_id)
        st.session_state[migrated_key] = True
projects = _timeit("db.list_projects", lambda: list_projects(owner_id) or [])
_debug_log(f"projects: loaded count={len(projects)}")
if "show_create" not in st.session_state:
    st.session_state["show_create"] = False
if "show_manage" not in st.session_state:
    st.session_state["show_manage"] = None

params = _get_query_params()
logout_param = _query_value(params, "logout")
project_param = _query_value(params, "project")
new_param = _query_value(params, "new")
create_param = _query_value(params, "create") or new_param
manage_param = _query_value(params, "manage")
if _is_truthy(logout_param):
    logout()
if st.session_state.pop("navigate_to_app", False):
    st.switch_page("app.py")
if project_param:
    project_map = {p.get("id"): p for p in projects if p.get("id")}
    if project_param in project_map:
        _redirect_to_project(project_param)
    _clear_query_params()
    st.warning("Project not found.")


# =============================
# FILTERS
# =============================
project_count = len(projects)
account = get_account_by_email(user.get("email", ""))
plan_state = access_status(account)
is_locked = not plan_state.get("allowed", True)
is_dev_bypass = bool(user.get("bypass")) and _is_localhost()
show_admin_sidebar = is_admin or is_dev_bypass

with st.sidebar:
    validate_now = st.button(
        "Validate Excel files (slow)",
        key="validate_excel_now",
        help="Checks each project's Excel to determine readiness/mapping issues.",
    )
    validate_auto = st.toggle(
        "Auto-validate on load",
        value=False,
        key="validate_excel_auto",
        help="Can be slow on large Excels; uses cache after first run.",
    )
    show_debug_logs = st.toggle(
        "Show debug logs",
        value=False,
        key="projects_show_debug_logs",
        help="Shows server-side progress markers for this page.",
    )

validate_excel = bool(validate_now or validate_auto)
if validate_excel:
    st.sidebar.caption("Validation is running (may take a while on huge Excel files).")

logo_uri = _get_logo_data_uri()
if logo_uri:
    logo_html = f'<img class="top-logo" src="{logo_uri}" alt="ChronoPlan logo" />'
else:
    logo_html = '<div class="top-logo-text">ChronoPlan</div>'
user_name = user.get("name") or user.get("email") or "User"
user_email = user.get("email") or ""
user_picture = user.get("picture")
initial = (user_name.strip()[:1] or "?").upper()
plan_status = (plan_state.get("status") or "trialing").lower()
trial_end = plan_state.get("trial_end")
days_left = plan_state.get("days_left")
plan_end = plan_state.get("plan_end")
plan_label = "Premium"
plan_class = "premium"
plan_meta = ""
if plan_status == "active":
    if is_locked:
        plan_label = "Subscription ended"
        plan_class = "locked"
        if plan_end:
            plan_meta = f"Ended {plan_end.strftime('%b %d, %Y')}"
        else:
            plan_meta = "Subscription required"
    elif plan_end:
        plan_meta = f"Ends {plan_end.strftime('%b %d, %Y')}"
elif plan_status == "trialing":
    if is_locked:
        plan_label = "Trial ended"
        plan_class = "locked"
        if trial_end:
            plan_meta = f"Ended {trial_end.strftime('%b %d, %Y')}"
    else:
        plan_label = "Trial"
        plan_class = "trial"
        if days_left is not None:
            plan_meta = f"{days_left} days left"
        elif trial_end:
            plan_meta = f"Ends {trial_end.strftime('%b %d, %Y')}"
elif plan_status != "active":
    if is_locked:
        plan_label = "Locked"
        plan_class = "locked"
        plan_meta = "Subscription required"
    else:
        plan_label = "Trial"
        plan_class = "trial"
if user_picture:
    avatar_html = (
        f'<div class="user-avatar-wrap">'
        f'<img class="user-avatar" src="{html.escape(user_picture)}" alt="avatar" '
        f'onerror="this.style.display=\\\"none\\\";'
        f'this.nextElementSibling.style.display=\\\"flex\\\";" />'
        f'<div class="user-avatar placeholder user-avatar-fallback">{html.escape(initial)}</div>'
        f'</div>'
    )
else:
    avatar_html = f'<div class="user-avatar placeholder">{html.escape(initial)}</div>'
email_html = f'<div class="user-email">{html.escape(user_email)}</div>' if user_email else ""
plan_badge_html = f'<div class="plan-badge {plan_class}">{html.escape(plan_label)}</div>'
plan_meta_html = f'<div class="plan-meta">{html.escape(plan_meta)}</div>' if plan_meta else ""
top_bar_html = f"""
<div class="top-bar">
  {logo_html}
  <div class="top-account">
    <div class="top-account-info">
      {avatar_html}
      <div class="user-info">
        <div class="user-name">{html.escape(user_name)}</div>
        {email_html}
        {plan_badge_html}
        {plan_meta_html}
      </div>
    </div>
    <div class="top-actions">
      <a class="top-link" href="/Billing">Billing</a>
      <a class="signout-btn" href="?logout=1" title="Sign out" aria-label="Sign out">⏻</a>
    </div>
  </div>
</div>
"""

if show_admin_sidebar:
    if user_picture:
        admin_avatar_html = (
            f'<div class="admin-avatar-wrap">'
            f'<img class="admin-avatar" src="{html.escape(user_picture)}" alt="avatar" '
            f'onerror="this.style.display=\\\"none\\\";'
            f'this.nextElementSibling.style.display=\\\"flex\\\";" />'
            f'<div class="admin-avatar placeholder admin-avatar-fallback">{html.escape(initial)}</div>'
            f'</div>'
        )
    else:
        admin_avatar_html = f'<div class="admin-avatar placeholder">{html.escape(initial)}</div>'
    admin_email_html = f'<div class="admin-email">{html.escape(user_email)}</div>' if user_email else ""
    access_label = "Admin access" if is_admin else "Dev access"
    badge_label = "Admin" if is_admin else "Dev"
    tools_label = "Admin tools" if is_admin else "Dev tools"
    admin_stats_link = '<a class="admin-button" href="/Admin">Open admin stats</a>'
    admin_note = ""
    admin_sidebar_html = f"""
    <div class="admin-sidebar">
      <div class="admin-card">
        <div class="admin-card-title">{access_label}</div>
        <div class="admin-user">
          {admin_avatar_html}
          <div class="admin-user-info">
            <div class="admin-name-row">
              <div class="admin-name">{html.escape(user_name)}</div>
              <span class="admin-badge">{badge_label}</span>
            </div>
            {admin_email_html}
          </div>
        </div>
        <div class="admin-meta">Projects {project_count}/{PROJECT_LIMIT}</div>
      </div>
      <div class="admin-card">
        <div class="admin-card-title">{tools_label}</div>
        <div class="admin-actions">
          {admin_stats_link}
        </div>
        {admin_note}
      </div>
    </div>
    """
    with st.sidebar:
        st.html(admin_sidebar_html)
        if st.button("Create project", key="admin_create_btn", disabled=is_locked):
            st.session_state["show_create"] = True
    if _is_localhost():
        with st.sidebar.expander("Dev user switcher", expanded=False):
            _render_dev_switcher_ui("admin_sidebar", user)

if plan_status == "trialing":
    locked_cta_label = "Start subscription"
elif plan_status == "active":
    locked_cta_label = "Renew subscription"
else:
    locked_cta_label = "Subscription required"

st.html(top_bar_html)
hero_cols = st.columns([2.2, 1], gap="large")
with hero_cols[0]:
    st.markdown('<div class="project-title">Pick your next project</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="project-sub">Build dashboards per client or per timeline.</div>',
        unsafe_allow_html=True,
    )
with hero_cols[1]:
    if is_locked:
        st.markdown(
            f'<a class="cta-button" href="/Billing">{locked_cta_label}</a>',
            unsafe_allow_html=True,
        )
    else:
        if st.button("Create project", key="open_create_dialog_btn", disabled=is_locked):
            st.session_state["show_create"] = True
    st.markdown(
        f'<div class="ghost-chip">Projects {project_count}/{PROJECT_LIMIT}</div>',
        unsafe_allow_html=True,
    )

flash_message = st.session_state.pop("project_flash", None)
if flash_message:
    st.success(flash_message)

if account and account.get("referral_code"):
    referral_link = f"{_base_url()}/?ref={account['referral_code']}"
    with st.expander("Referral link", expanded=False):
        st.caption("Share this link to grant a bonus month on the first paid month.")
        st.code(referral_link)

create_requested = st.session_state.get("show_create")
if _is_truthy(create_param) or create_requested:
    if is_locked:
        st.warning("Subscription required to create projects.")
    else:
        _open_create_dialog(project_count, owner_id, user.get("billing_account_id"))
    st.session_state["show_create"] = False

# =============================
# BUILD CARDS
# =============================
status_cache: dict[str | None, tuple[str, str, str | None]] = {}

if validate_excel:
    _debug_log("projects: validating excels")
    status_box = st.status("Checking project Excel files…", expanded=False)
    try:
        for idx, p in enumerate(projects, start=1):
            pid = p.get("id")
            if not pid:
                continue
            status_box.update(label=f"Checking project {idx}/{len(projects)}…")
            status_label, status_class, status_detail = _timeit(
                f"project.status:{pid}",
                lambda p=p: _project_status(p),
            )
            status_cache[pid] = (status_label, status_class, status_detail)
    finally:
        status_box.update(label="Projects ready", state="complete", expanded=False)
else:
    _debug_log("projects: validation skipped")
    for p in projects:
        file_path = p.get("file_path")
        if not _file_exists(file_path):
            status_cache[p.get("id")] = ("Needs upload", "warn", None)
            continue
        project_id = p.get("id")
        file_key = p.get("file_key")
        mapping_key = p.get("mapping_key")
        expected_key = project_mapping_key(project_id, file_key)
        if expected_key and mapping_key and mapping_key != expected_key:
            status_cache[p.get("id")] = ("Needs mapping (Stale)", "warn", "Mapping is for a different upload.")
        else:
            status_cache[p.get("id")] = ("Unchecked", "warn", "Click “Validate Excel files” to compute readiness.")

filtered = [p for p in projects if p.get("id")]
filtered = _sort_projects(filtered, "Recently updated")

if is_locked and plan_status == "trialing":
    locked_label = "Trial ended"
elif is_locked and plan_status == "active":
    locked_label = "Subscription ended"
else:
    locked_label = "Subscription required"

grid_columns = 3
cols = st.columns(grid_columns, gap="large")
card_index = 0
for p in filtered:
    project_id = p.get("id")
    if not project_id:
        continue
    name_html = html.escape(p.get("name", "Untitled"))
    updated_label_html = html.escape(_format_updated(p.get("updated_at")))
    status_label, status_class, status_detail = status_cache.get(
        project_id,
        _project_status(p),
    )
    file_path_value = p.get("file_path")
    file_name = (p.get("file_name") or "").strip()
    if not file_name and file_path_value:
        file_name = Path(file_path_value).name
    file_line_html = None
    if file_name:
        file_line_html = f'<div class="project-meta">Data {html.escape(file_name)}</div>'
    elif status_label == "Needs upload":
        file_line_html = '<div class="project-meta">No file uploaded</div>'
    detail_line_html = None
    if status_detail:
        detail_line_html = f'<div class="project-meta">{html.escape(status_detail)}</div>'
    badge_class = f"project-badge {status_class}".strip()
    file_line = file_line_html or ""
    detail_line = detail_line_html or ""
    card_class = "project-card is-locked" if is_locked else "project-card"
    card_link = (
        f'<a class="project-card-link" href="/?project={html.escape(project_id)}" aria-label="Open project"></a>'
        if not is_locked
        else ""
    )
    lock_html = f'<div class="project-card-lock">{locked_label}</div>' if is_locked else ""
    action_label = "Locked" if is_locked else _project_action(status_label)
    card_html = _clean_html_block(
        f"""
        <div class="{card_class}">
          {card_link}
          {lock_html}
          <div class="project-card-content">
            <div class="project-name">{name_html}</div>
            <div class="{badge_class}">{status_label}</div>
            {file_line}
            {detail_line}
            <div class="project-meta">Updated {updated_label_html}</div>
            <div class="project-action">{action_label}</div>
          </div>
        </div>
        """
    )
    col = cols[card_index % grid_columns]
    with col:
        with st.container(key=f"card_{project_id}"):
            st.markdown(card_html, unsafe_allow_html=True)
            if not is_locked:
                if st.button("Manage", key=f"manage_btn_{project_id}"):
                    st.session_state["show_manage"] = project_id
    card_index += 1

if project_count < PROJECT_LIMIT:
    col = cols[card_index % grid_columns]
    with col:
        with st.container(key="card_create"):
            if is_locked:
                create_html = _clean_html_block(
                    f"""
                    <div class="project-card create-card is-disabled is-locked">
                      <div class="project-card-lock">{locked_label}</div>
                      <div class="project-card-content">
                        <div class="project-name">Create new project</div>
                        <div class="project-meta">Subscription required</div>
                        <div class="project-action">Locked</div>
                      </div>
                    </div>
                    """
                )
                st.markdown(create_html, unsafe_allow_html=True)
            else:
                create_html = _clean_html_block(
                    f"""
                    <div class="project-card create-card">
                      <div class="project-card-content">
                        <div class="project-name">Create new project</div>
                        <div class="project-meta">Limit {PROJECT_LIMIT} projects</div>
                        <div class="project-action">Launch builder</div>
                      </div>
                    </div>
                    """
                )
                st.markdown(create_html, unsafe_allow_html=True)
                if st.button("Create", key="create_card_btn"):
                    st.session_state["show_create"] = True
else:
    col = cols[card_index % grid_columns]
    with col:
        with st.container(key="card_limit"):
            limit_html = _clean_html_block(
                f"""
                <div class="project-card create-card is-disabled">
                  <div class="project-name">Project limit reached</div>
                  <div class="project-meta">Limit {PROJECT_LIMIT} projects</div>
                  <div class="project-action">Archive a project to add more</div>
                </div>
                """
            )
            st.markdown(limit_html, unsafe_allow_html=True)

_debug_log("projects: rendered final grid")

manage_project = None
manage_requested = st.session_state.get("show_manage")
if manage_requested:
    project_map = {p.get("id"): p for p in projects if p.get("id")}
    manage_project = project_map.get(manage_requested)
    if not manage_project:
        st.warning("Project not found.")
    st.session_state["show_manage"] = None
elif manage_param:
    project_map = {p.get("id"): p for p in projects if p.get("id")}
    manage_project = project_map.get(manage_param)
    if not manage_project:
        _clear_query_params()
        st.warning("Project not found.")

if manage_project:
    _open_manage_dialog(manage_project, owner_id)

if _debug:
    with st.sidebar.expander("Debug: timings", expanded=False):
        for label, ms in _timings:
            st.caption(f"{label}: {ms:.1f} ms")

if show_debug_logs or _debug:
    with st.sidebar.expander("Debug: logs", expanded=False):
        logs = st.session_state.get("_debug_logs", [])
        text = "\n".join(logs[-200:]) if logs else "(no logs yet)"
        st.code(text)
        st.download_button(
            "Download logs",
            data=(text + "\n").encode("utf-8"),
            file_name="projects_debug.log",
            mime="text/plain",
        )
