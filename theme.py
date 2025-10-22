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
.ok::before{ content:"+"; margin-right:2px; }

/* ==== Barres horizontales (si tu les réactives) ==== */
.mbar-wrap{display:flex; align-items:center; gap:8px;}
.mbar{
  position:relative; height:10px; background:#1f2a44; border-radius:999px; overflow:hidden; flex-shrink:0;
}
.mfill{display:block; height:100%; border-radius:999px; transition:width .35s ease;}
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

/* ====== Chevron interne (submit Streamlit en haut-droite) ====== */
form[data-testid="stForm"]{ position:relative; margin:0; padding:0; }
form[data-testid="stForm"] .n2-card{ position:relative; padding-right:46px; }
form[data-testid="stForm"] button[kind="formSubmit"]{
  position:absolute !important; top:10px; right:12px;
  width:34px; height:28px; border-radius:8px;
  background:rgba(15,23,42,.88) !important;
  border:1px solid rgba(96,165,250,.45) !important;
  color:#e5e7eb !important; font-weight:800; font-size:16px;
  padding:0 !important; min-height:auto !important; z-index:3;
  box-shadow:0 6px 14px rgba(0,0,0,.30);
}
form[data-testid="stForm"] button[kind="formSubmit"]:hover{
  background:rgba(30,41,59,.96) !important; border-color:rgba(125,211,252,.9) !important;
}


/* --- Repositionne le submit (chevron) EN HAUT-DROITE de la carte N2 --- */
form[data-testid="stForm"]{ position: relative; }
form[data-testid="stForm"] .n2-card{ position: relative; padding-right: 46px; }

/* Le WRAPPER du bouton devient absolu dans la carte */
form[data-testid="stForm"] div[data-testid="stFormSubmitButton"]{
  position: absolute !important;
  top: 10px;              /* ajuste si besoin (ex: 6px ou 12px) */
  right: 12px;            /* marge droite de la carte */
  z-index: 5;
  width: 34px;            /* largeur du chevron */
  height: 28px;           /* hauteur du chevron */
  margin: 0 !important;   /* pas d’offset vertical */
  padding: 0 !important;
}

/* Le conteneur interne garde la même taille */
form[data-testid="stForm"] div[data-testid="stFormSubmitButton"] > div{
  width: 100% !important;
  height: 100% !important;
}

/* Scope: ne cible que le container qui contient la grille N2 native */
.n2-native-card{
  background:linear-gradient(180deg,#0f1a31,#0b1326);
  border:1px solid #223355; border-radius:12px;
  padding:8px 10px; margin:4px 0 6px;
  box-shadow:0 0 0 1px rgba(36,52,83,.35) inset;
}

/* Le bouton chevron dans la dernière colonne */
.n2-native-card button{
  border-radius:8px;
  background:rgba(15,23,42,.88);
  border:1px solid rgba(96,165,250,.45);
  color:#e5e7eb; font-weight:800; font-size:16px; min-height:28px;
}
.n2-native-card button:hover{
  background:rgba(30,41,59,.96);
  border-color:rgba(125,211,252,.9);
}












</style>
"""

def inject_theme():
    st.markdown(CSS, unsafe_allow_html=True)
