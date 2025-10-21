# theme.py
import streamlit as st

CSS = """
<style>
/* ============ Layout global ============ */
header[data-testid="stHeader"]{opacity:0;height:0}
.block-container{
  padding-top:1.4rem!important;
  max-width:2000px!important;
  padding-left:16px!important;
  padding-right:16px!important;
}
*{font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Arial}

/* ============ Tokens ============ */
:root{
  --bg:#0b1220; --glass:#0f172a; --glass2:#0b1224; --line:#1f2a44;
  --text:#e5e7eb; --muted:#94a3b8; --ok:#22c55e; --bad:#ef4444; --accent:#60a5fa;
  --col1:26%; --col2:10%; --col3:10%; --col4:15%; --col5:15%; --col6:8%; --col7:8%; --col8:8%;
}

/* ============ Hero (Niveau 1) ============ */
.hero{
  background:
    radial-gradient(1600px 500px at 20% -20%, rgba(59,130,246,.18), transparent 60%),
    linear-gradient(180deg,#0f1b34 0%,#0a1226 100%);
  border:1px solid rgba(96,165,250,.35);
  border-radius:18px; padding:18px 20px; margin:8px 0 16px;
  box-shadow:0 18px 30px rgba(0,0,0,.35), inset 0 0 0 1px rgba(59,130,246,.15);
}
.hero .title{font-size:1.35rem;font-weight:800;color:var(--text);text-shadow:0 0 18px rgba(59,130,246,.25);letter-spacing:.2px}
.hero .badge{
  margin-left:12px;padding:3px 10px;font-weight:700;border:1px solid rgba(96,165,250,.5);
  background:linear-gradient(180deg,rgba(14,165,233,.18),rgba(14,165,233,.10));border-radius:999px;color:#cffafe;font-size:.8rem
}
.hero .kpis{display:flex;gap:28px;flex-wrap:wrap}
.hero .kpi{font-size:.95rem;color:#cbd5e1}
.hero .ok{color:var(--ok);font-weight:800}
.hero .bad{color:var(--bad);font-weight:800}

/* ============ Section / Carte N2 ============ */
.section-card{
  background:linear-gradient(180deg,#0f1a31,#0b1326);
  border:1px solid #223355;border-radius:12px;padding:12px 14px;margin:6px 0 10px;box-shadow:0 0 0 1px rgba(36,52,83,.35) inset
}
.n2-grid{
  display:grid;
  grid-template-columns:var(--col1) var(--col2) var(--col3) var(--col4) var(--col5) var(--col6) var(--col7) var(--col8);
  align-items:center;gap:0;padding:10px 12px
}
.n2g-label,.n2g-cell{padding:10px 12px!important;box-sizing:border-box}
.n2g-label{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.n2g-label .title{font-size:1.15rem;font-weight:750;color:#f1f5f9;letter-spacing:.2px;text-shadow:0 0 6px rgba(59,130,246,.25)}
.n2g-label .badge{
  padding:3px 10px;font-size:.78rem;font-weight:700;color:#cffafe;
  background:linear-gradient(180deg,rgba(14,165,233,.18),rgba(14,165,233,.10));
  border:1px solid rgba(96,165,250,.5);border-radius:999px
}
/* libellé au-dessus de la valeur */
.n2g-cell{display:flex;flex-direction:column;align-items:flex-start}
.n2g-cell .small{font-size:.78rem;color:#aab4c3;text-transform:uppercase;letter-spacing:.3px;margin-bottom:4px}
.n2g-cell b{font-weight:700;color:var(--text)}
/* >>> couleurs des valeurs N2 (Écart/Impact/Gliss) */
.n2g-cell b.ok{color:var(--ok)!important}
.n2g-cell b.bad{color:var(--bad)!important}

/* ============ Tableau “neo” (flat, sans traits) ============ */
.table-card{
  background:linear-gradient(180deg,rgba(15,23,42,.65),rgba(11,18,36,.6));
  border:1px solid #1f2a44;border-radius:14px;padding:12px;margin:8px 0;box-shadow:0 6px 16px rgba(0,0,0,.22);overflow:hidden
}
.table-wrap{width:100%;overflow-x:auto}
table.neo{width:100%;border-collapse:separate;border-spacing:0;table-layout:fixed}

/* en-tête sans bordure */
table.neo thead th{
  font-size:.85rem;letter-spacing:.3px;text-transform:uppercase;color:#aab4c3;font-weight:700;text-align:left;
  padding:10px 12px;border-bottom:0!important;white-space:nowrap
}
/* cellules sans bordure */
table.neo td{
  padding:12px;font-size:.95rem;color:var(--text);border-bottom:0!important
}
table.neo tbody tr:hover{background:rgba(148,163,184,.06);transition:background .12s ease}

/* largeur cohérente */
.table-card .neo th:nth-child(1),.table-card .neo td:nth-child(1){width:var(--col1)}
.table-card .neo th:nth-child(2),.table-card .neo td:nth-child(2){width:var(--col2)}
.table-card .neo th:nth-child(3),.table-card .neo td:nth-child(3){width:var(--col3)}
.table-card .neo th:nth-child(4),.table-card .neo td:nth-child(4){width:var(--col4)}
.table-card .neo th:nth-child(5),.table-card .neo td:nth-child(5){width:var(--col5)}
.table-card .neo th:nth-child(6),.table-card .neo td:nth-child(6){width:var(--col6)}
.table-card .neo th:nth-child(7),.table-card .neo td:nth-child(7){width:var(--col7)}
.table-card .neo th:nth-child(8),.table-card .neo td:nth-child(8){width:var(--col8)}

/* barres mini */
.mbar{position:relative;height:8px;width:160px;background:#1f2a44;border-radius:999px;overflow:hidden;display:inline-block;vertical-align:middle}
.mfill{height:100%;border-radius:999px;transition:width .35s ease}
.mfill.blue{background:#3b82f6}.mfill.green{background:#22c55e}
.mval{display:inline-block;min-width:56px;margin-left:8px}

/* pastille + couleurs génériques */
.dot{width:8px;height:8px;background:var(--accent);border-radius:999px;display:inline-block}
.ok{color:var(--ok);font-weight:700}
.bad{color:var(--bad);font-weight:700}
</style>
"""

def inject_theme():
    st.markdown(CSS, unsafe_allow_html=True)
