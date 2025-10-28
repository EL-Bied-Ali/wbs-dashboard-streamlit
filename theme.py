import streamlit as st

CSS = """
<style>
/* ====== Layout global ====== */
header[data-testid="stHeader"]{opacity:1;min-height:48px;background:transparent;box-shadow:none}
.block-container{padding-top:1.2rem!important;max-width:2000px!important;padding-left:14px!important;padding-right:14px!important}
*{font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Arial}
:root{
  --bg:#0b1220; --glass:#0f172a; --glass2:#0b1224; --line:#1f2a44;
  --text:#e5e7eb; --muted:#94a3b8; --ok:#22c55e; --bad:#ef4444; --accent:#60a5fa;
  --col1:26%; --col2:10%; --col3:10%; --col4:15%; --col5:15%; --col6:8%; --col7:8%; --col8:8%;
  --fs-n1-title:1.9rem; --fs-n1-kpi:1.3rem; --fs-n1-label:.86rem;
  --fs-n2-title:1.25rem; --fs-n2-kpi:1.0rem; --fs-n2-label:.82rem;
  --fs-n3-head:.80rem; --fs-n3-cell:.92rem;
}
html,body{font-size:16px;line-height:1.35;background:#0a0f1c}

/* ====== Hero / N2 compact ====== */
.hero{background:linear-gradient(180deg,#0f1b34 0%,#0a1226 100%);
  border:1px solid rgba(96,165,250,.35);border-radius:16px;
  padding:12px 14px;margin:6px 0 10px}
.hero.compact .n1g-cell{padding:4px 6px}
.n1-grid{display:grid;
  grid-template-columns:var(--col1) var(--col2) var(--col3) var(--col4)
                        var(--col5) var(--col6) var(--col7) var(--col8);
  align-items:center}
.n1g-label{display:flex;align-items:center;gap:8px;padding:4px 6px}
.n1g-label .title{font-size:var(--fs-n1-title);font-weight:800;color:#f1f5f9}
.n1g-cell{display:flex;flex-direction:column;align-items:flex-start}
.n1g-cell .small{font-size:var(--fs-n1-label);color:#aab4c3;letter-spacing:.2px;margin-bottom:2px}
.n1g-cell b.ok{color:var(--ok)} .n1g-cell b.bad{color:var(--bad)}

.n2-grid{display:grid;
  grid-template-columns:var(--col1) var(--col2) var(--col3) var(--col4)
                        var(--col5) var(--col6) var(--col7) var(--col8);
  align-items:center;padding:4px 6px}
.n2-grid.compact .n2g-label,.n2-grid.compact .n2g-cell{padding:4px 6px}
.n2g-label{display:flex;align-items:center;gap:8px}
.n2g-label .title{font-size:var(--fs-n2-title);font-weight:750;color:#eaf2ff}
.n2g-cell .small{font-size:var(--fs-n2-label);color:#aab4c3;margin-bottom:2px}

/* ====== Mini bars ====== */
.mbar-wrap{display:flex;align-items:center;gap:6px}
.mbar{position:relative;height:9px;background:#1f2a44;border-radius:999px;overflow:hidden}
.mfill{display:block;height:100%;border-radius:999px;transition:width .35s ease}
.mfill.blue{background:#3b82f6}.mfill.green{background:#22c55e}
.mval{font-weight:650;color:var(--text);font-size:.9rem;min-width:46px;text-align:right}
.hero .mbar{width:130px!important;height:10px}
.n2-grid .mbar{width:120px!important;height:9px}
.table-card .mbar{width:100px!important;height:8px}
@keyframes growBar{from{width:0}to{width:var(--to,0%)}}.mfill.anim{animation:growBar .6s ease-out both}

/* ====== Tableau compact ====== */
.table-card{background:linear-gradient(180deg,rgba(15,23,42,.65),rgba(11,18,36,.6));
  border:1px solid #1f2a44;border-radius:12px;padding:8px 10px;margin:6px 0}
.table-card.compact table.neo thead th{font-size:var(--fs-n3-head);padding:6px 8px}
.table-card.compact table.neo td{padding:6px 8px;font-size:var(--fs-n3-cell)}
.table-card table.neo{width:100%;border-collapse:separate;border-spacing:0;table-layout:fixed}
.table-card table.neo thead{display:none}
.table-card tbody tr:hover{background:rgba(148,163,184,.06)}
.dot{width:7px;height:7px;background:var(--accent);border-radius:999px;display:inline-block}

/* ====== Radios sur la PAGE (à droite) ====== */
div[data-testid="stVerticalBlock"] [role="radiogroup"]{display:flex;flex-direction:column;gap:6px}
div[data-testid="stVerticalBlock"] [role="radiogroup"] label[data-baseweb="radio"]{
  position:relative;display:flex;align-items:center;gap:8px;width:100%;
  padding:8px 10px;border-radius:8px;
  background:linear-gradient(180deg,#0f1a31,#0b1326);
  border:1px solid rgba(96,165,250,.28);
  transition:border-color .15s ease,background .15s ease,transform .10s ease;cursor:pointer}
div[data-testid="stVerticalBlock"] [role="radiogroup"] label[data-baseweb="radio"]:hover{
  border-color:rgba(125,211,252,.8);transform:translateY(-1px)}
div[data-testid="stVerticalBlock"] [role="radiogroup"] label[data-baseweb="radio"]:has(input:checked){
  border-color:rgba(125,211,252,.95);
  background:linear-gradient(180deg,#0f1b34,#0b1326);
  box-shadow:inset 0 0 0 1px rgba(96,165,250,.45)}
div[data-testid="stVerticalBlock"] [role="radiogroup"] label[data-baseweb="radio"]:has(input:checked)::before{
  content:"";position:absolute;left:0;top:0;bottom:0;width:3px;
  background:linear-gradient(180deg,#60a5fa,#22c55e);
  border-top-left-radius:8px;border-bottom-left-radius:8px}

/* ====== Radios dans la SIDEBAR (si tu les utilises encore) ====== */
section[data-testid="stSidebar"] [role="radiogroup"]{display:flex;flex-direction:column;gap:6px}
section[data-testid="stSidebar"] label[data-baseweb="radio"]{
  position:relative;display:flex;align-items:center;gap:10px;width:100%;
  box-sizing:border-box;padding:8px 12px;border-radius:10px;
  background:linear-gradient(180deg,#0f1a31,#0b1326);border:1px solid rgba(96,165,250,.25);
  transition:border-color .15s ease,background .15s ease,transform .10s ease;cursor:pointer}
section[data-testid="stSidebar"] label[data-baseweb="radio"]:hover{border-color:rgba(125,211,252,.7);transform:translateY(-1px)}
section[data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked){
  border-color:rgba(125,211,252,.95);background:linear-gradient(180deg,#0f1b34,#0b1326);
  box-shadow:inset 0 0 0 1px rgba(96,165,250,.45)}
section[data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked)::before{
  content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:linear-gradient(180deg,#60a5fa,#22c55e);
  border-top-left-radius:10px;border-bottom-left-radius:10px}

/* ====== Divers ====== */
.ok{color:var(--ok);font-weight:700}.bad{color:var(--bad);font-weight:700}
button[data-testid="stSidebarCollapseButton"]{top:10px;left:10px}
</style>
"""

def inject_theme():
    st.markdown(CSS, unsafe_allow_html=True)
