import streamlit as st

CSS = """
<style>
/* ============ Layout global ============ */
header[data-testid="stHeader"]{
  opacity:1; height:auto; min-height:48px;
  background:transparent; box-shadow:none;
}
.block-container{
  padding-top:1.4rem!important; max-width:2000px!important;
  padding-left:16px!important; padding-right:16px!important;
}
*{font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Arial}
html, body { font-size:17px; line-height:1.4; }

/* ============ Tokens ============ */
:root{
  --bg:#0b1220; --glass:#0f172a; --glass2:#0b1224; --line:#1f2a44;
  --text:#e5e7eb; --muted:#94a3b8; --ok:#22c55e; --bad:#ef4444; --accent:#60a5fa;

  --col1:26%; --col2:10%; --col3:10%; --col4:15%;
  --col5:15%; --col6:8%;  --col7:8%;  --col8:8%;

  --fs-n1-title:2.1rem; --fs-n1-kpi:1.55rem; --fs-n1-label:0.95rem;
  --fs-n2-title:1.55rem; --fs-n2-kpi:1.15rem; --fs-n2-label:0.90rem;
  --fs-n3-head:0.90rem;  --fs-n3-cell:0.96rem; --fs-small:0.82rem;
}

/* ============ Hero (Niveau 1) ============ */
.hero{
  background: radial-gradient(1600px 500px at 20% -20%, rgba(59,130,246,.18), transparent 60%),
              linear-gradient(180deg,#0f1b34 0%,#0a1226 100%);
  border:1px solid rgba(96,165,250,.35);
  border-radius:18px; padding:18px 20px; margin:8px 0 16px;
  box-shadow:0 18px 30px rgba(0,0,0,.35), inset 0 0 0 1px rgba(59,130,246,.15);
  animation: fadeSlideUp .45s ease both;
}
.hero .title{
  font-size:var(--fs-n1-title)!important; font-weight:800; color:var(--text);
  text-shadow:0 0 18px rgba(59,130,246,.25); letter-spacing:.2px;
}
.hero .badge{
  margin-left:12px; padding:3px 10px; font-weight:700; border:1px solid rgba(96,165,250,.5);
  background:linear-gradient(180deg,rgba(14,165,233,.18),rgba(14,165,233,.10));
  border-radius:999px; color:#cffafe; font-size:.88rem;
}
.hero .n1-grid{
  display:grid; grid-template-columns:var(--col1) var(--col2) var(--col3) var(--col4) var(--col5) var(--col6) var(--col7) var(--col8);
  align-items:center; gap:0; width:100%;
}
.hero .n1g-label{display:flex; align-items:center; gap:8px; flex-wrap:wrap; padding:6px 8px;}
.hero .n1g-label .title{font-size:1.22rem; font-weight:800; color:#f1f5f9; text-shadow:0 0 8px rgba(59,130,246,.25);}
.hero .n1g-cell{display:flex; flex-direction:column; align-items:flex-start; padding:6px 8px;}
.hero .n1g-cell .small{
  font-size:var(--fs-n1-label); color:#aab4c3; text-transform:uppercase; letter-spacing:.3px; margin-bottom:4px;
}
.hero .n1g-cell b{font-size:var(--fs-n1-kpi); font-weight:700; color:var(--text);}
.hero .n1g-cell b.ok{color:var(--ok)!important;} .hero .n1g-cell b.bad{color:var(--bad)!important;}

/* ============ Section / Carte N2 ============ */
.section-card{
  background:linear-gradient(180deg,#0f1a31,#0b1326);
  border:1px solid #223355; border-radius:12px; padding:8px 10px; margin:4px 0 6px;
  box-shadow:0 0 0 1px rgba(36,52,83,.35) inset; animation: fadeSlideUp .45s ease .05s both;
}
.n2-grid{
  display:grid; grid-template-columns:var(--col1) var(--col2) var(--col3) var(--col4) var(--col5) var(--col6) var(--col7) var(--col8);
  align-items:center; gap:0; padding:6px 8px; row-gap:2px;
}
.n2g-label,.n2g-cell{padding:6px 8px!important; box-sizing:border-box;}
.n2g-label{display:flex; align-items:center; gap:8px; flex-wrap:wrap;}
.n2g-label .title{font-size:var(--fs-n2-title); font-weight:750; color:#f1f5f9; text-shadow:0 0 6px rgba(59,130,246,.25);}
.n2g-label .badge{
  padding:3px 10px; font-size:.88rem; font-weight:700; color:#cffafe;
  background:linear-gradient(180deg,rgba(14,165,233,.18),rgba(14,165,233,.10));
  border:1px solid rgba(96,165,250,.5); border-radius:999px;
  transition: transform .15s ease, box-shadow .15s ease, border-color .15s ease;
}
.n2g-label .badge:hover{ transform: translateY(-1px); box-shadow: 0 6px 14px rgba(59,130,246,.25); border-color: rgba(96,165,250,.8); }
.n2g-cell{display:flex; flex-direction:column; align-items:flex-start; gap:1px!important;}
.n2g-cell .small{
  font-size:var(--fs-n2-label); color:#aab4c3; text-transform:uppercase; letter-spacing:.3px; margin-bottom:4px;
}
.n2g-cell b{font-size:var(--fs-n2-kpi); font-weight:700; color:var(--text);}
.n2g-cell b.ok{color:var(--ok)!important;} .n2g-cell b.bad{color:var(--bad)!important;}

/* ============ Tableau N3 ============ */
.table-card{
  background:linear-gradient(180deg,rgba(15,23,42,.65),rgba(11,18,36,.6));
  border:1px solid #1f2a44; border-radius:14px; padding:12px; margin:8px 0;
  box-shadow:0 6px 16px rgba(0,0,0,.22); overflow:hidden; animation: fadeSlideUp .45s ease .1s both;
}
table.neo{width:100%; border-collapse:separate; border-spacing:0; table-layout:fixed;}
table.neo thead th{
  font-size:var(--fs-n3-head)!important; letter-spacing:.3px; text-transform:uppercase;
  color:#aab4c3; font-weight:700; text-align:left; padding:10px 12px; white-space:nowrap;
}
table.neo td{ padding:12px; font-size:var(--fs-n3-cell)!important; color:var(--text); }
table.neo tbody tr:hover{ background:rgba(148,163,184,.06); transition:background .12s ease; }
.table-card .neo th:nth-child(1),.table-card .neo td:nth-child(1){width:var(--col1);}
.table-card .neo th:nth-child(2),.table-card .neo td:nth-child(2){width:var(--col2);}
.table-card .neo th:nth-child(3),.table-card .neo td:nth-child(3){width:var(--col3);}
.table-card .neo th:nth-child(4),.table-card .neo td:nth-child(4){width:var(--col4);}
.table-card .neo th:nth-child(5),.table-card .neo td:nth-child(5){width:var(--col5);}
.table-card .neo th:nth-child(6),.table-card .neo td:nth-child(6){width:var(--col6);}
.table-card .neo th:nth-child(7),.table-card .neo td:nth-child(7){width:var(--col7);}
.table-card .neo th:nth-child(8),.table-card .neo td:nth-child(8){width:var(--col8);}
.dot{width:8px; height:8px; background:var(--accent); border-radius:999px; display:inline-block; animation: pulseDot 2.2s ease-in-out infinite;}
.ok{color:var(--ok); font-weight:700;} .bad{color:var(--bad); font-weight:700;}
.table-card table.neo, .table-card table.neo *{ border:0 !important; box-shadow:none !important; }
.table-card table.neo thead{ display:none !important; }

/* ==== Barres horizontales (si tu les réactives) ==== */
.mbar-wrap{display:flex; align-items:center; gap:8px;}
.mbar{
  position:relative; height:10px; background:#1f2a44; border-radius:999px; overflow:hidden; flex-shrink:0;
}
.mfill{display:block; height:100%; border-radius:999px; transition:width .35s ease;}
/* Dans le drawer, on laisse l'animation piloter la largeur (pas de transition concurrente) */
div[data-testid="stExpanderDetails"] .mfill{ transition:none }

.mfill.blue{background:#3b82f6;} .mfill.green{background:#22c55e;}
.mval{ font-weight:700; color:var(--text); font-size:0.95rem; min-width:52px; text-align:right; }
.hero .mbar{width:150px!important; height:12px;} .section-card .mbar{width:130px!important; height:11px;}
.table-card .mbar{width:110px!important; height:10px;}
.hero .mval{font-size:1.10rem; font-weight:750;} .section-card .mval{font-size:1.02rem; font-weight:700;}
.table-card .mval{font-size:0.95rem; font-weight:650;}
@keyframes growBar { from { width:0 } to { width:var(--to, 0%) } }
.mfill.anim{ animation: growBar .7s ease-out both; }
@keyframes sheen { 0%{transform:translateX(-100%);opacity:0} 15%{opacity:.22} 85%{opacity:.22} 100%{transform:translateX(100%);opacity:0} }
.mbar::after{
  content:""; position:absolute; top:0; bottom:0; width:40%;
  background:linear-gradient(90deg, transparent, rgba(255,255,255,.12), transparent);
  animation: sheen 2.6s ease-in-out infinite; pointer-events:none;
}

/* ==== Sidebar toggle visible ==== */
button[data-testid="stSidebarCollapseButton"]{
  position: fixed; top:12px; left:12px; z-index:600; width:38px; height:38px; border-radius:10px;
  opacity:1!important; pointer-events:auto!important;
  background:rgba(15,23,42,.92)!important; border:1px solid rgba(96,165,250,.55)!important;
  box-shadow:0 6px 18px rgba(0,0,0,.35);
}
button[data-testid="stSidebarCollapseButton"] svg,
button[data-testid="stSidebarCollapseButton"] svg *{ fill:#e5f0ff!important; stroke:#e5f0ff!important; }
button[data-testid="stSidebarCollapseButton"]:hover{
  background:rgba(30,41,59,.95)!important; border-color:rgba(125,211,252,.9)!important; box-shadow:0 8px 22px rgba(0,0,0,.45);
}
button[data-testid="stSidebarCollapseButton"]:focus{ outline:2px solid rgba(125,211,252,.9); outline-offset:2px; }
@media (max-width:900px){ .block-container{ padding-top:2.2rem!important; } }

/* ====== Animations ====== */
@keyframes fadeSlideUp { from { opacity:0; transform:translateY(6px) } to { opacity:1; transform:translateY(0) } }
@keyframes pulseDot { 0%,100%{transform:scale(1);opacity:1} 50%{transform:scale(1.35);opacity:.75} }





/* Grand wrapper autour de TOUT le N2 (header + tables + charts) */
div[data-testid="stVerticalBlock"]:has(.n2-block-sentinel){
  background: linear-gradient(180deg, #0f1a31, #0b1326);
  border: 1px solid #223355;
  border-radius: 12px;
  padding: 10px 12px;           /* air interne pour tout le bloc */
  margin: 8px 0 14px;           /* espacement entre 2 blocs N2 */
  box-shadow: 0 0 0 1px rgba(36,52,83,.35) inset;
  overflow: hidden;
  box-sizing: border-box;
}

/* Le sentinel doit exister dans le DOM mais rester invisible */
.n2-block-sentinel{
  visibility: hidden;           /* pas display:none */
  height: 0; padding: 0; margin: 0;
}

/* Nettoyage des marges “fantômes” autour des markdown/cols */
div[data-testid="stVerticalBlock"]:has(.n2-block-sentinel) [data-testid="stMarkdownContainer"] > p{ margin:0 !important; }
div[data-testid="stVerticalBlock"]:has(.n2-block-sentinel) .stColumns,
div[data-testid="stVerticalBlock"]:has(.n2-block-sentinel) [data-testid="column"]{ overflow:visible; }

/* Aplatit la .section-card interne rendue par ton header HTML */
div[data-testid="stVerticalBlock"]:has(.n2-block-sentinel) .section-card{
  background:transparent !important; border:0 !important; box-shadow:none !important;
  padding:0 !important; margin:0 !important;
}
div[data-testid="stVerticalBlock"]:has(.n2-block-sentinel) .n2-grid{
  padding:6px 8px !important;
}

/* Bouton chevron dans la colonne de droite */
div[data-testid="stVerticalBlock"]:has(.n2-block-sentinel) .stButton{
  display:flex; align-items:center; justify-content:flex-end; margin-top:4px;
}
div[data-testid="stVerticalBlock"]:has(.n2-block-sentinel) .stButton button{
  border-radius:8px;
  background:rgba(15,23,42,.88);
  border:1px solid rgba(96,165,250,.45);
  color:#e5e7eb; font-weight:800; font-size:16px;
  min-height:28px; padding:0 .25rem;
}
div[data-testid="stVerticalBlock"]:has(.n2-block-sentinel) .stButton button:hover{
  background:rgba(30,41,59,.96);
  border-color:rgba(125,211,252,.9);
}

/* === Fix: dimensions des barres au Niveau 2 (sans .section-card) === */
.n2-grid .mbar{ width:130px!important; height:11px; }
.n2-grid .mval{ font-size:1.02rem; font-weight:700; }



/* Expander invisible (pas de ligne grise) */
div[data-testid="stExpander"],
div[data-testid="stExpander"] > details,
div[data-testid="stExpander"] > details > summary{
  border:0!important; background:transparent!important; box-shadow:none!important;
  margin:0!important; padding:0!important;
}
div[data-testid="stExpander"] > details > summary{
  display:none!important; height:0!important; line-height:0!important;
}
div[data-testid="stExpander"] > details > summary::-webkit-details-marker{ display:none!important }

/* ================= N3: animations (rejouent grâce au remount) ================= */
@keyframes n3Open{
  0%{max-height:0;opacity:0;transform:scaleY(.98) translateY(-6px)}
  100%{max-height:2000px;opacity:1;transform:scaleY(1) translateY(0)}
}
@keyframes n3Close{
  0%{max-height:2000px;opacity:1;transform:scaleY(1) translateY(0)}
  100%{max-height:0;opacity:0;transform:scaleY(.98) translateY(-6px)}
}
div[data-testid="stExpander"] > details > div[data-testid="stExpanderDetails"]{
  overflow:hidden; transform-origin:top; will-change:max-height,opacity,transform;
}
div[data-testid="stExpander"] > details[open] > div[data-testid="stExpanderDetails"]{
  animation:n3Open .60s cubic-bezier(.22,.61,.36,1) both!important;
}
div[data-testid="stExpander"] > details:not([open]) > div[data-testid="stExpanderDetails"]{
  animation:n3Close .45s ease both!important;
}





/* ===== Loaders Schedule/Earned (animation au chargement) ===== */
.mbar{position:relative;display:block;width:100%;height:8px;border-radius:6px;background:rgba(148,163,184,.18);overflow:hidden}
.mfill{display:block;height:100%;width:0;will-change:width}
.mfill.anim{animation:fillX .9s ease forwards;animation-delay:var(--delay,0ms)}
.mbar-wrap.v .mval{opacity:0;animation:valIn .5s ease forwards;animation-delay:calc(var(--delay,0ms) + .35s)}

@keyframes fillX{
  from{width:0}
  to{width:var(--to,0%)}
}
@keyframes valIn{
  from{opacity:0;transform:translateY(2px)}
  to{opacity:1;transform:translateY(0)}
}

/* Légers décalages pour un rendu plus fluide */
.n2-grid .mbar-wrap.v{--delay:90ms}
.table-card .mbar-wrap.v{--delay:40ms}

/* Respecte l’accessibilité */
@media (prefers-reduced-motion: reduce){
  .mfill.anim{animation:none;width:var(--to,0%)}
  .mbar-wrap.v .mval{animation:none;opacity:1}
}

/* N3: alternance v0/v1 pour forcer le replay des barres */
@keyframes n3FillA { from{width:0} to{width:var(--to,0%)} }
@keyframes n3FillB { from{width:0} to{width:var(--to,0%)} }

div[data-testid="stExpanderDetails"]:has(.n3load.v0) .mfill{ width:0 }
div[data-testid="stExpanderDetails"]:has(.n3load.v0) .mfill.anim{ animation:n3FillA .9s ease forwards }
div[data-testid="stExpanderDetails"]:has(.n3load.v0) .mbar-wrap.v .mval{ opacity:0; animation:valIn .5s ease .35s forwards }

div[data-testid="stExpanderDetails"]:has(.n3load.v1) .mfill{ width:0 }
div[data-testid="stExpanderDetails"]:has(.n3load.v1) .mfill.anim{ animation:n3FillB .9s ease forwards }
div[data-testid="stExpanderDetails"]:has(.n3load.v1) .mbar-wrap.v .mval{ opacity:0; animation:valIn .5s ease .35s forwards }

/* Dans le drawer, on laisse l'animation piloter la largeur (pas de transition concurrente) */
div[data-testid="stExpanderDetails"] .mfill{ transition:none }












/* ====== keyframes doublés pour rejouer (A/B) ====== */
@keyframes n3ChartInA { from{opacity:0;transform:translateY(12px) scale(.985)} to{opacity:1;transform:translateY(0) scale(1)} }
@keyframes n3ChartInB { from{opacity:0;transform:translateY(12px) scale(.985)} to{opacity:1;transform:translateY(0) scale(1)} }

@keyframes n3GrowA { from{transform:scaleY(0.001);opacity:0} to{transform:scaleY(1);opacity:1} }
@keyframes n3GrowB { from{transform:scaleY(0.001);opacity:0} to{transform:scaleY(1);opacity:1} }

/* ========== ENTREE DU FRAME PLOTLY ========== */
/* v0 -> utilise animation *A* */
details[open] [data-testid="stExpanderDetails"]
  .stElementContainer:has(.n3load.v0) ~ .stElementContainer
  [data-testid="stFullScreenFrame"],
details[open] [data-testid="stExpanderDetails"]
  .stElementContainer:has(.n3load.v0) ~ .stElementContainer
  [data-testid="stPlotlyChart"]{
  opacity:0;
  animation: n3ChartInA .6s cubic-bezier(.22,.61,.36,1) .25s forwards;
  will-change: opacity, transform;
}

/* v1 -> utilise animation *B* */
details[open] [data-testid="stExpanderDetails"]
  .stElementContainer:has(.n3load.v1) ~ .stElementContainer
  [data-testid="stFullScreenFrame"],
details[open] [data-testid="stExpanderDetails"]
  .stElementContainer:has(.n3load.v1) ~ .stElementContainer
  [data-testid="stPlotlyChart"]{
  opacity:0;
  animation: n3ChartInB .6s cubic-bezier(.22,.61,.36,1) .25s forwards;
  will-change: opacity, transform;
}

/* ========== CROISSANCE DES BARRES ========== */
/* v0 -> *A* */
details[open] [data-testid="stExpanderDetails"]
  .stElementContainer:has(.n3load.v0) ~ .stElementContainer
  .main-svg .barlayer{
  transform-origin: bottom;
  transform-box: view-box;
  transform: scaleY(0.001);
  opacity: 0;
  animation: n3GrowA .7s cubic-bezier(.22,.61,.36,1) .2s forwards;
  will-change: transform, opacity;
}
/* v1 -> *B* */
details[open] [data-testid="stExpanderDetails"]
  .stElementContainer:has(.n3load.v1) ~ .stElementContainer
  .main-svg .barlayer{
  transform-origin: bottom;
  transform-box: view-box;
  transform: scaleY(0.001);
  opacity: 0;
  animation: n3GrowB .7s cubic-bezier(.22,.61,.36,1) .2s forwards;
  will-change: transform, opacity;
}

/* Accessibilité */
@media (prefers-reduced-motion: reduce){
  details[open] [data-testid="stExpanderDetails"]
    .stElementContainer:has(.n3load.v0), 
  details[open] [data-testid="stExpanderDetails"]
    .stElementContainer:has(.n3load.v1){
    /* neutralise toutes les animations ciblées ci-dessus */
  }
  details[open] [data-testid="stExpanderDetails"]
    .stElementContainer:has(.n3load) ~ .stElementContainer
    [data-testid="stFullScreenFrame"],
  details[open] [data-testid="stExpanderDetails"]
    .stElementContainer:has(.n3load) ~ .stElementContainer
    [data-testid="stPlotlyChart"],
  details[open] [data-testid="stExpanderDetails"]
    .stElementContainer:has(.n3load) ~ .stElementContainer
    .main-svg .barlayer{
    animation:none !important; opacity:1 !important; transform:none !important;
  }
}



/* ===== Sidebar radio: full-width inline, equal-size buttons ===== */
section[data-testid="stSidebar"] [role="radiogroup"]{
  display:flex; flex-direction:column; gap:6px;
}

/* Each option row */
section[data-testid="stSidebar"] label[data-baseweb="radio"]{
  position:relative;
  display:flex; align-items:center; gap:10px;
  width:100%;                                 /* 👈 all same width */
  box-sizing:border-box;                      /* respect padding + border */
  padding:8px 12px;
  border-radius:10px;
  background:linear-gradient(180deg,#0f1a31,#0b1326);
  border:1px solid rgba(96,165,250,.25);
  transition:border-color .15s ease, background .15s ease, transform .10s ease;
  cursor:pointer;
}

/* Hide native input */
section[data-testid="stSidebar"] label[data-baseweb="radio"] > input{
  position:absolute; opacity:0; width:0; height:0; pointer-events:none;
}

/* Align icon + text inline */
section[data-testid="stSidebar"] label[data-baseweb="radio"] > div:first-child{
  flex:0 0 auto; display:flex; align-items:center;
}
section[data-testid="stSidebar"] label[data-baseweb="radio"] > div:last-child{
  flex:1 1 auto; display:flex; align-items:center;
}
section[data-testid="stSidebar"] label[data-baseweb="radio"] [data-testid="stMarkdownContainer"]{
  margin:0; line-height:1.2; width:100%;
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
}

/* Hover effect */
section[data-testid="stSidebar"] label[data-baseweb="radio"]:hover{
  border-color:rgba(125,211,252,.7);
  transform:translateY(-1px);
}

/* Selected (with left accent bar) */
section[data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked){
  border-color:rgba(125,211,252,.95);
  background:linear-gradient(180deg,#0f1b34,#0b1326);
  box-shadow:inset 0 0 0 1px rgba(96,165,250,.45);
}
section[data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked)::before{
  content:""; position:absolute; left:0; top:0; bottom:0; width:3px;
  background:linear-gradient(180deg,#60a5fa,#22c55e);
  border-top-left-radius:10px; border-bottom-left-radius:10px;
}








/* ===== Style titres WBS Niveau 2 ===== */
.n2g-label {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 12px;
  margin-bottom: 8px;
  background: linear-gradient(90deg, rgba(30,58,138,.25), rgba(15,23,42,.4));
  border-left: 3px solid #3b82f6;
  border-radius: 6px;
  color: #e2e8f0;
  font-weight: 600;
  font-size: 1.05rem;
  letter-spacing: 0.3px;
  text-shadow: 0 0 4px rgba(59,130,246,.3);
  transition: background .2s ease, border-color .2s ease;
}

.n2g-label:hover {
  border-color: #60a5fa;
  background: linear-gradient(90deg, rgba(37,99,235,.35), rgba(15,23,42,.5));
}

.n2g-label .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: linear-gradient(180deg,#60a5fa,#22c55e);
  box-shadow: 0 0 5px rgba(59,130,246,.5);
}

/* theme.py */
.n3chart{background:linear-gradient(180deg,rgba(15,23,42,.65),rgba(11,18,36,.6));
border:1px solid #1f2a44;border-radius:14px;padding:10px 12px;margin:8px 0}
.n3chart .modebar{background:rgba(15,23,42,.65)!important;border-radius:8px}

/* === Animation lueur horizontale sur toute la ligne (niveau 2) === */
.n2-grid:hover {
  position: relative;
  background: linear-gradient(90deg,
    rgba(37,99,235,0.05) 0%,
    rgba(37,99,235,0.18) 50%,
    rgba(37,99,235,0.05) 100%);
  background-size: 200% 100%;
  animation: n2RowGlow 0.9s ease forwards;
}

@keyframes n2RowGlow {
  0%   { background-position: 200% 0; }
  100% { background-position: 0 0; }
}

/* Overlay clic pleine largeur (même zone pour clic + hover) */
div[class*="st-key-n2_"][class*="__rowbtn"]{
  position: relative;
  z-index: 10;
  margin-top: -56px;   /* ajuste 48–60 si besoin */
  height: 56px;
}
div[class*="st-key-n2_"][class*="__rowbtn"] .stButton{ position:absolute; inset:0; }
div[class*="st-key-n2_"][class*="__rowbtn"] .stButton button{
  width:100%; height:100%;
  background: transparent; border:0; padding:0; margin:0; cursor:pointer;
  border-radius:12px;
}

/* Même glow/anim que la ligne directement SUR le bouton overlay */
div[class*="st-key-n2_"][class*="__rowbtn"] .stButton button:hover{
  background: linear-gradient(90deg,
    rgba(37,99,235,0.05) 0%,
    rgba(37,99,235,0.18) 50%,
    rgba(37,99,235,0.05) 100%);
  background-size: 200% 100%;
  animation: n2RowGlow .9s ease forwards;
  box-shadow: 0 0 0 1px rgba(88,113,179,.35) inset;
}

/* (optionnel) garde aussi le hover direct sur la ligne */
.n2-grid:hover{
  filter: brightness(1.05);
  box-shadow: 0 0 0 1px rgba(88,113,179,.35) inset;
  transition: filter .15s ease, box-shadow .15s ease;
}

div[class*="st-key-n2_"][class*="__rowbtn"] {
  position: relative;
  z-index: 10;

  /* 🔽 Décalage vertical : plus négatif = plus haut, moins négatif = plus bas */
  margin-top: -59px;    /* ← monte le bouton de ~3px (ajuste à -58, -60, etc.) */

  /* 🔼 Hauteur totale du bouton : plus grand = couvre plus bas */
  height: 57px;         /* ← augmente légèrement la zone cliquable */

  /* Tu peux aussi ajouter un léger décalage latéral si besoin */
  margin-left: 1mm;     /* ← décale vers la droite d’environ 1 millimètre */
  width: calc(100% - 1mm); /* ← pour que la largeur reste équilibrée */
}




</style>
"""

def inject_theme():
    st.markdown(CSS, unsafe_allow_html=True)
