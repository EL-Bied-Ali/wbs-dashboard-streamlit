import streamlit as st

CSS = """
<style>
/* ============ Layout global ============ */
header[data-testid="stHeader"]{
  opacity:1; height:auto; min-height:48px;
  background:transparent; box-shadow:none;
}
.block-container{
  position:relative;
  padding-top:1.4rem!important; max-width:2000px!important;
  padding-left:16px!important; padding-right:16px!important;
}
*{font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Arial}
html, body { font-size:17px; line-height:1.4; }
body{
  background:var(--bg);
  position:relative;
  min-height:100vh;
}

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

/* ============ Ambient background glows ============ */
.bg-aurora{
  position:fixed; inset:-12% -8%;
  filter:blur(120px);
  opacity:0.55;
  pointer-events:none;
  z-index:-2;
  transform:translateZ(0);
}
.bg-aurora.a1{
  background:
    radial-gradient(circle at 18% 16%, rgba(59,130,246,.32), transparent 42%),
    radial-gradient(circle at 82% 12%, rgba(34,197,94,.28), transparent 46%);
  animation: driftA 22s ease-in-out infinite alternate;
}
.bg-aurora.a2{
  background:
    radial-gradient(circle at 14% 80%, rgba(14,165,233,.3), transparent 45%),
    radial-gradient(circle at 74% 72%, rgba(59,130,246,.25), transparent 52%);
  animation: driftB 26s ease-in-out infinite alternate;
}
.bg-aurora.grid{
  opacity:0.2;
  background:
    repeating-linear-gradient(90deg, rgba(148,163,184,.06) 0, rgba(148,163,184,.06) 1px, transparent 1px, transparent 120px),
    repeating-linear-gradient(0deg, rgba(148,163,184,.05) 0, rgba(148,163,184,.05) 1px, transparent 1px, transparent 120px);
  mask-image: radial-gradient(circle at 30% 30%, rgba(255,255,255,.5), transparent 55%),
              radial-gradient(circle at 70% 60%, rgba(255,255,255,.5), transparent 60%);
}
@keyframes driftA{
  from{ transform: translate(-6%, -4%) scale(1.02); }
  to  { transform: translate(4%, 6%) scale(1.05); }
}
@keyframes driftB{
  from{ transform: translate(6%, 8%) scale(1.04); }
  to  { transform: translate(-5%, -6%) scale(1.01); }
}

/* ============ Main glass frame ============ */

/* ============ Hero (Niveau 1) ============ */
.hero{
  position:relative;
  overflow:hidden;
  background: radial-gradient(1600px 500px at 20% -20%, rgba(59,130,246,.18), transparent 60%),
              linear-gradient(180deg,#0f1b34 0%,#0a1226 100%);
  border:1px solid rgba(96,165,250,.35);
  border-radius:18px; padding:14px 16px; margin:6px 0 12px;
  box-shadow:0 18px 30px rgba(0,0,0,.35), inset 0 0 0 1px rgba(59,130,246,.15);
  animation: fadeSlideUp .45s ease both;
}
.hero::before{
  content:"";
  position:absolute;
  inset:-12px -12px -18px -12px;
  background:
    radial-gradient(120% 120% at 18% -10%, rgba(96,165,250,.28), transparent 55%),
    radial-gradient(120% 120% at 82% -10%, rgba(34,197,94,.22), transparent 55%);
  opacity:0.55;
  filter:blur(12px);
  z-index:0;
  pointer-events:none;
}
.hero > *{ position:relative; z-index:1; }
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
  align-items:center; gap:0; padding:4px 8px; row-gap:0;
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

/* ==== Divider styling ==== */
hr{
  border-color: rgba(148,163,184,.28)!important;
  opacity:1;
  margin:8px 0 4px!important;
}

/* === Espace à droite du tableau === */
.block-container{
  margin-left: 0 !important;
  padding-right: 330px !important; /* largeur du panneau + marge */
}

/* ====== Animations ====== */
@keyframes fadeSlideUp { from { opacity:0; transform:translateY(6px) } to { opacity:1; transform:translateY(0) } }
@keyframes pulseDot { 0%,100%{transform:scale(1);opacity:1} 50%{transform:scale(1.35);opacity:.75} }







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
.mfill{display:block;height:100%;width:var(--to,0%);will-change:width}
.mfill.anim{animation:fillX_a .9s ease forwards;animation-delay:var(--delay,0ms)}
.mfill.anim.av1{animation-name:fillX_b;}
.mbar-wrap.v .mval{opacity:0;animation:valIn .5s ease forwards;animation-delay:calc(var(--delay,0ms) + .35s)}

@keyframes fillX_a{
  from{width:0}
  to{width:var(--to,0%)}
}
@keyframes fillX_b{
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
  align-items: flex-start;
  gap: 0 !important;              /* annule l'ancien gap:8px!important */
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

  /* réserve de la place à gauche pour le point */
  position: relative;
  padding-left: 36px !important;  /* ⬅ now overrides l’ancien padding!important */
}

/* point + glow + position fixe */
.n2g-label .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: linear-gradient(180deg,#60a5fa,#22c55e);
  box-shadow: 0 0 5px rgba(59,130,246,.5);
  position: absolute;
  left: 16px;
  top: 50%;
  transform: translateY(-50%);
}

.n2g-label:hover {
  border-color: #60a5fa;
  background: linear-gradient(90deg, rgba(37,99,235,.35), rgba(15,23,42,.5));
}





/* === N3 CHART STYLE === */
.n3chart {
  background: linear-gradient(180deg, rgba(15,23,42,.65), rgba(11,18,36,.6));
  border: 1px solid #1f2a44; border-radius: 14px;
  padding: 10px 12px; margin: 8px 0;
}
.n3chart .modebar {
  background: rgba(15,23,42,.65)!important;
  border-radius: 8px;
}

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

/* === Overlay clic pleine largeur (N2) === */
div[class*="st-key-n2_"][class*="__rowbtn"]{
  position: relative; z-index: 10;
  margin-top: -70px; height: 57px;
  margin-left: 2mm; width: calc(100% - 1mm);
}
div[class*="st-key-n2_"][class*="__rowbtn"] .stButton{ position:absolute; inset:0; }
div[class*="st-key-n2_"][class*="__rowbtn"] .stButton button{
  width:100%; height:100%; background:transparent; border:0; padding:0; margin:0;
  cursor:pointer; border-radius:12px;
}
div[class*="st-key-n2_"][class*="__rowbtn"] .stButton button:hover{
  background:linear-gradient(90deg,rgba(37,99,235,.05),rgba(37,99,235,.18),rgba(37,99,235,.05));
  background-size:200% 100%; animation:n2RowGlow .9s ease forwards;
  box-shadow:0 0 0 1px rgba(88,113,179,.35) inset;
}

/* (optionnel) garde aussi le hover direct sur la ligne */
.n2-grid:hover {
  filter: brightness(1.05);
  box-shadow: 0 0 0 1px rgba(88,113,179,.35) inset;
  transition: filter .15s ease, box-shadow .15s ease;
}




/* ===== Mini-bars dans le tableau (.mfill avec --to) ===== */
.table-card .mbar{ display:block; overflow:hidden; border-radius:6px; }
.table-card .mfill{ display:block; height:8px; width:var(--to,0%); border-radius:6px; }

/* Rejoue l’animation à chaque rendu (compatible avec --to inline) */
.table-card .mfill.anim{ animation:mfillGrowA .8s cubic-bezier(.22,.61,.36,1) forwards; }
.table-card .mfill.anim.av1{ animation-name:mfillGrowB; }
@keyframes mfillGrowA{ 0%{ width:0 } 100%{ width:var(--to) } }
@keyframes mfillGrowB{ 0%{ width:0 } 100%{ width:var(--to) } }

/* Valeur qui fade-in */
.table-card .mbar-wrap.v .mval{ opacity:0; transform:translateY(2px); animation:valIn .45s ease .25s forwards; }
@keyframes valIn{ to{ opacity:1; transform:none } }


















/* Radiogroup à l’intérieur du contenu principal (hors sidebar) */
div[data-testid="stVerticalBlock"] .main-radios [role="radiogroup"]{
  display:flex; flex-direction:column; gap:8px;
}
div[data-testid="stVerticalBlock"] .main-radios label[data-baseweb="radio"],
/* on cible aussi ceux créés simplement sur la page */
div[data-testid="stVerticalBlock"] [role="radiogroup"] label[data-baseweb="radio"]{
  position:relative; display:flex; align-items:center; gap:10px; width:100%;
  box-sizing:border-box; padding:10px 12px; border-radius:10px;
  background:linear-gradient(180deg,#0f1a31,#0b1326); border:1px solid rgba(96,165,250,.28);
  transition:border-color .15s ease, background .15s ease, transform .10s ease; cursor:pointer;
}
div[data-testid="stVerticalBlock"] [role="radiogroup"] label[data-baseweb="radio"]:hover{
  border-color:rgba(125,211,252,.8); transform:translateY(-1px);
}
div[data-testid="stVerticalBlock"] [role="radiogroup"] label[data-baseweb="radio"]:has(input:checked){
  border-color:rgba(125,211,252,.95); background:linear-gradient(180deg,#0f1b34,#0b1326);
  box-shadow:inset 0 0 0 1px rgba(96,165,250,.45);
}
div[data-testid="stVerticalBlock"] [role="radiogroup"] label[data-baseweb="radio"]:has(input:checked)::before{
  content:""; position:absolute; left:0; top:0; bottom:0; width:3px;
  background:linear-gradient(180deg,#60a5fa,#22c55e);
  border-top-left-radius:10px; border-bottom-left-radius:10px;
}










/* === Radios sur la PAGE (colonne de droite) — compact & stylé === */
div[data-testid="stVerticalBlock"] [role="radiogroup"]{
  display:flex; flex-direction:column; gap:6px;
}
div[data-testid="stVerticalBlock"] [role="radiogroup"] label[data-baseweb="radio"]{
  position:relative; display:flex; align-items:center; gap:8px; width:100%;
  box-sizing:border-box; padding:8px 10px; border-radius:10px;
  background:linear-gradient(180deg,#0f1a31,#0b1326);
  border:1px solid rgba(96,165,250,.28);
  transition:border-color .15s ease, background .15s ease, transform .10s ease; cursor:pointer;
}
div[data-testid="stVerticalBlock"] [role="radiogroup"] label[data-baseweb="radio"]:hover{
  border-color:rgba(125,211,252,.8); transform:translateY(-1px);
}
div[data-testid="stVerticalBlock"] [role="radiogroup"] label[data-baseweb="radio"]:has(input:checked){
  border-color:rgba(125,211,252,.95); background:linear-gradient(180deg,#0f1b34,#0b1326);
  box-shadow:inset 0 0 0 1px rgba(96,165,250,.45);
}
div[data-testid="stVerticalBlock"] [role="radiogroup"] label[data-baseweb="radio"]:has(input:checked)::before{
  content:""; position:absolute; left:0; top:0; bottom:0; width:3px;
  background:linear-gradient(180deg,#60a5fa,#22c55e);
  border-top-left-radius:10px; border-bottom-left-radius:10px;
}
/* Texte sur une ligne, coupe propre */
div[data-testid="stVerticalBlock"] [role="radiogroup"] [data-testid="stMarkdownContainer"]{
  margin:0; line-height:1.2; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
}



/* === Panneau fixe à droite pour les boutons WBS === */
#onpage-selector-panel{
  position: fixed;
  top: 68px;
  right: 16px;
  width: 260px;
  z-index: 120;
  padding: 10px 12px;
  background: linear-gradient(180deg,#0f1a31,#0b1326);
  border: 1px solid rgba(96,165,250,.28);
  border-radius: 10px;
  box-shadow: 0 8px 18px rgba(0,0,0,.35);
}








/* === Panneau WBS (compact, sans scroll horizontal) === */
.st-key-wbs_selector_onpage[data-testid="stElementContainer"]{
  position: fixed;
  top: 120px;               /* Distance depuis le haut */
  right: 20px;              /* Distance du bord droit */
  width: 290px;             /* largeur du panneau */
  max-height: 78vh;         /* Hauteur max avant scroll vertical */
  overflow-y: auto;         /* Scroll vertical uniquement */
  overflow-x: hidden !important; /* Bloque le scroll horizontal */
  z-index: 1200;
  padding: 14px 16px;
  background:
    linear-gradient(145deg, rgba(17,24,39,.92), rgba(9,12,20,.90)),
    radial-gradient(220% 120% at 20% -10%, rgba(59,130,246,.16), transparent 50%);
  border: 1px solid rgba(125,211,252,.45);
  border-radius: 12px;
  box-shadow:
    0 14px 28px rgba(0,0,0,.42),
    inset 0 0 0 1px rgba(59,130,246,.20),
    inset 0 -1px 0 rgba(34,197,94,.12);
  backdrop-filter: blur(12px);
}

/* === Titre "WBS à afficher" === */
.st-key-wbs_selector_onpage [data-testid="stWidgetLabel"]{
  margin: 0 0 10px;
  color:#e5e7eb;
  font-weight:800;
  text-align:center;
  font-size:1.2rem;
  text-shadow:0 0 10px rgba(96,165,250,.4);
}

/* === Boutons radio === */
.st-key-wbs_selector_onpage [role="radiogroup"]{
  display:flex; flex-direction:column; gap:7px;
}
.st-key-wbs_selector_onpage label[data-baseweb="radio"]{
  background: linear-gradient(180deg,#0f1a31,#0b1326);
  border:1px solid rgba(96,165,250,.25);
  border-radius:10px;
  padding:9px 10px;
  font-size:1.05rem;
  transition:all .15s ease;
  color:#e2e8f0;
  cursor:pointer;
}
.st-key-wbs_selector_onpage label[data-baseweb="radio"]:hover{
  border-color:rgba(125,211,252,.7);
  transform:translateY(-1px);
}
.st-key-wbs_selector_onpage label[data-baseweb="radio"]:has(input:checked){
  border-color:rgba(125,211,252,.95);
  box-shadow:inset 0 0 0 1px rgba(96,165,250,.45);
}
.st-key-wbs_selector_onpage::-webkit-scrollbar{ width:8px; }
.st-key-wbs_selector_onpage::-webkit-scrollbar-thumb{
  background: linear-gradient(180deg, rgba(96,165,250,.55), rgba(34,197,94,.6));
  border-radius:999px;
}
.st-key-wbs_selector_onpage::-webkit-scrollbar-track{
  background:rgba(15,23,42,.6);
  border-radius:999px;
}
.st-key-wbs_selector_onpage{
  transition: box-shadow .2s ease, transform .2s ease, border-color .2s ease;
}
.st-key-wbs_selector_onpage:hover{
  box-shadow:
    0 18px 32px rgba(0,0,0,.48),
    inset 0 0 0 1px rgba(125,211,252,.35);
  transform: translateY(-1px);
  border-color: rgba(125,211,252,.45);
}

/* === Glass frame on main content (wraps hero + N2/N3) === */
.st-key-glass_wrap[data-testid="stVerticalBlock"],
.st-key-glass_wrap[data-testid="stElementContainer"]{
  position:relative;
  z-index:0;
  padding:12px 16px 16px;
  margin:4px 0 8px;
  display:block;
  overflow:hidden;
}
.st-key-glass_wrap[data-testid="stVerticalBlock"]::before,
.st-key-glass_wrap[data-testid="stVerticalBlock"]::after,
.st-key-glass_wrap[data-testid="stElementContainer"]::before,
.st-key-glass_wrap[data-testid="stElementContainer"]::after{
  content:"";
  position:absolute;
  inset:0;
  border-radius:18px;
  pointer-events:none;
}
.st-key-glass_wrap[data-testid="stVerticalBlock"]::before,
.st-key-glass_wrap[data-testid="stElementContainer"]::before{
  background:linear-gradient(180deg, rgba(15,23,42,.82), rgba(10,15,30,.88));
  border:1px solid rgba(125,211,252,.26);
  box-shadow:
    0 22px 38px rgba(0,0,0,.38),
    inset 0 0 0 1px rgba(59,130,246,.10);
  backdrop-filter: blur(10px);
  z-index:0;
  overflow:hidden;
}
.st-key-glass_wrap[data-testid="stVerticalBlock"]::after,
.st-key-glass_wrap[data-testid="stElementContainer"]::after{
  background:
    radial-gradient(1200px 420px at 28% 0%, rgba(59,130,246,.18), transparent 55%),
    radial-gradient(900px 380px at 70% 90%, rgba(34,197,94,.14), transparent 60%);
  opacity:.65;
  z-index:0;
}
.st-key-glass_wrap[data-testid="stVerticalBlock"] > *,
.st-key-glass_wrap[data-testid="stElementContainer"] > *{
  position:relative;
  z-index:1;
}

/* === Supprime tout scroll horizontal sur la page === */
html, body, [data-testid="stAppViewBlockContainer"]{
  overflow-x: hidden !important;
}



</style>
"""

def inject_theme():
    st.markdown(CSS, unsafe_allow_html=True)
