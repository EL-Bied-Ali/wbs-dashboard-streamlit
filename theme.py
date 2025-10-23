import streamlit as st

CSS = """
<style>
/* ===== Global layout & base ===== */
:root{
  --bg:#0b1220; --glass:#0f172a; --glass2:#0b1224; --line:#1f2a44;
  --text:#e5e7eb; --muted:#94a3b8; --ok:#22c55e; --bad:#ef4444; --accent:#60a5fa;

  --col1:26%; --col2:10%; --col3:10%; --col4:15%;
  --col5:15%; --col6:8%;  --col7:8%;  --col8:8%;

  --fs-n1-title:2.1rem; --fs-n1-kpi:1.55rem; --fs-n1-label:0.95rem;
  --fs-n2-title:1.55rem; --fs-n2-kpi:1.15rem; --fs-n2-label:0.90rem;
  --fs-n3-head:0.90rem;  --fs-n3-cell:0.96rem; --fs-small:0.82rem;

  --speed-slow:16s; --speed-med:8s; --speed-fast:1.6s;
}

*{font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Arial}
html, body { font-size:17px; line-height:1.4; background:#070d1c; }
header[data-testid="stHeader"]{
  opacity:1; height:auto; min-height:48px; background:transparent; box-shadow:none;
}
.block-container{
  padding-top:1.4rem!important; max-width:2000px!important;
  padding-left:16px!important; padding-right:16px!important;
}

/* === Futuristic dynamic backdrop (scanlines + moving glows + particles) === */
body::before, body::after{
  content:""; position:fixed; inset:0; pointer-events:none; z-index:0;
}
body::before{
  background:
    radial-gradient(1200px 800px at 10% -10%, rgba(59,130,246,.10), transparent 60%),
    radial-gradient(900px 600px at 90% 120%, rgba(16,185,129,.07), transparent 60%),
    radial-gradient(800px 600px at 40% 20%, rgba(99,102,241,.08), transparent 60%);
  animation:bgFloat var(--speed-slow) ease-in-out infinite alternate;
  filter:saturate(1.05);
}
body::after{
  background:
    repeating-linear-gradient(to bottom, rgba(255,255,255,.03) 0 1px, transparent 1px 3px);
  mix-blend-mode:overlay;
  animation:scan var(--speed-med) linear infinite;
  opacity:.25;
}
@keyframes bgFloat { 0%{transform:translateY(0)} 100%{transform:translateY(-12px)} }
@keyframes scan { 0%{background-position-y:0} 100%{background-position-y:120px} }

/* ===== Hero (Level 1) ===== */
.hero{
  position:relative;
  background:
    radial-gradient(1600px 500px at 20% -20%, rgba(59,130,246,.18), transparent 60%),
    linear-gradient(180deg,#0f1b34 0%,#0a1226 100%);
  border:1px solid rgba(96,165,250,.35);
  border-radius:18px; padding:18px 20px; margin:8px 0 16px;
  box-shadow:0 18px 30px rgba(0,0,0,.35), inset 0 0 0 1px rgba(59,130,246,.15);
  animation: fadeSlideUp .45s ease both;
  transition: transform .35s ease, box-shadow .35s ease, border-color .35s ease;
  overflow:hidden;
}
.hero:hover{
  transform: translateY(-2px) perspective(900px) rotateX(.6deg) rotateY(-.6deg);
  box-shadow:0 24px 42px rgba(0,0,0,.45), 0 0 32px rgba(96,165,250,.25) inset;
  border-color:rgba(125,211,252,.65);
}
.hero::before{
  content:""; position:absolute; inset:-1px; border-radius:20px;
  background: conic-gradient(from 0deg,
    rgba(96,165,250,.0), rgba(96,165,250,.35), rgba(59,130,246,.0) 40%,
    rgba(34,197,94,.3), rgba(59,130,246,.0) 70%, rgba(99,102,241,.35), rgba(96,165,250,.0));
  filter: blur(14px);
  opacity:.65; z-index:0; animation:spin 12s linear infinite;
}
.hero::after{
  content:""; position:absolute; inset:0; z-index:0; pointer-events:none;
  background:linear-gradient(120deg, transparent 30%, rgba(255,255,255,.08) 50%, transparent 70%);
  transform:translateX(-100%); animation:sheenSweep 5.5s ease-in-out infinite;
}
@keyframes spin{to{transform:rotate(1turn)}}
@keyframes sheenSweep{0%{transform:translateX(-100%)} 100%{transform:translateX(100%)}}

.hero .title{
  position:relative; z-index:1;
  font-size:var(--fs-n1-title)!important; font-weight:900; letter-spacing:.2px;
  background:linear-gradient(90deg,#93c5fd,#a78bfa,#22d3ee,#93c5fd);
  background-size:300% 100%;
  -webkit-background-clip:text; background-clip:text; color:transparent;
  animation: textFlow 7s ease-in-out infinite;
}
@keyframes textFlow{ 0%{background-position:0%} 50%{background-position:100%} 100%{background-position:0%} }

.hero .badge{
  position:relative; z-index:1;
  margin-left:12px; padding:3px 10px; font-weight:800;
  border:1px solid rgba(96,165,250,.6);
  background:linear-gradient(180deg,rgba(14,165,233,.22),rgba(14,165,233,.10));
  border-radius:999px; color:#cffafe; font-size:.9rem;
  box-shadow:inset 0 0 12px rgba(59,130,246,.25);
  transition:transform .18s ease, box-shadow .18s ease, border-color .18s ease;
}
.hero .badge:hover{ transform:translateY(-1px) scale(1.03); border-color:rgba(125,211,252,.9); box-shadow:0 8px 18px rgba(59,130,246,.25) }

.hero .n1-grid{
  position:relative; z-index:1;
  display:grid; grid-template-columns:var(--col1) var(--col2) var(--col3) var(--col4) var(--col5) var(--col6) var(--col7) var(--col8);
  align-items:center; gap:0; width:100%;
}
.hero .n1g-label{display:flex; align-items:center; gap:8px; flex-wrap:wrap; padding:6px 8px;}
.hero .n1g-label .title{font-size:1.22rem; font-weight:900;}
.hero .n1g-cell{display:flex; flex-direction:column; align-items:flex-start; padding:6px 8px;}
.hero .n1g-cell .small{
  font-size:var(--fs-n1-label); color:#aab4c3; text-transform:uppercase; letter-spacing:.3px; margin-bottom:4px;
}
.hero .n1g-cell b{font-size:var(--fs-n1-kpi); font-weight:800; color:var(--text);}
.hero .n1g-cell b.ok{color:var(--ok)!important;} .hero .n1g-cell b.bad{color:var(--bad)!important;}

/* ===== Section N2 wrapper + header ===== */
.section-card{
  background:linear-gradient(180deg,#0f1a31,#0b1326);
  border:1px solid #223355; border-radius:12px; padding:8px 10px; margin:4px 0 6px;
  box-shadow:0 0 0 1px rgba(36,52,83,.35) inset; animation: fadeSlideUp .45s ease .05s both;
}

.n2-grid{
  position:relative;
  display:grid; grid-template-columns:var(--col1) var(--col2) var(--col3) var(--col4) var(--col5) var(--col6) var(--col7) var(--col8);
  align-items:center; gap:0; padding:6px 8px; row-gap:2px;
  transition:transform .3s ease, box-shadow .3s ease;
}
.n2-grid::after{
  content:""; position:absolute; inset:0; pointer-events:none; border-radius:10px;
  background: radial-gradient(600px 100px at 5% 0%, rgba(59,130,246,.12), transparent 70%);
  opacity:.65; animation:bgSweep var(--speed-slow) ease-in-out infinite alternate;
}
@keyframes bgSweep{ from{transform:translateX(0)} to{transform:translateX(12px)} }
.n2-grid:hover{ transform:translateY(-1px); box-shadow:0 8px 22px rgba(0,0,0,.25) }

.n2g-label,.n2g-cell{padding:6px 8px!important; box-sizing:border-box;}
.n2g-label{display:flex; align-items:center; gap:8px; flex-wrap:wrap;}
.n2g-label .title{
  font-size:var(--fs-n2-title); font-weight:800;
  background:linear-gradient(90deg,#c7d2fe,#67e8f9,#93c5fd); background-size:250% 100%;
  -webkit-background-clip:text; background-clip:text; color:transparent; animation:textFlow 8s ease-in-out infinite;
}
.n2g-label .badge{
  padding:3px 10px; font-size:.88rem; font-weight:800; color:#cffafe;
  background:linear-gradient(180deg,rgba(14,165,233,.18),rgba(14,165,233,.10));
  border:1px solid rgba(96,165,250,.6); border-radius:999px;
  transition: transform .15s ease, box-shadow .15s ease, border-color .15s ease;
}
.n2g-label .badge:hover{ transform: translateY(-1px); box-shadow: 0 6px 14px rgba(59,130,246,.25); border-color: rgba(96,165,250,.9); }
.n2g-cell{display:flex; flex-direction:column; align-items:flex-start; gap:1px!important;}
.n2g-cell .small{
  font-size:var(--fs-n2-label); color:#aab4c3; text-transform:uppercase; letter-spacing:.3px; margin-bottom:4px;
}
.n2g-cell b{font-size:var(--fs-n2-kpi); font-weight:800; color:var(--text);}
.n2g-cell b.ok{color:var(--ok)!important;} .n2g-cell b.bad{color:var(--bad)!important;}
.n2g-cell.gliss b{ text-shadow:0 0 12px rgba(99,102,241,.25); }

/* ===== Table N3 ===== */
.table-card{
  position:relative; overflow:hidden;
  background:linear-gradient(180deg,rgba(15,23,42,.65),rgba(11,18,36,.6));
  border:1px solid #1f2a44; border-radius:14px; padding:12px; margin:8px 0;
  box-shadow:0 6px 16px rgba(0,0,0,.22); animation: fadeSlideUp .45s ease .1s both;
}
.table-card::before{
  content:""; position:absolute; inset:-1px; border-radius:16px; pointer-events:none;
  background:conic-gradient(from 0deg, rgba(96,165,250,.0), rgba(96,165,250,.35), rgba(59,130,246,.0) 40%,
    rgba(34,197,94,.25), rgba(59,130,246,.0) 70%, rgba(99,102,241,.35), rgba(96,165,250,.0));
  filter:blur(10px); opacity:.45; animation:spin var(--speed-med) linear infinite;
}
table.neo{width:100%; border-collapse:separate; border-spacing:0; table-layout:fixed; position:relative; z-index:1;}
table.neo thead th{
  font-size:var(--fs-n3-head)!important; letter-spacing:.3px; text-transform:uppercase;
  color:#aab4c3; font-weight:700; text-align:left; padding:10px 12px; white-space:nowrap;
}
table.neo td{ padding:12px; font-size:var(--fs-n3-cell)!important; color:var(--text); }
table.neo tbody tr{ transition:background .12s ease; }
table.neo tbody tr:hover{
  background:linear-gradient(90deg, rgba(147,197,253,.08), rgba(34,197,94,.05) 50%, transparent);
}
.table-card .neo th:nth-child(1),.table-card .neo td:nth-child(1){width:var(--col1);}
.table-card .neo th:nth-child(2),.table-card .neo td:nth-child(2){width:var(--col2);}
.table-card .neo th:nth-child(3),.table-card .neo td:nth-child(3){width:var(--col3);}
.table-card .neo th:nth-child(4),.table-card .neo td:nth-child(4){width:var(--col4);}
.table-card .neo th:nth-child(5),.table-card .neo td:nth-child(5){width:var(--col5);}
.table-card .neo th:nth-child(6),.table-card .neo td:nth-child(6){width:var(--col6);}
.table-card .neo th:nth-child(7),.table-card .neo td:nth-child(7){width:var(--col7);}
.table-card .neo th:nth-child(8),.table-card .neo td:nth-child(8){width:var(--col8);}

/* Status pills and activity dot */
.ok{color:var(--ok); font-weight:800;} .bad{color:var(--bad); font-weight:800;}
.ok::before{ content:"+"; margin-right:2px; }
.dot{width:8px; height:8px; background:var(--accent); border-radius:999px; display:inline-block; position:relative;
  animation: pulseDot 2.2s ease-in-out infinite;
}
.dot::after{
  content:""; position:absolute; inset:-8px; border-radius:999px; border:2px solid rgba(96,165,250,.25);
  animation:ripple 2.2s ease-out infinite;
}
@keyframes pulseDot { 0%,100%{transform:scale(1);opacity:1} 50%{transform:scale(1.35);opacity:.75} }
@keyframes ripple { 0%{transform:scale(.5); opacity:.5} 100%{transform:scale(1.6); opacity:0} }

/* ===== Bars with animated fill + spark ===== */
.mbar-wrap{display:flex; align-items:center; gap:8px;}
.mbar{
  position:relative; height:12px; background:#1f2a44; border-radius:999px; overflow:hidden; flex-shrink:0;
}
.mfill{display:block; height:100%; border-radius:999px; transition:width .35s ease; position:relative;}
.mfill.blue{background:#3b82f6;} .mfill.green{background:#22c55e;}
.mval{ font-weight:800; color:var(--text); font-size:0.98rem; min-width:56px; text-align:right; }

.hero .mbar{width:150px!important;} .section-card .mbar{width:130px!important;} .table-card .mbar{width:110px!important;}
.hero .mval{font-size:1.08rem;} .section-card .mval{font-size:1.02rem;} .table-card .mval{font-size:.96rem;}

@keyframes growBar { from { width:0 } to { width:var(--to, 0%) } }
.mfill.anim{ animation: growBar .9s ease-out both; }

/* moving sheen inside bar */
@keyframes sheen { 0%{transform:translateX(-100%);opacity:0} 15%{opacity:.22} 85%{opacity:.22} 100%{transform:translateX(100%);opacity:0} }
.mbar::after{
  content:""; position:absolute; top:0; bottom:0; width:40%;
  background:linear-gradient(90deg, transparent, rgba(255,255,255,.12), transparent);
  animation: sheen 2.6s ease-in-out infinite; pointer-events:none;
}

/* spark traveling to the current % */
.mfill.anim::before{
  content:""; position:absolute; top:50%; width:12px; height:12px; transform:translate(-50%,-50%);
  border-radius:50%; box-shadow:0 0 12px rgba(255,255,255,.9), 0 0 24px rgba(96,165,250,.65);
  background:radial-gradient(circle at 50% 50%, #fff, rgba(255,255,255,.0) 60%);
  animation: spark var(--speed-fast) ease-in-out infinite;
}
@keyframes spark {
  0% { left: 0% }
  50%{ left: calc(var(--to, 0%) - 6px) }
  100%{ left: 0% }
}

/* ===== Sidebar toggle button ===== */
button[data-testid="stSidebarCollapseButton"]{
  position: fixed; top:12px; left:12px; z-index:600; width:38px; height:38px; border-radius:10px;
  opacity:1!important; pointer-events:auto!important;
  background:rgba(15,23,42,.92)!important; border:1px solid rgba(96,165,250,.55)!important;
  box-shadow:0 6px 18px rgba(0,0,0,.35); transition:transform .16s ease, box-shadow .16s ease, border-color .16s ease;
}
button[data-testid="stSidebarCollapseButton"]:hover{
  transform:translateY(-1px) scale(1.03);
  background:rgba(30,41,59,.96)!important; border-color:rgba(125,211,252,.9)!important; box-shadow:0 8px 22px rgba(0,0,0,.45);
}
button[data-testid="stSidebarCollapseButton"]:focus{ outline:2px solid rgba(125,211,252,.9); outline-offset:2px; }
button[data-testid="stSidebarCollapseButton"] svg,
button[data-testid="stSidebarCollapseButton"] svg *{ fill:#e5f0ff!important; stroke:#e5f0ff!important; }
@media (max-width:900px){ .block-container{ padding-top:2.2rem!important; } }

/* ====== Animations used elsewhere ====== */
@keyframes fadeSlideUp { from { opacity:0; transform:translateY(6px) } to { opacity:1; transform:translateY(0) } }

/* ===== N2 full-wrapper styling via sentinel ===== */
div[data-testid="stVerticalBlock"]:has(.n2-block-sentinel){
  background: linear-gradient(180deg, #0f1a31, #0b1326);
  border: 1px solid #223355; border-radius: 12px;
  padding: 10px 12px; margin: 8px 0 14px;
  box-shadow: 0 0 0 1px rgba(36,52,83,.35) inset, 0 12px 24px rgba(0,0,0,.25);
  overflow: hidden; box-sizing: border-box; position:relative;
}
div[data-testid="stVerticalBlock"]:has(.n2-block-sentinel)::after{
  content:""; position:absolute; inset:0; pointer-events:none;
  background:radial-gradient(800px 120px at 100% -40%, rgba(99,102,241,.18), transparent 70%);
  animation:bgFloat var(--speed-med) ease-in-out infinite alternate; opacity:.55;
}
.n2-block-sentinel{ visibility: hidden; height: 0; padding: 0; margin: 0; }
div[data-testid="stVerticalBlock"]:has(.n2-block-sentinel) [data-testid="stMarkdownContainer"] > p{ margin:0 !important; }
div[data-testid="stVerticalBlock"]:has(.n2-block-sentinel) .stColumns,
div[data-testid="stVerticalBlock"]:has(.n2-block-sentinel) [data-testid="column"]{ overflow:visible; }

/* Flatten inner .section-card rendered by header HTML */
div[data-testid="stVerticalBlock"]:has(.n2-block-sentinel) .section-card{
  background:transparent !important; border:0 !important; box-shadow:none !important;
  padding:0 !important; margin:0 !important;
}
div[data-testid="stVerticalBlock"]:has(.n2-block-sentinel) .n2-grid{ padding:6px 8px !important; }

/* Chevron button column on the right - micro interactions */
div[data-testid="stVerticalBlock"]:has(.n2-block-sentinel) .stButton{
  display:flex; align-items:center; justify-content:flex-end; margin-top:4px;
}
div[data-testid="stVerticalBlock"]:has(.n2-block-sentinel) .stButton button{
  border-radius:8px; background:rgba(15,23,42,.88);
  border:1px solid rgba(96,165,250,.45); color:#e5e7eb; font-weight:900; font-size:16px;
  min-height:28px; padding:0 .35rem; transition:transform .12s ease, border-color .12s ease, box-shadow .12s ease;
  box-shadow:0 0 0 rgba(0,0,0,0);
}
div[data-testid="stVerticalBlock"]:has(.n2-block-sentinel) .stButton button:hover{
  transform:translateY(-1px) scale(1.04); border-color:rgba(125,211,252,.9);
  box-shadow:0 6px 16px rgba(59,130,246,.25);
}
div[data-testid="stVerticalBlock"]:has(.n2-block-sentinel) .stButton button:active{ transform:scale(.96) }

/* ===== Accessibility - respect reduced motion ===== */
@media (prefers-reduced-motion: reduce){
  *{animation:none!important; transition:none!important}
  .mbar::after,.mfill.anim::before{display:none!important}
}
</style>
"""

def inject_theme():
    st.markdown(CSS, unsafe_allow_html=True)
