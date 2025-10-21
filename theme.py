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
    radial-gradient(1200px 400px at 20% -10%, rgba(59,130,246,.15), transparent 60%),
    linear-gradient(180deg, #111c34, #0b1224);
  border:1px solid #223355;
  border-radius:18px;
  padding:16px 18px;
  margin:4px 0 12px 0;
  box-shadow:0 10px 24px rgba(0,0,0,.25);
}
.hero .title{font-size:1.2rem;font-weight:800;color:var(--text);letter-spacing:.3px}

/* ============ Header / KPIs communs ============ */
.row{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap}
.left{display:flex;align-items:center;gap:10px}
.title{color:var(--text);font-weight:700;font-size:1.05rem}
.title-lg{font-size:1.15rem}
.badge{
  font-size:.78rem;color:#cffafe;background:rgba(14,165,233,.15);
  border:1px solid rgba(14,165,233,.35);
  padding:2px 8px;border-radius:999px;margin-left:10px
}
.dot{width:8px;height:8px;background:var(--accent);border-radius:999px;display:inline-block}
.kpis{display:flex;gap:22px;flex-wrap:wrap}
.kpi{color:var(--muted);font-size:.92rem}
.kpi b{color:var(--text)}
.kpi .ok{color:var(--ok);font-weight:700}
.kpi .bad{color:var(--bad);font-weight:700}
.small{font-size:.86rem;color:var(--muted)}
.sep{height:1px;background:var(--line);margin:10px 0 6px 0;border-radius:1px}

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
}
table.neo th + th{ border-left:none }

/* Corps */
table.neo td{
  padding:12px 12px; font-size:.95rem; color:var(--text); white-space:nowrap;
  border-bottom:1px solid rgba(31,42,68,.8);
  border-left:none;
}
table.neo tbody tr:first-child td{ border-bottom:2px solid #2a3b62 }
table.neo tbody tr{ transition: background .12s ease; }
table.neo tbody tr:hover{ background: rgba(148,163,184,.06); }

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
.col-sign .ok{ color:var(--ok); font-weight:700 }
.col-sign .bad{ color:var(--bad); font-weight:700 }
.col-gliss .ok{ color:var(--ok); font-weight:700 }
.col-gliss .bad{ color:var(--bad); font-weight:700 }
</style>
"""

# RESET table borders (sécurité visuelle)
CSS += """
<style>
table.neo, table.neo * { border: none !important; box-shadow: none !important; }
</style>
"""

# Large layout anti-scroll + sizing des colonnes
CSS += """
<style>
/* === LARGE LAYOUT – ANTI-SCROLL === */
[data-testid="stAppViewContainer"] .main .block-container {
  max-width: 2100px;
  padding-left: 12px;
  padding-right: 12px;
}
[data-testid="stSidebar"] > div { width: 320px; }

.table-card .neo{ table-layout:auto; }
.table-card .neo th, .table-card .neo td{ padding:10px 12px; white-space:nowrap; }
.table-card .neo .lvl{ min-width:280px; }
.table-card .neo .col-date{ min-width:130px; }
.table-card .neo .col-bar{ min-width:220px; }
.table-card .neo .col-sign, .table-card .neo .col-gliss{ min-width:110px; }
.table-card .table-wrap{ overflow-x:visible; }
</style>
"""

# Header N2 aligné + correctifs
CSS += """
<style>
/* ===== Header N2 aligné aux colonnes ===== */
.n2-grid{
  display:grid;
  grid-template-columns: 280px 130px 130px 220px 220px 110px 110px 85px; /* colonne glissement -15px */
  align-items:center;
  gap:12px;
  padding:8px 6px 2px 6px;
}
.n2g-label{display:flex; align-items:center; gap:10px}
.n2g-cell{display:flex; flex-direction:column; gap:2px}
.n2g-cell .small{opacity:.8}
.n2g-cell b{color:var(--text)}
.n2-grid .small{font-size:.78rem; color:#aab4c3; text-transform:uppercase; letter-spacing:.3px}

/* Badge collé au titre même en 2 lignes */
.n2g-label{ flex-wrap:wrap; align-items:baseline; gap:6px; }
.n2g-label .badge{ margin-left:0; vertical-align:baseline; }

/* Responsive fallback */
@media (max-width: 1200px){
  .n2-grid{ grid-template-columns: 1fr; row-gap:8px; }
  .n2g-row{ display:flex; flex-wrap:wrap; gap:14px }
  .n2g-cell{ flex:0 0 auto; min-width:160px }
}

.n2g-cell:last-child {
  margin-left: -12px;   /* rapproche Glissement de 12px */
}
</style>
"""

# Étiquette de section (optionnelle, si utilisée ailleurs)
CSS += """
<style>
.n2-tag{
  display:inline-flex; align-items:center; gap:8px;
  background:linear-gradient(135deg,#1e3a8a,#0f172a);
  border:1px solid rgba(96,165,250,.35);
  color:#e0f2fe; padding:6px 14px; border-radius:999px;
  font-weight:700; font-size:0.92rem; letter-spacing:.3px;
  margin:10px 0 8px 2px; box-shadow:0 0 8px rgba(59,130,246,.25);
}
.n2-tag:hover{
  background:linear-gradient(135deg,#2563eb,#1e3a8a);
  box-shadow:0 0 10px rgba(96,165,250,.4); transition:all .25s ease;
}
.n2-icon{ font-size:1.05rem; filter:drop-shadow(0 0 3px rgba(59,130,246,.3)); }
</style>
"""

CSS += """
<style>
/* --- Streamlit Cloud: fixes anti-débordement --- */

/* 1) Le scroll horizontal reste DANS la carte, pas dehors */
.table-card{ overflow:hidden; }
.table-card .table-wrap{ overflow-x:auto !important; }

/* 2) Empêche les cellules en nowrap de pousser hors du conteneur */
.table-card .neo th,
.table-card .neo td{
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 1px;  /* active ellipsis en layout auto */
}

/* 3) Légère réduction des largeurs mini en environnements plus étroits */
@media (max-width: 1750px){
  .table-card .neo .lvl{ min-width:240px; }
  .table-card .neo .col-bar{ min-width:190px; }
  .mbar{ width:140px; }
}
</style>
"""

CSS += """
<style>
/* === Streamlit Cloud: full-width no-scroll === */

/* Étire vraiment la page comme en local */
[data-testid="stAppViewContainer"] .main .block-container{
  max-width: 2300px !important;
}

/* Le tableau s’adapte (pas de scroll) */
.table-card{ overflow: hidden; }
.table-card .table-wrap{ overflow-x: visible !important; }

/* Autoriser le retour à la ligne (on retire le nowrap) */
.table-card .neo th,
.table-card .neo td{
  white-space: normal !important;
  word-break: break-word;
  overflow: visible;
  text-overflow: clip;
}

/* Réduire un peu les largeurs mini pour tenir sur Cloud */
.table-card .neo .lvl{ min-width: 240px; }
.table-card .neo .col-date{ min-width: 110px; }
.table-card .neo .col-bar{ min-width: 180px; }
.mbar{ width: 120px; }

/* Header N2 aligné avec les nouvelles largeurs */
.n2-grid{
  grid-template-columns: 240px 110px 110px 180px 180px 95px 95px 80px !important;
}
/* petit décalage glissement */
.n2-grid > .n2g-cell:last-child{ margin-left: -10px; }
</style>
"""


def inject_theme():
  st.markdown(CSS, unsafe_allow_html=True)
