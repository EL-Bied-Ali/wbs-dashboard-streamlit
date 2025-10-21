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
  --col1:25%; --col2:10%; --col3:10%; --col4:15%;
  --col5:15%; --col6:8%; --col7:8%; --col8:9%;
  --pageMax:2000px;
}

/* ===== Stronger Level-1 hero card ===== */
.hero{
  background:radial-gradient(1600px 500px at 20% -20%, rgba(59,130,246,.18), transparent 60%),
             linear-gradient(180deg, #0f1b34 0%, #0a1226 100%);
  border:1px solid rgba(96,165,250,.35);
  border-radius:18px;
  padding:18px 20px;
  margin:8px 0 16px 0;
  box-shadow:0 18px 30px rgba(0,0,0,.35), inset 0 0 0 1px rgba(59,130,246,.15);
}
.hero .title{
  font-size:1.35rem;font-weight:800;color:var(--text);
  text-shadow:0 0 18px rgba(59,130,246,.25);
}
.hero .badge{
  margin-left:12px;padding:3px 10px;font-weight:700;
  border-color:rgba(96,165,250,.5);
  background:linear-gradient(180deg,rgba(14,165,233,.18),rgba(14,165,233,.10));
}
.hero .kpis{gap:28px}
.hero .kpi{font-size:.95rem;color:#cbd5e1}
.hero .kpi b{color:#e5e7eb}
.hero .ok{color:#22c55e;font-weight:800}
.hero .bad{color:#ef4444;font-weight:800}
.sep{height:1px;background:linear-gradient(90deg,rgba(96,165,250,.35),rgba(96,165,250,.08));margin:12px 0 8px;border-radius:1px}

/* ============ Cards ============ */
.section-card{
  background:linear-gradient(180deg,#0f1a31,#0b1326);
  border:1px solid #223355;border-radius:12px;
  padding:12px 14px;margin:6px 0 10px 0;
  box-shadow:0 0 0 1px rgba(36,52,83,.35) inset;
}
.table-card{
  background:linear-gradient(180deg,rgba(15,23,42,.65),rgba(11,18,36,.6));
  border:1px solid #1f2a44;border-radius:14px;
  padding:12px;margin:8px 0;
  box-shadow:0 6px 16px rgba(0,0,0,.22);
  overflow:hidden;
}
.table-wrap{width:100%;overflow-x:auto}

/* ============ Table ============ */
table.neo{width:100%;border-collapse:separate;border-spacing:0;table-layout:fixed}
table.neo th, table.neo td{
  padding:10px 12px;font-size:.95rem;color:var(--text);
  border-bottom:1px solid rgba(31,42,68,.8);overflow:hidden;text-overflow:ellipsis;
}
table.neo thead th{
  font-size:.85rem;text-transform:uppercase;letter-spacing:.3px;
  color:#aab4c3;font-weight:700;text-align:left;
  border-bottom:1px solid var(--line);
}
table.neo tbody tr:hover{background:rgba(148,163,184,.06)}
.ok{color:var(--ok);font-weight:700}
.bad{color:var(--bad);font-weight:700}

/* --- Alignement header/table --- */
.table-card .neo thead th:nth-child(1),
.table-card .neo tbody td:nth-child(1){width:var(--col1)}
.table-card .neo thead th:nth-child(2),
.table-card .neo tbody td:nth-child(2){width:var(--col2)}
.table-card .neo thead th:nth-child(3),
.table-card .neo tbody td:nth-child(3){width:var(--col3)}
.table-card .neo thead th:nth-child(4),
.table-card .neo tbody td:nth-child(4){width:var(--col4)}
.table-card .neo thead th:nth-child(5),
.table-card .neo tbody td:nth-child(5){width:var(--col5)}
.table-card .neo thead th:nth-child(6),
.table-card .neo tbody td:nth-child(6){width:var(--col6)}
.table-card .neo thead th:nth-child(7),
.table-card .neo tbody td:nth-child(7){width:var(--col7)}
.table-card .neo thead th:nth-child(8),
.table-card .neo tbody td:nth-child(8){width:var(--col8)}

/* --- Grille N2 alignée --- */
.n2-grid{
  display:grid !important;
  grid-template-columns:var(--col1) var(--col2) var(--col3) var(--col4)
                       var(--col5) var(--col6) var(--col7) var(--col8);
  align-items:center;gap:12px;
}
.n2g-label,.lvl{display:flex;align-items:center;gap:6px}
.n2g-cell{display:flex;flex-direction:column;gap:2px}

/* --- Barres mini --- */
.mbar{height:8px;width:100%;max-width:140px;background:var(--line);border-radius:999px;overflow:hidden}
.mfill{height:100%;border-radius:999px;transition:width .35s ease}
.mfill.blue{background:#3b82f6}
.mfill.green{background:#22c55e}

/* === Layout large & page === */
[data-testid="stAppViewContainer"] .main .block-container,
section[data-testid="stMain"] > div{
  max-width:var(--pageMax)!important;width:100%!important;
  padding:0 16px!important;margin:0 auto!important;
}
.section-card,.table-card{width:100%!important}

/* === Fix texte vertical === */
.table-card .neo th,.table-card .neo td{
  writing-mode:horizontal-tb!important;text-orientation:mixed!important;
  transform:none!important;white-space:nowrap!important;
  word-break:keep-all!important;overflow:visible!important;
}

/* === Responsive === */
@media (max-width:1750px){
  :root{
    --col1:26%;--col2:9%;--col3:9%;--col4:12%;
    --col5:12%;--col6:10%;--col7:10%;--col8:12%;
  }
  .mbar{max-width:120px}
}
@media (min-width:2200px){:root{--pageMax:2300px}}
</style>
"""

def inject_theme():
    st.markdown(CSS, unsafe_allow_html=True)
