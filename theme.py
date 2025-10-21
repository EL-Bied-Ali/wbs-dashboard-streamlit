import streamlit as st

CSS = """
<style>
/* ============ Layout ============ */
header[data-testid="stHeader"]{opacity:0;height:0}
.block-container{padding-top:1.4rem !important;max-width:1180px}
*{font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Arial}

/* ============ Design tokens ============ */
:root{
  --bg:#0b1220;
  --glass:#0f172a;
  --glass2:#0b1224;
  --line:#1f2a44;
  --text:#e5e7eb;
  --muted:#94a3b8;
  --ok:#22c55e;
  --bad:#ef4444;
  --accent:#60a5fa;
}

/* ============ Hero (Niveau 1) ============ */
.hero{
  background:
    radial-gradient(1600px 500px at 20% -20%, rgba(59,130,246,.18), transparent 60%),
    linear-gradient(180deg, #0f1b34 0%, #0a1226 100%);
  border: 1px solid rgba(96,165,250,.35);
  border-radius: 18px;
  padding: 18px 20px;
  margin: 8px 0 16px 0;
  box-shadow:
    0 18px 30px rgba(0,0,0,.35),
    inset 0 0 0 1px rgba(59,130,246,.15);
}
.hero .title{
  font-size: 1.35rem;
  font-weight: 800;
  letter-spacing: .2px;
  text-shadow: 0 0 18px rgba(59,130,246,.25);
  color: var(--text);
}
.hero .kpis{gap:28px;display:flex;flex-wrap:wrap}
.hero .kpi{font-size:.95rem;color:#cbd5e1}
.hero .kpi .label{
  display:block;font-size:.75rem;text-transform:uppercase;
  letter-spacing:.4px;color:#93a3b8
}
.hero .kpi b{color:#e5e7eb}
.hero .ok{color:#22c55e;font-weight:800}
.hero .bad{color:#ef4444;font-weight:800}
.hero .badge{
  margin-left:12px;padding:3px 10px;font-weight:700;
  border-color:rgba(96,165,250,.5);
  background:linear-gradient(180deg,rgba(14,165,233,.18),rgba(14,165,233,.10));
  color:#cffafe;border:1px solid rgba(14,165,233,.35);
  border-radius:999px;font-size:.78rem
}
.sep{
  height:1px;
  background:linear-gradient(90deg,rgba(96,165,250,.35),rgba(96,165,250,.08));
  margin:12px 0 8px;
  border-radius:1px;
}

/* ============ Carte N2 ============ */
.section-card{
  background:linear-gradient(180deg,#0f1a31,#0b1326);
  border:1px solid #223355;
  border-radius:12px;
  padding:12px 14px;
  margin:6px 0 10px 0;
  box-shadow:0 0 0 1px rgba(36,52,83,.35) inset;
}
.section-card .kpis{gap:18px}

/* ============ Containers natifs stylés ============ */
div[data-testid="stVerticalBlockBorderWrapper"]{
  background:linear-gradient(180deg,#0d1730,#0a1124);
  border-color:#2a3b62 !important;
  border-radius:16px !important;
  padding:12px 14px !important;
  box-shadow:
    0 0 0 1px rgba(42,59,98,.35) inset,
    0 18px 28px rgba(0,0,0,.28);
}
div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stVerticalBlockBorderWrapper"]{
  background:rgba(15,23,42,.55);
  border-color:#223355 !important;
  box-shadow:0 0 0 1px rgba(34,51,85,.25) inset;
  margin-top:12px;
  padding:10px 12px !important;
}

/* ============ Table “neo” moderne ============ */
.table-card{
  background: linear-gradient(180deg, rgba(15,23,42,.65), rgba(11,18,36,.6));
  border: 1px solid #1f2a44; border-radius:14px;
  padding:12px; margin:8px 0;
  box-shadow: 0 6px 16px rgba(0,0,0,.22);
}
.table-wrap{ width:100%; overflow-x:auto }
table.neo{ width:100%; border-collapse:separate; border-spacing:0; }

/* En-tête */
table.neo thead th{
  font-size:.85rem; letter-spacing:.3px; text-transform:uppercase;
  color:#aab4c3; font-weight:700; text-align:left;
  padding:10px 12px; border-bottom:1px solid var(--line);
  white-space:nowrap;
}
table.neo th + th{ border-left:none }

/* Corps */
table.neo td{
  padding:12px 12px; font-size:.95rem; color:var(--text); white-space:nowrap;
  border-bottom:1px solid rgba(31,42,68,.8);
  border-left:none;
}
table.neo tbody tr:first-child td{ border-bottom:2px solid #2a3b62 }
table.neo tbody tr:hover{ background: rgba(148,163,184,.06); transition: background .12s ease }

/* Coins doux */
table.neo tbody tr:first-child td:first-child { border-top-left-radius:10px }
table.neo tbody tr:first-child td:last-child  { border-top-right-radius:10px }
table.neo tbody tr:last-child  td:first-child { border-bottom-left-radius:10px }
table.neo tbody tr:last-child  td:last-child  { border-bottom-right-radius:10px }

/* Détails */
.col-date{ color:#cbd5e1 }
.mbar{
  position:relative; height:8px; width:160px;
  background:var(--line); border-radius:999px; overflow:hidden;
  display:inline-block; vertical-align:middle;
}
.mfill{height:100%; border-radius:999px; transition:width .35s ease}
.mfill.blue{ background:#3b82f6 } .mfill.green{ background:#22c55e }
.mval{ display:inline-block; min-width:56px; margin-left:8px }

.ok{ color:var(--ok); font-weight:700 }
.bad{ color:var(--bad); font-weight:700 }

/* === Large layout anti-scroll === */
[data-testid="stAppViewContainer"] .main .block-container {
  max-width: 2100px;
  padding-left: 12px;
  padding-right: 12px;
}
[data-testid="stSidebar"] > div { width: 320px; }

/* === Largeurs relatives des colonnes === */
:root{
  --col1: 25%;
  --col2: 10%;
  --col3: 10%;
  --col4: 15%;
  --col5: 15%;
  --col6: 8%;
  --col7: 8%;
  --col8: 9%;
}

/* === N2 Header grid (alignement parfait) === */
.n2-grid{
  display:grid;
  grid-template-columns:
    var(--col1) var(--col2) var(--col3) var(--col4)
    var(--col5) var(--col6) var(--col7) var(--col8);
  align-items:center;
  gap:0;
}
.n2g-label,.n2g-cell{
  padding:10px 12px !important;
  box-sizing:border-box;
}
.n2g-label{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.n2-grid>.n2g-cell:last-child{margin-right:-1px}

/* === Fix texte vertical === */
.table-card .neo th,
.table-card .neo td,
.table-card .neo td:first-child,
.table-card .neo th:first-child {
  writing-mode: horizontal-tb !important;
  text-orientation: mixed !important;
  transform: none !important;
  white-space: nowrap !important;
  word-break: keep-all !important;
  overflow: visible !important;
}
</style>
"""

def inject_theme():
    st.markdown(CSS, unsafe_allow_html=True)
