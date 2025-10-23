import streamlit as st

CSS = """
<style>
:root{
  --bg:#0c111a; --panel:#0f1522; --panel2:#0c111a; --line:#1c2940;
  --text:#e8ecef; --muted:#9ba7b4; --ok:#2fb573; --bad:#dc5d5d;
  --accent:#c9a66b; --accent-weak:#c9a66b22;
  --col1:26%; --col2:10%; --col3:10%; --col4:15%;
  --col5:15%; --col6:8%;  --col7:8%;  --col8:8%;
  --fs-n1-title:2.0rem; --fs-n1-kpi:1.45rem; --fs-n1-label:.95rem;
  --fs-n2-title:1.45rem; --fs-n2-kpi:1.08rem; --fs-n2-label:.90rem;
  --fs-n3-head:.88rem;   --fs-n3-cell:.96rem;
  --ease:cubic-bezier(.22,.61,.36,1);
}
*{font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Arial}
html,body{background:#0a0f17;}
.block-container{max-width:2000px!important; padding:1.25rem 16px 2rem!important;}
header[data-testid="stHeader"]{background:transparent; box-shadow:none}

/* ===== N1 (Hero) ===== */
.hero{
  position:relative; overflow:hidden;
  background:
    linear-gradient(180deg, rgba(201,166,107,.06), rgba(201,166,107,0) 40%),
    linear-gradient(180deg, #101726, #0c121f);
  border:1px solid rgba(201,166,107,.38);
  border-radius:16px; padding:18px 20px; margin:10px 0 18px;
  box-shadow:0 12px 28px rgba(0,0,0,.30), inset 0 0 0 1px rgba(255,255,255,.02);
  transition:box-shadow .25s var(--ease), transform .25s var(--ease), border-color .25s var(--ease);
  animation:fadeUp .28s var(--ease) both;
}
.hero:hover{ transform:translateY(-2px); border-color:rgba(201,166,107,.55);
  box-shadow:0 18px 36px rgba(0,0,0,.38), 0 0 0 1px rgba(201,166,107,.08) inset }
.hero .title{ font-size:var(--fs-n1-title)!important; font-weight:800; letter-spacing:.2px; color:var(--text) }
.hero .badge{ margin-left:10px; padding:3px 10px; border-radius:999px; font-weight:700; font-size:.9rem; color:#1b2433;
  background:linear-gradient(180deg,#d8c39a,#c9a66b); border:1px solid #c8ad74; box-shadow:inset 0 -1px 0 rgba(0,0,0,.15) }
.hero .n1-grid{ margin-top:.35rem; display:grid; gap:0; width:100%;
  grid-template-columns:var(--col1) var(--col2) var(--col3) var(--col4) var(--col5) var(--col6) var(--col7) var(--col8); align-items:center }
.hero .n1g-label{display:flex; align-items:center; gap:10px; padding:6px 8px}
.hero .n1g-cell{padding:6px 8px; display:flex; flex-direction:column; align-items:flex-start}
.hero .n1g-cell .small{font-size:var(--fs-n1-label); color:var(--muted); text-transform:uppercase; letter-spacing:.28px; margin-bottom:3px}
.hero .n1g-cell b{font-size:var(--fs-n1-kpi); font-weight:800; color:var(--text)}
.hero .n1g-cell b.ok{color:var(--ok)} .hero .n1g-cell b.bad{color:var(--bad)}

/* ===== N2 wrapper ===== */
div[data-testid="stVerticalBlock"]:has(.n2-block-sentinel){
  background:linear-gradient(180deg,#0f1626,#0d1422);
  border:1px solid #1f2a40; border-radius:12px;
  padding:10px 12px; margin:8px 0 14px;
  box-shadow:0 0 0 1px rgba(255,255,255,.02) inset, 0 10px 22px rgba(0,0,0,.22)
}
.n2-block-sentinel{visibility:hidden; height:0; padding:0; margin:0}
div[data-testid="stVerticalBlock"]:has(.n2-block-sentinel) [data-testid="stMarkdownContainer"] > p{margin:0!important}
.section-card{background:transparent; border:0; padding:0; margin:0; box-shadow:none}
.n2-grid{display:grid; align-items:center;
  grid-template-columns:var(--col1) var(--col2) var(--col3) var(--col4) var(--col5) var(--col6) var(--col7) var(--col8);
  padding:6px 8px; border-radius:10px; transition:background .2s var(--ease)}
.n2-grid:hover{background:linear-gradient(90deg, var(--accent-weak), transparent 70%)}
.n2g-label{display:flex; align-items:center; gap:10px; padding:6px 8px}
.n2g-label .title{font-size:var(--fs-n2-title); font-weight:800; color:var(--text)}
.n2g-label .badge{ padding:2px 10px; font-size:.86rem; font-weight:700; color:#1b2433;
  background:linear-gradient(180deg,#e9dbbd,#c9a66b); border:1px solid #ccb27b; border-radius:999px }
.n2g-cell{display:flex; flex-direction:column; align-items:flex-start; padding:6px 8px}
.n2g-cell .small{font-size:var(--fs-n2-label); color:var(--muted); text-transform:uppercase; letter-spacing:.28px; margin-bottom:2px}
.n2g-cell b{font-size:var(--fs-n2-kpi); font-weight:800; color:var(--text)}
.n2g-cell b.ok{color:var(--ok)} .n2g-cell b.bad{color:var(--bad)}

/* ===== Table N3 ===== */
.table-card{ position:relative; overflow:hidden;
  background:linear-gradient(180deg,#0f1522,#0c121e);
  border:1px solid #1f2a40; border-radius:12px;
  padding:10px 10px 12px; margin:8px 0;
  box-shadow:0 8px 18px rgba(0,0,0,.20), inset 0 0 0 1px rgba(255,255,255,.02);
  animation:fadeUp .28s var(--ease) both
}
table.neo{width:100%; border-collapse:separate; border-spacing:0; table-layout:fixed}
table.neo thead th{
  font-size:var(--fs-n3-head)!important; text-transform:uppercase; letter-spacing:.26px;
  color:var(--muted); font-weight:700; text-align:left; padding:10px 12px; white-space:nowrap; border-bottom:1px solid #1f2a40}
table.neo td{padding:11px 12px; font-size:var(--fs-n3-cell)!important; color:var(--text); border-bottom:1px dashed rgba(255,255,255,.04)}
table.neo tbody tr:last-child td{border-bottom:none}
table.neo tbody tr:hover{background:linear-gradient(90deg, rgba(201,166,107,.08), transparent 70%)}

/* ===== Barres ===== */
.mbar-wrap{display:flex; align-items:center; gap:8px}
.mbar{position:relative; height:12px; border-radius:999px; overflow:hidden; flex-shrink:0;
  background:linear-gradient(180deg,#162237,#121c2e); border:1px solid #1e2a41}
.mfill{display:block; height:100%; border-radius:999px; transition:width .45s var(--ease)}
.mfill.blue{background:linear-gradient(180deg,#5ba2ff,#3b82f6)}
.mfill.green{background:linear-gradient(180deg,#41c78d,#2fb573)}
.mval{font-weight:800; color:var(--text); font-size:.96rem; min-width:56px; text-align:right}
.hero .mbar{width:150px!important} .section-card .mbar{width:130px!important} .table-card .mbar{width:110px!important}

/* ===== Toggle sidebar ===== */
button[data-testid="stSidebarCollapseButton"]{
  position:fixed; top:12px; left:12px; z-index:600; width:38px; height:38px; border-radius:10px;
  background:rgba(16,23,38,.92)!important; border:1px solid rgba(201,166,107,.45)!important;
  box-shadow:0 8px 18px rgba(0,0,0,.35);
  transition:transform .18s var(--ease), box-shadow .18s var(--ease), border-color .18s var(--ease)
}
button[data-testid="stSidebarCollapseButton"]:hover{ transform:translateY(-1px);
  border-color:rgba(201,166,107,.8)!important; box-shadow:0 12px 26px rgba(0,0,0,.45) }
button[data-testid="stSidebarCollapseButton"] svg,button[data-testid="stSidebarCollapseButton"] svg *{fill:#eae6de!important; stroke:#eae6de!important}

/* ===== N3 collapsible (dépliage animé) ===== */
.n3-header{
  display:flex; align-items:center; justify-content:space-between; gap:12px;
  padding:10px 12px; background:linear-gradient(180deg,#0f1522,#0c121e);
  border:1px solid #1f2a40; border-radius:10px; cursor:pointer;
  transition:background .2s var(--ease), border-color .2s var(--ease)
}
.n3-header:hover{ background:linear-gradient(90deg, var(--accent-weak), transparent 70%); border-color:#263650 }
.n3-title{ font-weight:800; color:var(--text) }
.n3-toggle{
  display:inline-flex; align-items:center; gap:8px; padding:6px 10px; border-radius:999px;
  background:#111a2b; border:1px solid #2a3854; color:#e8ecef; font-weight:700; font-size:.92rem
}
.n3-toggle .chev{ display:inline-block; transition:transform .25s var(--ease) }
.n3-toggle[aria-pressed="true"] .chev{ transform:rotate(90deg) }

/* conteneur animé */
.n3-panel{
  overflow:hidden; max-height:0; opacity:0; transform:translateY(-6px);
  transition:max-height .45s var(--ease), opacity .32s var(--ease), transform .32s var(--ease)
}
.n3-panel.open{ max-height:1800px; opacity:1; transform:translateY(0) } /* 1800px = large pour tables */

/* Micro fade-in des blocs internes */
.n3-panel.open .table-card, .n3-panel.open .section-card{ animation:fadeUp .28s var(--ease) both }

/* Accessibilité */
.ok{color:var(--ok); font-weight:800} .bad{color:var(--bad); font-weight:800}
@keyframes fadeUp{from{opacity:0; transform:translateY(6px)} to{opacity:1; transform:translateY(0)}}
@media (prefers-reduced-motion:reduce){ *{animation:none!important; transition:none!important} }
</style>
"""

def inject_theme():
    st.markdown(CSS, unsafe_allow_html=True)
