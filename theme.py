import streamlit as st

CSS = """
<style>
/* ============ Layout global ============ */
header[data-testid="stHeader"]{opacity:1;min-height:48px;background:transparent;box-shadow:none}
.block-container{padding-top:1.4rem!important;max-width:2000px!important;padding-left:16px!important;padding-right:16px!important}
*{font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Arial}
html,body{font-size:17px;line-height:1.4}

/* ============ Tokens ============ */
:root{
  --bg:#0b1220; --glass:#0f172a; --glass2:#0b1224; --line:#1f2a44;
  --text:#e5e7eb; --muted:#94a3b8; --ok:#22c55e; --bad:#ef4444; --accent:#60a5fa;
  --col1:26%; --col2:10%; --col3:10%; --col4:15%; --col5:15%; --col6:8%; --col7:8%; --col8:8%;
  --fs-n1-title:2.1rem; --fs-n1-kpi:1.55rem; --fs-n1-label:0.95rem;
  --fs-n2-title:1.55rem; --fs-n2-kpi:1.15rem; --fs-n2-label:0.90rem;
  --fs-n3-head:0.90rem;  --fs-n3-cell:0.96rem; --fs-small:0.82rem;
}

/* ============ Hero (Niveau 1) ============ */
.hero{
  background:radial-gradient(1600px 500px at 20% -20%,rgba(59,130,246,.18),transparent 60%),linear-gradient(180deg,#0f1b34 0%,#0a1226 100%);
  border:1px solid rgba(96,165,250,.35); border-radius:18px; padding:18px 20px; margin:8px 0 16px;
  box-shadow:0 18px 30px rgba(0,0,0,.35), inset 0 0 0 1px rgba(59,130,246,.15); animation:fadeSlideUp .45s ease both
}
.hero .title{font-size:var(--fs-n1-title)!important;font-weight:800;color:var(--text);text-shadow:0 0 18px rgba(59,130,246,.25);letter-spacing:.2px}
.hero .badge{margin-left:12px;padding:3px 10px;font-weight:700;border:1px solid rgba(96,165,250,.5);background:linear-gradient(180deg,rgba(14,165,233,.18),rgba(14,165,233,.10));border-radius:999px;color:#cffafe;font-size:.88rem}
.hero .n1-grid{display:grid;grid-template-columns:var(--col1) var(--col2) var(--col3) var(--col4) var(--col5) var(--col6) var(--col7) var(--col8);align-items:center;gap:0;width:100%}
.hero .n1g-label{display:flex;align-items:center;gap:8px;flex-wrap:wrap;padding:6px 8px}
.hero .n1g-label .title{font-size:1.22rem;font-weight:800;color:#f1f5f9;text-shadow:0 0 8px rgba(59,130,246,.25)}
.hero .n1g-cell{display:flex;flex-direction:column;align-items:flex-start;padding:6px 8px}
.hero .n1g-cell .small{font-size:var(--fs-n1-label);color:#aab4c3;text-transform:uppercase;letter-spacing:.3px;margin-bottom:4px}
.hero .n1g-cell b{font-size:var(--fs-n1-kpi);font-weight:700;color:var(--text)}
.hero .n1g-cell b.ok{color:var(--ok)!important}.hero .n1g-cell b.bad{color:var(--bad)!important}

/* ============ Section / Carte N2 ============ */
.section-card{
  background:linear-gradient(180deg,#0f1a31,#0b1326);
  border:1px solid #223355;border-radius:12px;padding:8px 10px;margin:4px 0 6px;
  box-shadow:0 0 0 1px rgba(36,52,83,.35) inset;animation:fadeSlideUp .45s ease .05s both
}
.n2-grid{display:grid;grid-template-columns:var(--col1) var(--col2) var(--col3) var(--col4) var(--col5) var(--col6) var(--col7) var(--col8);align-items:center;gap:0;padding:6px 8px;row-gap:2px}
.n2g-label,.n2g-cell{padding:6px 8px!important;box-sizing:border-box}
.n2g-label{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.n2g-label .title{font-size:var(--fs-n2-title);font-weight:750;color:#f1f5f9;text-shadow:0 0 6px rgba(59,130,246,.25)}
.n2g-label .badge{padding:3px 10px;font-size:.88rem;font-weight:700;color:#cffafe;background:linear-gradient(180deg,rgba(14,165,233,.18),rgba(14,165,233,.10));border:1px solid rgba(96,165,250,.5);border-radius:999px;transition:transform .15s ease,box-shadow .15s ease,border-color .15s ease}
.n2g-label .badge:hover{transform:translateY(-1px);box-shadow:0 6px 14px rgba(59,130,246,.25);border-color:rgba(96,165,250,.8)}
.n2g-cell{display:flex;flex-direction:column;align-items:flex-start;gap:1px!important}
.n2g-cell .small{font-size:var(--fs-n2-label);color:#aab4c3;text-transform:uppercase;letter-spacing:.3px;margin-bottom:4px}
.n2g-cell b{font-size:var(--fs-n2-kpi);font-weight:700;color:var(--text)}
.n2g-cell b.ok{color:var(--ok)!important}.n2g-cell b.bad{color:var(--bad)!important}

/* ============ Tableau N3 ============ */
.table-card{
  background:linear-gradient(180deg,rgba(15,23,42,.65),rgba(11,18,36,.6));
  border:1px solid #1f2a44;border-radius:14px;padding:12px;margin:8px 0;
  box-shadow:0 6px 16px rgba(0,0,0,.22);overflow:hidden;animation:fadeSlideUp .45s ease .1s both
}
table.neo{width:100%;border-collapse:separate;border-spacing:0;table-layout:fixed}
table.neo thead th{font-size:var(--fs-n3-head)!important;letter-spacing:.3px;text-transform:uppercase;color:#aab4c3;font-weight:700;text-align:left;padding:10px 12px;white-space:nowrap}
table.neo td{padding:12px;font-size:var(--fs-n3-cell)!important;color:var(--text)}
table.neo tbody tr:hover{background:rgba(148,163,184,.06);transition:background .12s ease}
.table-card .neo th:nth-child(1),.table-card .neo td:nth-child(1){width:var(--col1)}
.table-card .neo th:nth-child(2),.table-card .neo td:nth-child(2){width:var(--col2)}
.table-card .neo th:nth-child(3),.table-card .neo td:nth-child(3){width:var(--col3)}
.table-card .neo th:nth-child(4),.table-card .neo td:nth-child(4){width:var(--col4)}
.table-card .neo th:nth-child(5),.table-card .neo td:nth-child(5){width:var(--col5)}
.table-card .neo th:nth-child(6),.table-card .neo td:nth-child(6){width:var(--col6)}
.table-card .neo th:nth-child(7),.table-card .neo td:nth-child(7){width:var(--col7)}
.table-card .neo th:nth-child(8),.table-card .neo td:nth-child(8){width:var(--col8)}
.dot{width:8px;height:8px;background:var(--accent);border-radius:999px;display:inline-block;animation:pulseDot 2.2s ease-in-out infinite}
.ok{color:var(--ok);font-weight:700}.bad{color:var(--bad);font-weight:700}
.table-card table.neo,.table-card table.neo *{border:0!important;box-shadow:none!important}
.table-card table.neo thead{display:none!important}

/* ==== Mini-barres horizontales (Schedule/Earned) ==== */
.mbar-wrap{display:flex;align-items:center;gap:8px}
.mbar{position:relative;height:10px;background:#1f2a44;border-radius:999px;overflow:hidden;flex-shrink:0}
.mfill{display:block;height:100%;border-radius:999px;transition:width .35s ease}
div[data-testid="stExpanderDetails"] .mfill{transition:none} /* pas de transition concurrente dans le drawer */
.mfill.blue{background:#3b82f6}.mfill.green{background:#22c55e}
.mval{font-weight:700;color:var(--text);font-size:.95rem;min-width:52px;text-align:right}
.hero .mbar{width:150px!important;height:12px}.section-card .mbar{width:130px!important;height:11px}.table-card .mbar{width:110px!important;height:10px}
.hero .mval{font-size:1.10rem;font-weight:750}.section-card .mval{font-size:1.02rem;font-weight:700}.table-card .mval{font-size:.95rem;font-weight:650}
@keyframes growBar{from{width:0}to{width:var(--to,0%)}}
.mfill.anim{animation:growBar .7s ease-out both}
@keyframes sheen{0%{transform:translateX(-100%);opacity:0}15%{opacity:.22}85%{opacity:.22}100%{transform:translateX(100%);opacity:0}}
.mbar::after{content:"";position:absolute;top:0;bottom:0;width:40%;background:linear-gradient(90deg,transparent,rgba(255,255,255,.12),transparent);animation:sheen 2.6s ease-in-out infinite;pointer-events:none}

/* ==== Sidebar toggle visible ==== */
button[data-testid="stSidebarCollapseButton"]{
  position:fixed;top:12px;left:12px;z-index:600;width:38px;height:38px;border-radius:10px;opacity:1!important;pointer-events:auto!important;
  background:rgba(15,23,42,.92)!important;border:1px solid rgba(96,165,250,.55)!important;box-shadow:0 6px 18px rgba(0,0,0,.35)
}
button[data-testid="stSidebarCollapseButton"] svg,button[data-testid="stSidebarCollapseButton"] svg *{fill:#e5f0ff!important;stroke:#e5f0ff!important}
button[data-testid="stSidebarCollapseButton"]:hover{background:rgba(30,41,59,.95)!important;border-color:rgba(125,211,252,.9)!important;box-shadow:0 8px 22px rgba(0,0,0,.45)}
button[data-testid="stSidebarCollapseButton"]:focus{outline:2px solid rgba(125,211,252,.9);outline-offset:2px}
@media (max-width:900px){.block-container{padding-top:2.2rem!important}}

/* ====== Animations utilitaires ====== */
@keyframes fadeSlideUp{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
@keyframes pulseDot{0%,100%{transform:scale(1);opacity:1}50%{transform:scale(1.35);opacity:.75}}

/* ===== Expander invisible (pas de ligne grise) ===== */
div[data-testid="stExpander"],div[data-testid="stExpander"]>details,div[data-testid="stExpander"]>details>summary{
  border:0!important;background:transparent!important;box-shadow:none!important;margin:0!important;padding:0!important
}
div[data-testid="stExpander"]>details>summary{display:none!important;height:0!important;line-height:0!important}
div[data-testid="stExpander"]>details>summary::-webkit-details-marker{display:none!important}

/* ===== N3 open/close (wrapper du drawer) ===== */
@keyframes n3Open{0%{max-height:0;opacity:0;transform:scaleY(.98) translateY(-6px)}100%{max-height:2000px;opacity:1;transform:scaleY(1) translateY(0)}}
@keyframes n3Close{0%{max-height:2000px;opacity:1;transform:scaleY(1) translateY(0)}100%{max-height:0;opacity:0;transform:scaleY(.98) translateY(-6px)}}
div[data-testid="stExpander"]>details>div[data-testid="stExpanderDetails"]{overflow:hidden;transform-origin:top;will-change:max-height,opacity,transform}
div[data-testid="stExpander"]>details[open]>div[data-testid="stExpanderDetails"]{animation:n3Open .60s cubic-bezier(.22,.61,.36,1) both!important}
div[data-testid="stExpander"]>details:not([open])>div[data-testid="stExpanderDetails"]{animation:n3Close .45s ease both!important}

/* ===== N3: alternance v0/v1 pour rejouer les mini-barres HTML ===== */
@keyframes n3FillA{from{width:0}to{width:var(--to,0%)}}
@keyframes n3FillB{from{width:0}to{width:var(--to,0%)}}
div[data-testid="stExpanderDetails"]:has(.n3load.v0) .mfill{width:0}
div[data-testid="stExpanderDetails"]:has(.n3load.v0) .mfill.anim{animation:n3FillA .9s ease forwards}
div[data-testid="stExpanderDetails"]:has(.n3load.v0) .mbar-wrap.v .mval{opacity:0;animation:valIn .5s ease .35s forwards}
div[data-testid="stExpanderDetails"]:has(.n3load.v1) .mfill{width:0}
div[data-testid="stExpanderDetails"]:has(.n3load.v1) .mfill.anim{animation:n3FillB .9s ease forwards}
div[data-testid="stExpanderDetails"]:has(.n3load.v1) .mbar-wrap.v .mval{opacity:0;animation:valIn .5s ease .35s forwards}
@keyframes valIn{from{opacity:0;transform:translateY(2px)}to{opacity:1;transform:translateY(0)}}

/* ===== N3: animation Plotly (frame + couches barres) via .n3load v0/v1 ===== */
@keyframes n3ChartInA{from{opacity:0;transform:translateY(12px) scale(.985)}to{opacity:1;transform:translateY(0) scale(1)}}
@keyframes n3ChartInB{from{opacity:0;transform:translateY(12px) scale(.985)}to{opacity:1;transform:translateY(0) scale(1)}}
@keyframes n3GrowA{from{transform:scaleY(0.001);opacity:0}to{transform:scaleY(1);opacity:1}}
@keyframes n3GrowB{from{transform:scaleY(0.001);opacity:0}to{transform:scaleY(1);opacity:1)}

/* Entrée douce du conteneur Plotly */
details[open] [data-testid="stExpanderDetails"]
  .stElementContainer:has(.n3load.v0) ~ .stElementContainer
  [data-testid="stFullScreenFrame"],
details[open] [data-testid="stExpanderDetails"]
  .stElementContainer:has(.n3load.v0) ~ .stElementContainer
  [data-testid="stPlotlyChart"]{
  opacity:0;animation:n3ChartInA .6s cubic-bezier(.22,.61,.36,1) .25s forwards;will-change:opacity,transform
}
details[open] [data-testid="stExpanderDetails"]
  .stElementContainer:has(.n3load.v1) ~ .stElementContainer
  [data-testid="stFullScreenFrame"],
details[open] [data-testid="stExpanderDetails"]
  .stElementContainer:has(.n3load.v1) ~ .stElementContainer
  [data-testid="stPlotlyChart"]{
  opacity:0;animation:n3ChartInB .6s cubic-bezier(.22,.61,.36,1) .25s forwards;will-change:opacity,transform
}

/* Croissance des barres */
details[open] [data-testid="stExpanderDetails"]
  .stElementContainer:has(.n3load.v0) ~ .stElementContainer
  .main-svg .barlayer{
  transform-origin:bottom;transform-box:view-box;transform:scaleY(0.001);opacity:0;
  animation:n3GrowA .7s cubic-bezier(.22,.61,.36,1) .2s forwards;will-change:transform,opacity
}
details[open] [data-testid="stExpanderDetails"]
  .stElementContainer:has(.n3load.v1) ~ .stElementContainer
  .main-svg .barlayer{
  transform-origin:bottom;transform-box:view-box;transform:scaleY(0.001);opacity:0;
  animation:n3GrowB .7s cubic-bezier(.22,.61,.36,1) .2s forwards;will-change:transform,opacity
}

/* Accessibilité (réduit les animations si demandé) */
@media (prefers-reduced-motion: reduce){
  .mfill.anim{animation:none;width:var(--to,0%)}
  .mbar-wrap.v .mval{animation:none;opacity:1}
  details[open] [data-testid="stExpanderDetails"] .stElementContainer:has(.n3load) ~ .stElementContainer [data-testid="stFullScreenFrame"],
  details[open] [data-testid="stExpanderDetails"] .stElementContainer:has(.n3load) ~ .stElementContainer [data-testid="stPlotlyChart"],
  details[open] [data-testid="stExpanderDetails"] .stElementContainer:has(.n3load) ~ .stElementContainer .main-svg .barlayer{
    animation:none!important;opacity:1!important;transform:none!important
  }
}

/* ===== Sidebar radio (boutons pleine largeur) ===== */
section[data-testid="stSidebar"] [role="radiogroup"]{display:flex;flex-direction:column;gap:6px}
section[data-testid="stSidebar"] label[data-baseweb="radio"]{
  position:relative;display:flex;align-items:center;gap:10px;width:100%;box-sizing:border-box;padding:8px 12px;border-radius:10px;
  background:linear-gradient(180deg,#0f1a31,#0b1326);border:1px solid rgba(96,165,250,.25);
  transition:border-color .15s ease,background .15s ease,transform .10s ease;cursor:pointer
}
section[data-testid="stSidebar"] label[data-baseweb="radio"]>input{position:absolute;opacity:0;width:0;height:0;pointer-events:none}
section[data-testid="stSidebar"] label[data-baseweb="radio"]>div:first-child{flex:0 0 auto;display:flex;align-items:center}
section[data-testid="stSidebar"] label[data-baseweb="radio"]>div:last-child{flex:1 1 auto;display:flex;align-items:center}
section[data-testid="stSidebar"] label[data-baseweb="radio"] [data-testid="stMarkdownContainer"]{margin:0;line-height:1.2;width:100%;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
section[data-testid="stSidebar"] label[data-baseweb="radio"]:hover{border-color:rgba(125,211,252,.7);transform:translateY(-1px)}
section[data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked){
  border-color:rgba(125,211,252,.95);background:linear-gradient(180deg,#0f1b34,#0b1326);box-shadow:inset 0 0 0 1px rgba(96,165,250,.45)
}
section[data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked)::before{
  content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:linear-gradient(180deg,#60a5fa,#22c55e);
  border-top-left-radius:10px;border-bottom-left-radius:10px
}

/* === Overlay clic pleine largeur (N2) === */
div[class*="st-key-n2_"][class*="__rowbtn"]{position:relative;z-index:10;margin-top:-70px;height:57px;margin-left:2mm;width:calc(100% - 1mm)}
div[class*="st-key-n2_"][class*="__rowbtn"] .stButton{position:absolute;inset:0}
div[class*="st-key-n2_"][class*="__rowbtn"] .stButton button{width:100%;height:100%;background:transparent;border:0;padding:0;margin:0;cursor:pointer;border-radius:12px}
div[class*="st-key-n2_"][class*="__rowbtn"] .stButton button:hover{
  background:linear-gradient(90deg,rgba(37,99,235,.05),rgba(37,99,235,.18),rgba(37,99,235,.05));
  background-size:200% 100%;animation:n2RowGlow .9s ease forwards;box-shadow:0 0 0 1px rgba(88,113,179,.35) inset
}
.n2-grid:hover{filter:brightness(1.05);box-shadow:0 0 0 1px rgba(88,113,179,.35) inset;transition:filter .15s ease,box-shadow .15s ease}
@keyframes n2RowGlow{0%{background-position:200% 0}100%{background-position:0 0}}
</style>
"""

def inject_theme():
    st.markdown(CSS, unsafe_allow_html=True)
