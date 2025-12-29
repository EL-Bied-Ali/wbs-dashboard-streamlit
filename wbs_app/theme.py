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
html, body, [data-testid="stAppViewContainer"]{
  zoom:var(--ui-zoom);
}
.muted{ color:var(--muted); }
body{
  background:var(--bg);
  position:relative;
  min-height:100vh;
}
[data-testid="stAppViewContainer"]{
  position:relative;
  z-index:1;
  background: transparent !important;
}

/* ============ Tokens ============ */
:root{
  --bg:#0b1220; --glass:#0f172a; --glass2:#0b1224; --line:#1f2a44;
  --text:#e5e7eb; --muted:#94a3b8; --ok:#22c55e; --bad:#ef4444; --accent:#60a5fa;
  --ui-zoom:1;

  --col1:26%; --col2:10%; --col3:10%; --col4:15%;
  --col5:15%; --col6:8%;  --col7:8%;  --col8:8%;

  --bar-h:clamp(0.38rem,0.6vw,0.55rem);
  --bar-h-lg:clamp(0.5rem,0.9vw,0.75rem);
  --bar-w-lg:clamp(7.5rem,16vw,11rem);
  --bar-w-md:clamp(6.5rem,14vw,9.5rem);
  --bar-w-sm:clamp(5.5rem,12vw,8.5rem);

  --fs-n1-title:2.1rem; --fs-n1-kpi:1.55rem; --fs-n1-label:0.95rem;
  --fs-n2-title:1.55rem; --fs-n2-kpi:1.15rem; --fs-n2-label:0.90rem;
  --fs-n3-head:0.90rem;  --fs-n3-cell:0.96rem; --fs-small:0.82rem;
}

/* Ambient background glows removed to avoid bottom banding artifacts. */

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

/* Root hero toggle: full-card click without visible button */
div[class*="hero_wrap__"]{ position:relative; }
div[class*="hero_wrap__"] div[class*="__hero_toggle"]{ position:absolute; inset:0; margin:0; z-index:6; }
div[class*="hero_wrap__"] div[class*="__hero_toggle"] button{
  width:100%; height:100%; opacity:0; border:0; padding:0; margin:0;
}

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
.n2g-label .leaf-badge{
  margin-left:8px;
  font-size:0.95rem;
  color:#94a3b8;
  background:rgba(15,23,42,.6);
  border:1px solid rgba(148,163,184,.25);
  padding:2px 6px;
  border-radius:999px;
  line-height:1;
}
.n2-grid.depth-3 .n2g-label .title{font-size:1.18rem; opacity:.92;}
.n2-grid.depth-4 .n2g-label .title{font-size:1.08rem; opacity:.88;}
.n2-grid.depth-5 .n2g-label .title{font-size:1.02rem; opacity:.84;}
.n2-grid.depth-6 .n2g-label .title{font-size:0.98rem; opacity:.8;}
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
.table-card td.lvl{ padding-left:12px; }
.table-card td.lvl .indent{
  display:inline-flex; align-items:center; gap:8px;
  margin-left: calc(var(--indent, 0) * 14px);
}
.table-card tr.depth-1 td.lvl{
  background: linear-gradient(90deg, rgba(59,130,246,.12), rgba(59,130,246,.04) 60%, transparent);
  border-left: 3px solid rgba(59,130,246,.45);
}
.table-card tr.depth-2 td.lvl{
  background: linear-gradient(90deg, rgba(59,130,246,.08), rgba(59,130,246,.03) 60%, transparent);
  border-left: 2px solid rgba(59,130,246,.35);
}
.table-card tr.depth-3 td.lvl{
  background: linear-gradient(90deg, rgba(59,130,246,.06), rgba(59,130,246,.02) 60%, transparent);
  border-left: 2px solid rgba(59,130,246,.28);
}
.table-card tr.depth-4 td.lvl{
  background: linear-gradient(90deg, rgba(59,130,246,.05), rgba(59,130,246,.015) 60%, transparent);
  border-left: 1px solid rgba(59,130,246,.22);
}
.table-card tr.depth-5 td.lvl{
  background: linear-gradient(90deg, rgba(59,130,246,.045), rgba(59,130,246,.012) 60%, transparent);
  border-left: 1px solid rgba(59,130,246,.18);
}
.table-card tr.depth-6 td.lvl{
  background: linear-gradient(90deg, rgba(59,130,246,.04), rgba(59,130,246,.01) 60%, transparent);
  border-left: 1px solid rgba(59,130,246,.15);
}
.table-card td.lvl .label{ font-weight:700; }
.table-card td.lvl.depth-1 .label{ font-weight:650; opacity:.95; }
.table-card td.lvl.depth-2 .label{ font-weight:600; opacity:.9; font-size:0.94rem; }
.table-card td.lvl.depth-3 .label{ font-weight:600; opacity:.85; font-size:0.92rem; }
.table-card td.lvl.depth-4 .label{ font-weight:600; opacity:.8; font-size:0.9rem; }
.table-card td.lvl.depth-5 .label{ font-weight:600; opacity:.75; font-size:0.88rem; }
.table-card td.lvl.depth-6 .label{ font-weight:600; opacity:.72; font-size:0.86rem; }
.table-card td.lvl .dot{
  width:6px; height:6px; border-radius:999px;
  background:var(--accent); display:inline-block; opacity:.9;
}
.table-card td.lvl.depth-2 .dot{ width:5px; height:5px; opacity:.8; }
.table-card td.lvl.depth-3 .dot{ width:5px; height:5px; opacity:.7; }
.table-card td.lvl.depth-4 .dot{ width:4px; height:4px; opacity:.6; }
.table-card td.lvl.depth-5 .dot{ width:4px; height:4px; opacity:.55; }
.table-card td.lvl.depth-6 .dot{ width:3px; height:3px; opacity:.5; }
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

/* ==== Barres horizontales (si tu les rÃ©actives) ==== */
.mbar-wrap{display:flex; align-items:center; gap:8px;}
.mbar{
  position:relative; height:var(--bar-h); background:#1f2a44; border-radius:999px; overflow:hidden; flex-shrink:0;
}
.mfill{display:block; height:100%; border-radius:999px; transition:width .35s ease;}
/* Dans le drawer, on laisse l'animation piloter la largeur (pas de transition concurrente) */
div[data-testid="stExpanderDetails"] .mfill{ transition:none }

.mfill.blue{background:#3b82f6;} .mfill.green{background:#22c55e;}
.mval{ font-weight:700; color:var(--text); font-size:0.95rem; min-width:52px; text-align:right; }
.hero .mbar{width:var(--bar-w-lg)!important; height:var(--bar-h-lg)!important;}
.section-card .mbar{width:var(--bar-w-md)!important; height:var(--bar-h)!important;}
.table-card .mbar{width:var(--bar-w-sm)!important; height:var(--bar-h)!important;}
.hero .mval{font-size:1.10rem; font-weight:750;} .section-card .mval{font-size:1.02rem; font-weight:700;}
.table-card .mval{font-size:0.95rem; font-weight:650;}
.stButton button{
  border-radius:10px;
}
div[class*="__chartbar"] .stButton button{
  background:rgba(15,23,42,.88)!important;
  border:1px solid rgba(96,165,250,.45)!important;
  color:#e5e7eb!important;
  font-weight:700;
  font-size:0.9rem;
  padding:4px 10px;
  min-height:28px;
}
div[class*="__chartbar"] .stButton button:hover{
  background:rgba(30,41,59,.96)!important;
  border-color:rgba(125,211,252,.9)!important;
}
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


/* ====== Animations ====== */
@keyframes fadeSlideUp { from { opacity:0; transform:translateY(6px) } to { opacity:1; transform:translateY(0) } }
@keyframes pulseDot { 0%,100%{transform:scale(1);opacity:1} 50%{transform:scale(1.35);opacity:.75} }







/* Le sentinel doit exister dans le DOM mais rester invisible */
.n2-block-sentinel{
  visibility: hidden;           /* pas display:none */
  height: 0; padding: 0; margin: 0;
}

/* Nettoyage des marges â€œfantÃ´mesâ€ autour des markdown/cols */
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
.n2-grid .mbar{ width:var(--bar-w-md)!important; height:var(--bar-h)!important; }
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

/* ================= N3: animations (rejouent grÃ¢ce au remount) ================= */
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
.mbar{position:relative;display:block;width:100%;height:var(--bar-h);border-radius:6px;background:rgba(148,163,184,.18);overflow:hidden}
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

/* LÃ©gers dÃ©calages pour un rendu plus fluide */
.n2-grid .mbar-wrap.v{--delay:90ms}
.table-card .mbar-wrap.v{--delay:40ms}

/* Respecte lâ€™accessibilitÃ© */
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












/* ====== keyframes doublÃ©s pour rejouer (A/B) ====== */
@keyframes n3ChartInA { from{opacity:0;transform:translateY(12px) scale(.985)} to{opacity:1;transform:translateY(0) scale(1)} }
@keyframes n3ChartInB { from{opacity:0;transform:translateY(12px) scale(.985)} to{opacity:1;transform:translateY(0) scale(1)} }

@keyframes n3GrowA { from{transform:scaleY(0.001);opacity:0} to{transform:scaleY(1);opacity:1} }
@keyframes n3GrowB { from{transform:scaleY(0.001);opacity:0} to{transform:scaleY(1);opacity:1} }

/* ========== CHART WRAP ANIM (sans expander) ========== */
div[class*="__chartwrap_v0"] [data-testid="stFullScreenFrame"],
div[class*="__chartwrap_v0"] [data-testid="stPlotlyChart"]{
  opacity:0;
  animation: n3ChartInA .6s cubic-bezier(.22,.61,.36,1) .15s forwards;
  will-change: opacity, transform;
}
div[class*="__chartwrap_v1"] [data-testid="stFullScreenFrame"],
div[class*="__chartwrap_v1"] [data-testid="stPlotlyChart"]{
  opacity:0;
  animation: n3ChartInB .6s cubic-bezier(.22,.61,.36,1) .15s forwards;
  will-change: opacity, transform;
}
div[class*="__chartwrap_v0"] .main-svg .barlayer{
  transform-origin: bottom;
  transform-box: view-box;
  transform: scaleY(0.001);
  opacity: 0;
  animation: n3GrowA .7s cubic-bezier(.22,.61,.36,1) .2s forwards;
  will-change: transform, opacity;
}
div[class*="__chartwrap_v1"] .main-svg .barlayer{
  transform-origin: bottom;
  transform-box: view-box;
  transform: scaleY(0.001);
  opacity: 0;
  animation: n3GrowB .7s cubic-bezier(.22,.61,.36,1) .2s forwards;
  will-change: transform, opacity;
}

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

/* AccessibilitÃ© */
@media (prefers-reduced-motion: reduce){
  details[open] [data-testid="stExpanderDetails"]
    .stElementContainer:has(.n3load.v0), 
  details[open] [data-testid="stExpanderDetails"]
    .stElementContainer:has(.n3load.v1){
    /* neutralise toutes les animations ciblÃ©es ci-dessus */
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
  div[class*="__chartwrap_v0"] [data-testid="stFullScreenFrame"],
  div[class*="__chartwrap_v0"] [data-testid="stPlotlyChart"],
  div[class*="__chartwrap_v1"] [data-testid="stFullScreenFrame"],
  div[class*="__chartwrap_v1"] [data-testid="stPlotlyChart"],
  div[class*="__chartwrap_v0"] .main-svg .barlayer,
  div[class*="__chartwrap_v1"] .main-svg .barlayer{
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
  width:100%;                                 /* ðŸ‘ˆ all same width */
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

  /* rÃ©serve de la place Ã  gauche pour le point */
  position: relative;
  padding-left: 36px !important;  /* â¬… now overrides lâ€™ancien padding!important */
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
div[class*="__rowwrap"]{ position: relative; }
div[class*="__rowwrap"] div[class*="__rowbtn"]{
  position: absolute; inset: 0; z-index: 10;
  margin: 0; padding: 0;
}
div[class*="__rowwrap"] div[class*="__rowbtn"] .stButton{ position:absolute; inset:0; }
div[class*="__rowwrap"] div[class*="__rowbtn"] .stButton button{
  width:100%; height:100%; background:transparent; border:0; padding:0; margin:0;
  cursor:pointer; border-radius:12px;
}
div[class*="__rowwrap"] div[class*="__rowbtn"] .stButton button:hover{
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

/* Rejoue lâ€™animation Ã  chaque rendu (compatible avec --to inline) */
.table-card .mfill.anim{ animation:mfillGrowA .8s cubic-bezier(.22,.61,.36,1) forwards; }
.table-card .mfill.anim.av1{ animation-name:mfillGrowB; }
@keyframes mfillGrowA{ 0%{ width:0 } 100%{ width:var(--to) } }
@keyframes mfillGrowB{ 0%{ width:0 } 100%{ width:var(--to) } }

/* Valeur qui fade-in */
.table-card .mbar-wrap.v .mval{ opacity:0; transform:translateY(2px); animation:valIn .45s ease .25s forwards; }
@keyframes valIn{ to{ opacity:1; transform:none } }


















/* === Left sidebar: modern nav + pages === */
section[data-testid="stSidebar"]{
  font-size: 16px;
  background: linear-gradient(180deg, #0c1529 0%, #0a111f 55%, #090f1c 100%);
  border-right: 1px solid rgba(90, 120, 200, 0.18);
}
section[data-testid="stSidebar"] [data-testid="stSidebarContent"],
section[data-testid="stSidebar"] > div{
  background: transparent !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarContent"]{
  display: flex;
  flex-direction: column;
  height: 100%;
}
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"]{
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
}
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] > div{
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
}
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] [data-testid="stVerticalBlock"]{
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  height: 100%;
}
section[data-testid="stSidebar"] .sidebar-spacer{
  flex: 1 1 auto;
  min-height: 24px;
}
section[data-testid="stSidebar"] div[data-testid="stLayoutWrapper"]:has(.st-key-brand_card),
section[data-testid="stSidebar"] div[data-testid="stElementContainer"]:has(.st-key-brand_card),
section[data-testid="stSidebar"] .st-key-brand_card{
  order: 999;
  margin-top: auto !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"]{
  display: none !important;
}
section[data-testid="stSidebar"] .sidebar-nav-title{
  font-size: 12px !important;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  color: rgba(157,168,198,.85);
  margin: 6px 0 10px 0;
}
section[data-testid="stSidebar"] [data-testid="stPageLink"]{
  margin: 6px 0 !important;
}
section[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]{
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px !important;
  border-radius: 12px;
  border: 1px solid rgba(148,163,184,.18);
  background: rgba(15,23,42,.55);
  box-shadow: 0 10px 24px rgba(0,0,0,.25);
  font-size: 20px !important;
  font-weight: 700;
  line-height: 1.1;
  transition: border-color .2s ease, background .2s ease, box-shadow .2s ease;
}
section[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"][aria-current="page"]{
  border-color: rgba(75,111,244,.65);
  background: rgba(75,111,244,.18);
  box-shadow: 0 10px 26px rgba(18, 40, 110, .35);
}
section[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover{
  border-color: rgba(96,165,250,.5);
  background: rgba(30,41,59,.7);
}
section[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] [data-testid="stMarkdownContainer"] p{
  font-size: 20px !important;
  font-weight: 700;
  line-height: 1.1;
  margin: 0 !important;
}
div.st-key-brand_logo_row_scurve > div[data-testid="stHorizontalBlock"],
div.st-key-brand_logo_row_wbs > div[data-testid="stHorizontalBlock"]{
  justify-content: flex-end;
  gap: 12px;
  flex-wrap: nowrap;
}
div[class*="st-key-brand_logo_item_"]{
  position: relative;
  width: 288px;
  height: 288px;
  display: grid;
  grid-template-areas: "stack";
  align-items: center;
  justify-items: center;
}
div[class*="st-key-brand_logo_item_"] > div{
  grid-area: stack;
}
div[class*="st-key-brand_logo_item_"] .stButton{
  align-self: center;
  justify-self: center;
  z-index: 5;
  pointer-events: auto;
  margin: 0 !important;
}
div[class*="st-key-brand_logo_item_"] .brand-pill{
  position: relative;
  z-index: 1;
  pointer-events: none;
}
section[data-testid="stSidebar"] [data-testid="stElementContainer"]:has([data-testid="stPageLink"]){
  margin: 0 !important;
  padding: 0 !important;
}
/* Sidebar auth card */
section[data-testid="stSidebar"] div.st-key-auth_card{
  margin: 6px 0 18px 0;
  padding: 12px 54px 18px 12px;
  border-radius: 14px;
  background: linear-gradient(180deg, rgba(15,23,42,.72), rgba(11,18,36,.65));
  border: 1px solid rgba(148,163,184,.18);
  box-shadow: 0 12px 26px rgba(0,0,0,.28);
  position: relative;
}
section[data-testid="stSidebar"] div.st-key-brand_card{
  margin: 18px 0 0 0;
  padding: 12px;
  border-radius: 14px;
  background: linear-gradient(180deg, rgba(15,23,42,.72), rgba(11,18,36,.65));
  border: 1px solid rgba(148,163,184,.18);
  box-shadow: 0 12px 26px rgba(0,0,0,.28);
  margin-top: auto;
}
section[data-testid="stSidebar"] .brand-title{
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  color: rgba(157,168,198,.85);
  margin-bottom: 10px;
}
section[data-testid="stSidebar"] .brand-label{
  font-size: 12px;
  font-weight: 700;
  color: rgba(157,168,198,.85);
  margin: 2px 0 6px 0;
}
section[data-testid="stSidebar"] div.st-key-auth_card [data-testid="column"]{
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
}
section[data-testid="stSidebar"] .auth-title{
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  color: rgba(157,168,198,.85);
  margin-bottom: 8px;
}
section[data-testid="stSidebar"] .auth-row{
  display: flex;
  align-items: center;
  gap: 10px;
}
section[data-testid="stSidebar"] .auth-avatar{
  width: 38px;
  height: 38px;
  border-radius: 999px;
  object-fit: cover;
  border: 1px solid rgba(148,163,184,.3);
  box-shadow: 0 6px 14px rgba(0,0,0,.25);
}
section[data-testid="stSidebar"] .auth-avatar.placeholder{
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(75,111,244,.18);
  color: var(--text);
  font-weight: 800;
}
section[data-testid="stSidebar"] .auth-meta{
  display: flex;
  flex-direction: column;
  gap: 2px;
}
section[data-testid="stSidebar"] .auth-name{
  font-size: 16px;
  font-weight: 800;
  color: var(--text);
}
section[data-testid="stSidebar"] .auth-email{
  font-size: 12px;
  color: var(--muted);
  word-break: break-word;
}
section[data-testid="stSidebar"] div.st-key-auth_card div.st-key-auth_logout_btn{
  position: absolute;
  top: 10px;
  right: 10px;
  margin: 0 !important;
  padding: 0 !important;
}
section[data-testid="stSidebar"] div.st-key-auth_card div.st-key-auth_logout_btn .stButton{
  display: flex;
  justify-content: flex-end;
}
section[data-testid="stSidebar"] div.st-key-auth_card div.st-key-auth_logout_btn .stButton button{
  width: 40px !important;
  height: 40px !important;
  min-width: 0 !important;
  padding: 0 !important;
  border-radius: 999px !important;
  border: 1px solid rgba(148,163,184,.3) !important;
  background: rgba(15,23,42,.7) !important;
  color: var(--text) !important;
  font-weight: 700 !important;
  font-size: 16px !important;
  line-height: 1 !important;
  box-shadow: inset 0 0 0 1px rgba(255,255,255,.04);
}
section[data-testid="stSidebar"] div.st-key-auth_card div.st-key-auth_logout_btn .stButton button:hover{
  border-color: rgba(96,165,250,.6) !important;
  background: rgba(30,41,59,.9) !important;
}
section[data-testid="stSidebar"] .stRadio [data-testid="stWidgetLabel"] p{
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  color: rgba(157,168,198,.85);
  margin: 12px 0 8px 0;
}
section[data-testid="stSidebar"] .stRadio [role="radiogroup"][aria-label="Pages"]{
  display: flex;
  flex-direction: column;
  gap: 6px;
}
section[data-testid="stSidebar"] .stRadio [role="radiogroup"][aria-label="Pages"] label[data-baseweb="radio"]{
  padding: 8px 12px;
  border-radius: 10px;
  border: 1px solid rgba(148,163,184,.16);
  background: rgba(15,23,42,.45);
  transition: border-color .2s ease, background .2s ease;
}
section[data-testid="stSidebar"] .stRadio [role="radiogroup"][aria-label="Pages"] label[data-baseweb="radio"] > div:first-child{
  display: none;
}
section[data-testid="stSidebar"] .stRadio [role="radiogroup"][aria-label="Pages"] label[data-baseweb="radio"]:has(input:checked){
  border-color: rgba(75,111,244,.55);
  background: rgba(75,111,244,.16);
}
section[data-testid="stSidebar"] .stRadio [role="radiogroup"][aria-label="Pages"] label[data-baseweb="radio"]:hover{
  border-color: rgba(96,165,250,.45);
  background: rgba(30,41,59,.6);
}
section[data-testid="stSidebar"] .stRadio [role="radiogroup"][aria-label="Pages"] [data-testid="stMarkdownContainer"] p{
  font-size: 18px;
  font-weight: 700;
  margin: 0;
}
section[data-testid="stSidebar"] [data-testid="stSelectbox"]{
  background: rgba(15,23,42,.45);
  border: 1px solid rgba(148,163,184,.16);
  border-radius: 12px;
  padding: 8px 10px;
  box-shadow: 0 10px 22px rgba(0,0,0,.25);
}
section[data-testid="stSidebar"] [data-testid="stSelectbox"] [data-testid="stWidgetLabel"] p{
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  color: rgba(157,168,198,.85);
  margin: 0 0 6px 0;
}
section[data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"]{
  background: transparent;
}
section[data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"] [value]{
  font-size: 16px;
  font-weight: 700;
  color: var(--text);
}
/* Disable transitions on radios to avoid flicker when Streamlit rerenders */

/* === Glass frame on main content (wraps hero + N2/N3) === */
.st-key-glass_wrap[data-testid="stVerticalBlock"],
.st-key-glass_wrap[data-testid="stElementContainer"]{
  position:relative;
  z-index:0;
  padding:12px 16px 16px;
  margin:4px 0 8px;
  display:block;
  overflow:hidden;
  transform: translateZ(0);
  backface-visibility: hidden;
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
  transform: translateZ(0);
  backface-visibility: hidden;
}
.st-key-glass_wrap[data-testid="stVerticalBlock"]::after,
.st-key-glass_wrap[data-testid="stElementContainer"]::after{
  background:
    radial-gradient(1200px 420px at 28% 0%, rgba(59,130,246,.18), transparent 55%),
    radial-gradient(900px 380px at 70% 90%, rgba(34,197,94,.14), transparent 60%);
  opacity:.65;
  z-index:0;
  transform: translateZ(0);
  backface-visibility: hidden;
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

/* Force solid background (remove any residual gradients/bands). */
html, body, #root, .stApp, section.main, section[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"], [data-testid="stAppViewBlockContainer"], main{
  background: var(--bg) !important;
  background-image: none !important;
  background-attachment: initial !important;
}
html, body, [data-testid="stAppViewContainer"]{
  zoom: 1 !important;
}
html, body, #root, .stApp, section.stMain, [data-testid="stMainBlockContainer"]{
  min-height: 100vh !important;
}
html::before, html::after,
body::before, body::after,
[data-testid="stAppViewContainer"]::before,
[data-testid="stAppViewContainer"]::after{
  content: none !important;
  display: none !important;
}

/* === Responsive bar widths (follow container width/zoom) === */
.mbar-wrap{ width:100%; }
.mbar{ flex:1 1 auto; min-width:0; width:auto; }
.mval{ flex:0 0 auto; white-space:nowrap; }
.hero .mbar,
.section-card .mbar,
.table-card .mbar,
.n2-grid .mbar{
  width:auto !important;
}

/* === Brand strip (company/client logos) === */
.brand-row{
  display:flex;
  justify-content:flex-end;
  margin: 6px 0 14px 0;
}
.brand-strip{
  display:flex;
  align-items:center;
  gap:8px;
}
.brand-pill{
  height:216px;
  min-width:216px;
  padding:6px 8px;
  border-radius:28px;
  border:1px solid rgba(148,163,184,.18);
  background: rgba(15,23,42,.55);
  box-shadow: 0 12px 26px rgba(0,0,0,.25);
  display:inline-flex;
  align-items:center;
  justify-content:center;
}
.brand-pill img{
  height:100%;
  width:auto;
  object-fit:contain;
}




</style>
"""

def inject_theme():
    st.markdown(CSS, unsafe_allow_html=True)


