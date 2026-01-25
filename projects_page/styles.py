from __future__ import annotations

import os
import textwrap
from typing import Any

import streamlit as st

GLOBAL_CSS = """
<style id="chronoplan-global-css">
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

.block-container{
  width: 100%;
  max-width: min(1200px, calc(100vw - 48px));
  padding: 48px 24px 96px;
}

@media (max-width: 900px){
  .block-container{ padding: 28px 16px 72px; }
}

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

/* ===== PLAN BADGE ===== */
.plan-badge{
  align-self:flex-start;
  font-size:11px;
  font-weight:700;
  text-transform:uppercase;
  letter-spacing:0.12em;
  padding:4px 10px;
  border-radius:999px;
  border:1px solid rgba(148,163,184,0.25);
  background: rgba(15,23,42,0.45);
  color: var(--text);
}
.plan-badge.premium{
  border-color: rgba(34,197,94,0.35);
  background: rgba(34,197,94,0.12);
  color:#22c55e;
}
.plan-badge.trial{
  border-color: rgba(251,191,36,0.35);
  background: rgba(251,191,36,0.12);
  color:#fbbf24;
}
.plan-badge.locked{
  border-color: rgba(248,113,113,0.35);
  background: rgba(248,113,113,0.12);
  color:#f87171;
}
.plan-meta{ font-size:12px; color: var(--muted); }

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

/* ===================================
   Create Project Popover Button
   Styled to match .cta-button
   =================================== */

div.st-key-create_project_cta button[data-testid="stPopoverButton"] {
  /* Base styling: match .cta-button */
  font-size: 14px !important;
  font-weight: 600 !important;
  padding: 10px 20px !important;
  border-radius: 999px !important;
  background: linear-gradient(120deg, var(--accent), var(--accent-2)) !important;
  color: #0b0f18 !important;
  box-shadow: 0 14px 36px rgba(109,213,237,.35) !important;
  
  /* Reset Streamlit secondary button defaults */
  border: none !important;
  outline: none !important;
  text-decoration: none !important;
  line-height: normal !important;
  
  /* Smooth transitions */
  transition: all 150ms ease-in-out !important;
}

div.st-key-create_project_cta button[data-testid="stPopoverButton"]:hover {
  opacity: 0.9 !important;
  transform: translateY(-2px) !important;
  box-shadow: 0 16px 40px rgba(109,213,237,.45) !important;
}

div.st-key-create_project_cta button[data-testid="stPopoverButton"]:active {
  transform: translateY(0) !important;
  box-shadow: 0 10px 28px rgba(109,213,237,.30) !important;
}

div.st-key-create_project_cta button[data-testid="stPopoverButton"]:focus {
  outline: none !important;
  box-shadow: 0 14px 36px rgba(109,213,237,.35), 0 0 0 3px rgba(109,213,237,.2) !important;
}

/* Hide the expand_more icon */
div.st-key-create_project_cta button[data-testid="stPopoverButton"] svg {
  display: none !important;
}

/* =========================
   Create Project Popover - Premium Glass Card
   ========================= */

/* Reset trigger wrapper (no frame around button) */
div.st-key-create_project_cta [data-testid="stPopover"] {
  background: transparent !important;
}

div.st-key-create_project_cta [data-testid="stPopover"] > div {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
}

/* =========================
   Popover panels - stable via wrapper containers
   ========================= */

/* shared defaults (panel visuals moved to wrapper containers below) */
div[data-testid="stPopoverBody"]{
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
}

/* Create Project popover wrapper */
div[data-testid="stPopoverBody"] [class*="st-key-cp_popover_create"]{
  background: var(--card) !important;
  border: 1px solid var(--card-border) !important;
  border-radius: 18px !important;
  box-shadow: 0 30px 90px rgba(0, 0, 0, 0.62), inset 0 0 16px rgba(0, 0, 0, 0.10) !important;
  backdrop-filter: blur(12px) !important;
  -webkit-backdrop-filter: blur(12px) !important;
  padding: 18px 18px 16px 18px !important;
  min-width: 360px !important;
}

/* Manage Project popover wrapper (key is per-project: cp_popover_manage_<id>) */
div[data-testid="stPopoverBody"] [class*="st-key-cp_popover_manage_"]{
  background: var(--card) !important;
  border: 1px solid var(--card-border) !important;
  border-radius: 18px !important;
  box-shadow: 0 24px 72px rgba(0, 0, 0, 0.60), inset 0 0 16px rgba(0, 0, 0, 0.10) !important;
  backdrop-filter: blur(12px) !important;
  -webkit-backdrop-filter: blur(12px) !important;
  padding: 16px !important;
  min-width: 360px !important;
}

/* hard reset inner wrappers for BOTH popovers */
div[data-testid="stPopoverBody"] [class*="st-key-cp_popover_create"] *,
div[data-testid="stPopoverBody"] [class*="st-key-cp_popover_manage_"] *{
  background: transparent !important;
  border: none !important;
  outline: none !important;
  box-shadow: none !important;
  border-radius: 0 !important;
}

/* Title */
div[data-testid="stPopoverBody"] [class*="st-key-cp_popover_create"] .manage-modal-title {
  color: var(--text) !important;
  font-size: 18px !important;
  font-weight: 750 !important;
  letter-spacing: 0.2px !important;
  margin-bottom: 6px !important;
}

/* Subtitle */
div[data-testid="stPopoverBody"] [class*="st-key-cp_popover_create"] .manage-modal-sub {
  color: var(--muted) !important;
  font-size: 13px !important;
  line-height: 1.35 !important;
  margin-bottom: 14px !important;
}

/* Input wrapper (BaseWeb) */
div[data-testid="stPopoverBody"] [class*="st-key-cp_popover_create"] [data-testid="stTextInputRootElement"] {
  background: rgba(10, 12, 18, 0.55) !important;
  border: 1px solid rgba(148, 163, 184, 0.22) !important;
  border-radius: 12px !important;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04) !important;
}

div[data-testid="stPopoverBody"] [class*="st-key-cp_popover_create"] [data-testid="stTextInputRootElement"]:focus-within {
  border-color: rgba(109, 213, 237, 0.55) !important;
  box-shadow: 0 0 0 3px rgba(109, 213, 237, 0.18) !important;
}

/* Input text */
div[data-testid="stPopoverBody"] [class*="st-key-cp_popover_create"] input[type="text"] {
  color: var(--text) !important;
  font-size: 14px !important;
  padding: 11px 12px !important;
}

div[data-testid="stPopoverBody"] [class*="st-key-cp_popover_create"] input[type="text"]::placeholder {
  color: rgba(139, 152, 180, 0.85) !important;
}

/* Hide submit button inside Create Project popover */
div[data-testid="stPopoverBody"] [class*="st-key-cp_popover_create"] [data-testid="stFormSubmitButton"] {
  display: none !important;
}

/* Hide Streamlit default "Press Enter to submit form" hint */
div[data-testid="stPopoverBody"] [class*="st-key-cp_popover_create"] form small {
  display: none !important;
}

/* Helper text under input (subtitle moved below) */
div[data-testid="stPopoverBody"] [class*="st-key-cp_popover_create"] .create-project-helper {
  margin-top: 8px !important;
  color: var(--muted) !important;
  font-size: 12px !important;
  line-height: 1.4 !important;
  opacity: 0.85 !important;
}

/* Section titles - Manage project */
div[data-testid="stPopoverBody"] [class*="st-key-cp_popover_manage_"] [data-testid="stCaptionContainer"] p {
  color: var(--text) !important;
  font-size: 14px !important;
  font-weight: 700 !important;
  margin: 0 0 12px 0 !important;
}

/* Danger zone title - with red accent */
div[data-testid="stPopoverBody"] [class*="st-key-cp_popover_manage_"] .manage-danger-title {
  color: rgba(255, 140, 140, 0.95) !important;
  font-size: 12px !important;
  font-weight: 800 !important;
  margin: 12px 0 10px 0 !important;
}

/* Divider - subtle line */
div[data-testid="stPopoverBody"] [class*="st-key-cp_popover_manage_"] hr {
  border: none !important;
  height: 1px !important;
  background: var(--card-border) !important;
  opacity: 0.5 !important;
  margin: 10px 0 !important;
}

/* Input wrapper */
div[data-testid="stPopoverBody"] [class*="st-key-cp_popover_manage_"] [data-testid="stTextInputRootElement"] {
  background: rgba(10, 12, 18, 0.55) !important;
  border: 1px solid rgba(148, 163, 184, 0.22) !important;
  border-radius: 12px !important;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04) !important;
}

/* Input focus ring */
div[data-testid="stPopoverBody"] [class*="st-key-cp_popover_manage_"] [data-testid="stTextInputRootElement"]:focus-within {
  border-color: rgba(109, 213, 237, 0.55) !important;
  box-shadow: 0 0 0 3px rgba(109, 213, 237, 0.18) !important;
}

/* Input text */
div[data-testid="stPopoverBody"] [class*="st-key-cp_popover_manage_"] input[type="text"] {
  color: var(--text) !important;
  font-size: 14px !important;
  padding: 11px 12px !important;
}

/* Buttons container */
div[data-testid="stPopoverBody"] [class*="st-key-cp_popover_manage_"] [data-testid="stHorizontalBlock"] {
  gap: 8px !important;
}

/* Save button - secondary style */
div[data-testid="stPopoverBody"] [class*="st-key-cp_popover_manage_"] [data-testid="stBaseButton-secondary"] {
  width: 100% !important;
  border-radius: 12px !important;
  padding: 10px 14px !important;
  font-weight: 700 !important;
  border: 1px solid rgba(148, 163, 184, 0.22) !important;
  background: rgba(10, 12, 18, 0.55) !important;
  color: var(--text) !important;
}

div[data-testid="stPopoverBody"] [class*="st-key-cp_popover_manage_"] [data-testid="stBaseButton-secondary"]:hover {
  border-color: rgba(109, 213, 237, 0.35) !important;
  background: rgba(10, 12, 18, 0.70) !important;
  box-shadow: 0 10px 24px rgba(0, 0, 0, 0.35) !important;
}

/* Delete button - danger style */
div[data-testid="stPopoverBody"] [class*="st-key-cp_popover_manage_"] [data-testid="stBaseButton-primary"] {
  width: 100% !important;
  border-radius: 12px !important;
  padding: 10px 14px !important;
  font-weight: 800 !important;
  border: 1px solid rgba(255, 100, 100, 0.35) !important;
  background: rgba(255, 100, 100, 0.12) !important;
  color: rgba(255, 160, 160, 0.95) !important;
}

div[data-testid="stPopoverBody"] [class*="st-key-cp_popover_manage_"] [data-testid="stBaseButton-primary"]:hover {
  background: rgba(255, 100, 100, 0.18) !important;
  border-color: rgba(255, 100, 100, 0.50) !important;
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.40) !important;
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
  transition: transform .18s ease, box-shadow .2s ease, border-color .2s ease;

  border:1px solid rgba(148,163,184,0.14);
  background: rgba(15,23,42,0.18);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);

  box-shadow:
    0 18px 60px rgba(0,0,0,0.35),
    inset 0 1px 0 rgba(255,255,255,0.06);

  overflow:hidden;
}
.project-card:hover{
  transform: translateY(-3px);
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
  content: "\\01F4C4";
  font-size: 13px;
  opacity: 0.75;
}
.project-file-chip.empty{
  color: rgba(139,152,180,0.65);
  font-style: italic;
}
.project-file-chip.empty::before{
  content: "\\2014";
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

.admin-sidebar{
  display:flex;
  flex-direction:column;
  gap:14px;
}
.admin-card{
  border-radius:16px;
  padding:16px;
  border:1px solid rgba(148,163,184,0.18);
  background: linear-gradient(180deg, rgba(13,18,35,0.92), rgba(8,12,24,0.88));
  box-shadow: 0 18px 36px rgba(0,0,0,0.35);
}
.admin-card-title{
  font-size:12px;
  text-transform:uppercase;
  letter-spacing:0.12em;
  color: rgba(157,168,198,0.85);
}
.admin-user{ display:flex; align-items:center; gap:12px; margin-top:12px; }
.admin-avatar{
  width:42px; height:42px;
  border-radius:50%;
  border:1px solid rgba(148,163,184,0.35);
  object-fit:cover;
}
.admin-avatar-wrap{ position:relative; width:42px; height:42px; flex:0 0 auto; }
.admin-avatar-wrap .admin-avatar,
.admin-avatar-wrap .admin-avatar-fallback{ width:42px; height:42px; }
.admin-avatar-fallback{ position:absolute; inset:0; display:none; }
.admin-avatar.placeholder{
  display:flex;
  align-items:center;
  justify-content:center;
  background: rgba(109,213,237,0.12);
  color: var(--accent);
  font-weight:700;
}
.admin-user-info{ display:flex; flex-direction:column; gap:2px; min-width:0; }
.admin-name-row{ display:flex; align-items:center; gap:8px; }
.admin-name{ font-size:16px; font-weight:600; color: var(--text); }
.admin-badge{
  font-size:10px;
  text-transform:uppercase;
  letter-spacing:0.14em;
  padding:2px 8px;
  border-radius:999px;
  border:1px solid rgba(109,213,237,0.4);
  background: rgba(109,213,237,0.12);
  color: var(--accent);
}
.admin-email{ font-size:12px; color: var(--muted); word-break: break-word; }
.admin-meta{ margin-top:12px; font-size:12px; color: var(--muted); }
.admin-actions{ display:grid; gap:10px; margin-top:12px; }
.admin-button{
  display:inline-flex;
  align-items:center;
  justify-content:center;
  width:100%;
  padding:10px 12px;
  border-radius:12px;
  border:1px solid rgba(148,163,184,0.25);
  background: rgba(15,23,42,0.55);
  color: var(--text);
  text-decoration:none;
  font-weight:600;
  transition: border-color 0.2s ease, background 0.2s ease, box-shadow 0.2s ease;
}
.admin-button:hover{
  border-color: rgba(109,213,237,0.7);
  background: rgba(25,34,55,0.8);
  box-shadow: 0 10px 22px rgba(0,0,0,0.25);
}
.admin-button.ghost{ background: transparent; color: var(--muted); }

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


def should_disable_css() -> bool:
    params: dict[str, object] = {}
    try:
        params = dict(st.query_params)
    except Exception:
        getter = getattr(st, "experimental_get_query_params", None)
        if callable(getter):
            params = getter() or {}

    nocss_value = str(params.get("nocss", "")).strip().lower()
    if nocss_value in {"1", "true", "yes", "on"}:
        return True

    env_value = os.getenv("CHRONOPLAN_NO_CSS", "").strip().lower()
    return env_value in {"1", "true", "yes", "on"}


def inject_global_css() -> None:
    if should_disable_css():
        return
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
