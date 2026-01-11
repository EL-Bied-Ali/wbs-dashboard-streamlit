from __future__ import annotations

import textwrap
from typing import Any

import streamlit as st

GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:wght@500;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');

:root{
  --bg:#05060B;
  --card:rgba(20, 27, 46, 0.88);
  --card-border:rgba(148, 163, 184, 0.18);
  --text:#e5e7eb;
  --muted:#8b98b4;
  --accent:#6dd5ed;
  --accent-2:#b47cff;
}

html, body { background: var(--bg); }
.stApp{
  background: transparent;
  color: var(--text);
  font-family: "Space Grotesk", sans-serif;
}

body::before{
  content:"";
  position: fixed;
  inset: 0;
  background:
    radial-gradient(800px 300px at 20% 0%, rgba(109,213,237,.35), transparent 60%),
    radial-gradient(700px 260px at 80% 0%, rgba(180,124,255,.35), transparent 60%),
    radial-gradient(600px 400px at 50% 40%, rgba(109,213,237,.08), transparent 70%),
    var(--bg);
  z-index: 0;
}

/* Keep Streamlit content above background */
.stApp > header, .stApp > div { position: relative; z-index: 1; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebarNav"] { display: none !important; }

.block-container { max-width: 1200px; padding: 48px 24px 96px; }

/* =========================
   TOP / HERO (RESTORED)
   ========================= */
.project-hero{
  display:flex;
  flex-wrap:wrap;
  gap:32px;
  align-items:center;
  justify-content:space-between;
  margin-bottom:40px;
}

.top-bar{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:16px;
  margin-bottom:28px;
}

.top-logo{ height:120px; width:auto; display:block; }

.top-logo-text{
  font-family:"Fraunces", serif;
  font-size:40px;
  font-weight:700;
  color: var(--text);
}

.top-account{
  display:flex;
  align-items:center;
  gap:16px;
  padding:16px 22px;
  border-radius:18px;
  border:1px solid rgba(148,163,184,0.2);
  background: rgba(15,23,42,0.6);
}

.top-account-info{ display:flex; align-items:center; gap:12px; }
.top-actions{ display:flex; align-items:center; gap:10px; }

.top-link{
  font-size:12px;
  font-weight:600;
  color: var(--text);
  padding:6px 12px;
  border-radius:999px;
  border:1px solid rgba(148,163,184,0.35);
  background: rgba(15,23,42,0.45);
  text-decoration:none;
}
.top-link:hover{ border-color: rgba(109,213,237,0.6); }

.signout-btn{
  width:38px; height:38px;
  border-radius:10px;
  border:1px solid rgba(148,163,184,0.35);
  background: rgba(15,23,42,0.5);
  display:inline-flex;
  align-items:center;
  justify-content:center;
  color: var(--muted);
  text-decoration:none;
  font-size:18px;
}
.signout-btn:hover{ border-color: rgba(109,213,237,0.6); color: var(--text); }

.user-avatar{
  width:56px; height:56px;
  border-radius:50%;
  object-fit:cover;
  border:1px solid rgba(148,163,184,0.35);
}
.user-avatar-wrap{ position:relative; width:56px; height:56px; flex:0 0 auto; }
.user-avatar-wrap .user-avatar,
.user-avatar-wrap .user-avatar-fallback{ width:56px; height:56px; }
.user-avatar-fallback{ position:absolute; inset:0; display:none; }
.user-avatar.placeholder{
  display:flex;
  align-items:center;
  justify-content:center;
  background: rgba(109,213,237,0.12);
  color: var(--accent);
  font-weight:700;
}

.user-info{ display:flex; flex-direction:column; gap:2px; }
.user-name{ font-size:16px; font-weight:600; color: var(--text); }
.user-email{ font-size:14px; color: var(--muted); }

.project-title{
  font-family:"Fraunces", serif;
  font-size: clamp(32px, 5vw, 54px);
  margin:0 0 12px;
}
.project-sub{ font-size:16px; color: var(--muted); max-width:520px; }

.project-cta{ display:flex; gap:14px; align-items:center; }
.cta-button{
  font-size:14px;
  font-weight:600;
  padding:10px 20px;
  border-radius:999px;
  background: linear-gradient(120deg, var(--accent), var(--accent-2));
  color:#0b0f18;
  text-decoration:none;
  box-shadow: 0 14px 36px rgba(109,213,237,.35);
}
.ghost-chip{
  font-size:13px;
  color: var(--muted);
  padding:6px 12px;
  border-radius:999px;
  border:1px solid rgba(148,163,184,.25);
  background: rgba(15,23,42,.35);
}

/* =========================
   GRID + CARD
   ========================= */
.project-grid{
  display:grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap:20px;
}

.project-card{
  position:relative;
  border-radius:18px;
  padding:18px 18px 16px 18px;
  min-height:160px;

  border:1px solid rgba(148,163,184,0.14);
  background: rgba(15,23,42,0.55);
  backdrop-filter: blur(10px);

  box-shadow:
    0 18px 60px rgba(0,0,0,0.35),
    inset 0 1px 0 rgba(255,255,255,0.06);

  overflow:hidden;
}
.project-card:hover{
  box-shadow:
    0 22px 70px rgba(0,0,0,0.45),
    0 0 0 1px rgba(109,213,237,0.20),
    inset 0 1px 0 rgba(255,255,255,0.08);
}

.project-card::before{
  content:"";
  position:absolute;
  left:0; right:0; top:0;
  height:3px;
  background: linear-gradient(90deg, var(--accent), var(--accent-2));
  opacity:0.9;
}

.project-card-link{ position:absolute; inset:0; z-index:1; border-radius:18px; }

.project-card-content{
  position:relative; z-index:2;
  display:flex; flex-direction:column;
  gap:10px; min-height:100%;
  pointer-events:none;
  padding-top:2px;
}

/* =========================
   FIX: ACTIONS MENU TOP-RIGHT
   (based on your DOM)
   ========================= */

/* Anchor on st-key-card_ because actions + html live inside it */
.stVerticalBlock[class*="st-key-card_"]{
  position: relative !important;
  overflow: visible !important;
  transition: transform .18s ease, border-color .2s ease, box-shadow .2s ease !important;
}

.stVerticalBlock[class*="st-key-card_"]:hover{
  transform: translateY(-3px) !important;
}

/* ACTIONS - version roue ⚙ */
.stVerticalBlock[class*="st-key-card_"] .stVerticalBlock[class*="st-key-actions_"]{
  position: absolute !important;
  top: 18px !important;
  right: 14px !important;
  left: auto !important;
  bottom: auto !important;
  z-index: 9999 !important;

  width: fit-content !important;
  max-width: fit-content !important;
  margin: 0 !important;
  padding: 0 !important;
}

/* shrink Streamlit wrapper that may try to be 100% width */
.stVerticalBlock[class*="st-key-card_"] .stVerticalBlock[class*="st-key-actions_"] > div[data-testid="stLayoutWrapper"]{
  width: fit-content !important;
}

/* Keep only ⋯ (hide the expand_more icon) */
.stVerticalBlock[class*="st-key-actions_"] [data-testid="stIconMaterial"]{
  display: none !important;
}

/* Ensure the menu stays clickable over the full-card link */
.project-card-link{ z-index: 1 !important; }
.stVerticalBlock[class*="st-key-actions_"]{ pointer-events: auto !important; }

/* =========================
   TEXT
   ========================= */
.project-name{
  display: inline-flex;
  align-items: center;
  align-self: flex-start;

  max-width: 100%;
  padding: 7px 14px;
  border-radius: 999px;

  background: linear-gradient(
    120deg,
    rgba(109,213,237,0.22),
    rgba(180,124,255,0.22)
  );
  border: 1px solid rgba(109,213,237,0.45);

  font-size: 14.5px;
  font-weight: 700;
  letter-spacing: 0.2px;
  color: rgba(229,231,235,0.98);

  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;

  box-shadow:
    inset 0 1px 0 rgba(255,255,255,0.12),
    0 6px 20px rgba(109,213,237,0.18);
}
.project-name::after{ display:none; }

.project-meta{
  font-size:12px;
  color: rgba(139,152,180,0.95);
}
.project-file-chip{
  background: none !important;
  border: none !important;
  padding: 0 !important;

  display: inline-flex;
  align-items: center;
  gap: 8px;
  align-self: flex-start;

  max-width: 100%;
  font-size: 12px;
  font-weight: 500;
  color: rgba(139,152,180,0.95);

  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.project-file-chip::before{
  content: "📄";
  font-size: 13px;
  opacity: 0.75;
}
.project-file-chip.empty{
  color: rgba(139,152,180,0.65);
  font-style: italic;
}
.project-file-chip.empty::before{
  content: "—";
  opacity: 0.6;
}

.stVerticalBlock[class*="st-key-card_"]:hover .project-name{
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,0.18),
    0 10px 28px rgba(109,213,237,0.30);
}

/* =========================
   MODAL / ADMIN (kept)
   ========================= */
.manage-modal-title{ font-family:"Fraunces", serif; font-size:20px; font-weight:700; color: var(--text); }
.manage-modal-sub{ color: var(--muted); font-size:13px; }
.manage-modal-label{
  font-size:11px;
  text-transform:uppercase;
  letter-spacing:0.14em;
  color: var(--muted);
}

.admin-sidebar{ display:flex; flex-direction:column; gap:18px; }
.admin-card{
  border-radius:16px;
  padding:16px;
  border:1px solid rgba(148,163,184,0.18);
  background: linear-gradient(180deg, rgba(13,18,35,0.92), rgba(8,12,24,0.88));
  box-shadow: 0 18px 36px rgba(0,0,0,0.35);
}

/* --- Gear button: no background + hover rotate/scale --- */
.stVerticalBlock[class*="st-key-actions_"] button[data-testid="stPopoverButton"]{
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;

  width: 30px !important;
  height: 30px !important;
  min-width: 30px !important;
  min-height: 30px !important;

  display: grid !important;
  place-items: center !important;

  transition: transform 160ms ease, opacity 160ms ease !important;
  opacity: 0.85 !important;
}

.stVerticalBlock[class*="st-key-actions_"] button[data-testid="stPopoverButton"]:hover{
  transform: rotate(20deg) scale(1.12) !important;
  opacity: 1 !important;
}

/* center the symbol */
.stVerticalBlock[class*="st-key-actions_"]
  button[data-testid="stPopoverButton"] [data-testid="stMarkdownContainer"],
.stVerticalBlock[class*="st-key-actions_"]
  button[data-testid="stPopoverButton"] p{
  margin: 0 !important;
  padding: 0 !important;
  line-height: 1 !important;
  font-size: 18px !important;
  font-weight: 600 !important;
  transform: none !important;
}

/* hide expand_more icon */
.stVerticalBlock[class*="st-key-actions_"] [data-testid="stIconMaterial"]{
  display: none !important;
}

.admin-sidebar{
  display:flex;
  flex-direction:column;
  gap:14px;
}

/* ===== SIDEBAR (single source of truth) ===== */

/* outer panel */
section[data-testid="stSidebar"]{
  position: relative !important;
  z-index: 5 !important;
  background: linear-gradient(180deg, rgba(15,23,42,0.92), rgba(8,12,24,0.88)) !important;
  border-right: 1px solid rgba(148,163,184,0.18) !important;
  box-shadow: 12px 0 40px rgba(0,0,0,0.35) !important;
}

/* inner wrapper (this is what often paints the visible bg) */
section[data-testid="stSidebar"] > div[data-testid="stSidebarContent"]{
  background: linear-gradient(180deg, rgba(15,23,42,0.92), rgba(8,12,24,0.88)) !important;
  padding: 18px 16px 24px !important;
}

/* header row */
section[data-testid="stSidebar"] div[data-testid="stSidebarHeader"]{
  background: rgba(2,6,23,0.22) !important;
  border-bottom: 1px solid rgba(148,163,184,0.14) !important;
  padding: 12px 12px 10px !important;
}

/* collapse button */
section[data-testid="stSidebar"] div[data-testid="stSidebarCollapseButton"] button{
  background: rgba(2,6,23,0.35) !important;
  border: 1px solid rgba(148,163,184,0.18) !important;
  border-radius: 10px !important;
  width: 34px !important;
  height: 34px !important;
  box-shadow: none !important;
}

/* Debug 5 secondes (puis enlève)
section[data-testid="stSidebar"]{ outline: 3px solid red !important; }
*/
</style>


"""


def inject_global_css() -> None:
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def clean_html_block(markup: str) -> str:
    cleaned = textwrap.dedent(markup).strip()
    return "\n".join(line.lstrip() for line in cleaned.splitlines())


def render_html(container: Any, markup: str) -> None:
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
