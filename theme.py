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

  /* largeurs colonnes tableau & grilles */
  --col1:26%; --col2:10%; --col3:10%; --col4:15%;
  --col5:15%; --col6:8%;  --col7:8%;  --col8:8%;

  /* TYPO agrandie + hiérarchie N1>N2>N3 */
  --fs-n1-title: 1.70rem;  /* titre principal (N1) */
  --fs-n1-kpi:   1.24rem;
  --fs-n1-label: 0.90rem;

  --fs-n2-title: 1.50rem;  /* plus grand mais < N1 */
  --fs-n2-kpi:   1.12rem;  /* valeurs un peu plus visibles */
  --fs-n2-label: 0.92rem;  /* étiquettes plus lisibles */


  --fs-n3-head:  0.95rem;  /* tableau (N3) */
  --fs-n3-cell:  1.00rem;
  --fs-small:    0.86rem;
}

/* base un peu plus grande */
html, body { font-size:17px; line-height:1.4; }

/* ============ Hero (Niveau 1) ============ */
.hero{
  background:
    radial-gradient(1600px 500px at 20% -20%, rgba(59,130,246,.18), transparent 60%),
    linear-gradient(180deg,#0f1b34 0%,#0a1226 100%);
  border:1px solid rgba(96,165,250,.35);
  border-radius:18px; padding:18px 20px; margin:8px 0 16px;
  box-shadow:0 18px 30px rgba(0,0,0,.35), inset 0 0 0 1px rgba(59,130,246,.15);
}
.hero .title{
  font-size:var(--fs-n1-title)!important;
  font-weight:800; color:var(--text);
  text-shadow:0 0 18px rgba(59,130,246,.25); letter-spacing:.2px;
}
.hero .badge{
  margin-left:12px;padding:3px 10px;font-weight:700;border:1px solid rgba(96,165,250,.5);
  background:linear-gradient(180deg,rgba(14,165,233,.18),rgba(14,165,233,.10));
  border-radius:999px;color:#cffafe;font-size:.88rem
}

/* N1 aligné sur la grille des colonnes */
.hero .n1-grid{
  display:grid;
  grid-template-columns:
    var(--col1) var(--col2) var(--col3) var(--col4)
    var(--col5) var(--col6) var(--col7) var(--col8);
  align-items:center; gap:0; width:100%;
}
.hero .n1g-label{
  display:flex; align-items:center; gap:8px; flex-wrap:wrap; padding:6px 8px;
}
.hero .n1g-label .title{
  font-size:1.22rem; font-weight:800; color:#f1f5f9;
  letter-spacing:.2px; text-shadow:0 0 8px rgba(59,130,246,.25);
}
.hero .n1g-cell{
  display:flex; flex-direction:column; align-items:flex-start; padding:6px 8px;
}
.hero .n1g-cell .small{
  font-size:var(--fs-n1-label); color:#aab4c3; text-transform:uppercase; letter-spacing:.3px; margin-bottom:4px;
}
.hero .n1g-cell b{ font-size:var(--fs-n1-kpi); font-weight:700; color:var(--text); }
.hero .n1g-cell b.ok{ color:var(--ok)!important; }
.hero .n1g-cell b.bad{ color:var(--bad)!important; }

/* ============ Section / Carte N2 ============ */
.section-card{
  background:linear-gradient(180deg,#0f1a31,#0b1326);
  border:1px solid #223355;border-radius:12px;padding:8px 10px;margin:4px 0 6px; /* compact */
  box-shadow:0 0 0 1px rgba(36,52,83,.35) inset
}
.n2-grid{
  display:grid;
  grid-template-columns:var(--col1) var(--col2) var(--col3) var(--col4) var(--col5) var(--col6) var(--col7) var(--col8);
  align-items:center; gap:0; padding:6px 8px; row-gap:2px;
}
.n2g-label,.n2g-cell{padding:6px 8px!important; box-sizing:border-box}
.n2g-label{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.n2g-label .title{
  font-size:var(--fs-n2-title); font-weight:750; color:#f1f5f9;
  letter-spacing:.2px; text-shadow:0 0 6px rgba(59,130,246,.25)
}
.n2g-label .badge{
  padding:3px 10px;font-size:.88rem;font-weight:700;color:#cffafe;
  background:linear-gradient(180deg,rgba(14,165,233,.18),rgba(14,165,233,.10));
  border:1px solid rgba(96,165,250,.5);border-radius:999px
}
/* libellé au-dessus de la valeur */
.n2g-cell{display:flex;flex-direction:column;align-items:flex-start; gap:1px!important}
.n2g-cell .small{
  font-size:var(--fs-n2-label); color:#aab4c3; text-transform:uppercase; letter-spacing:.3px; margin-bottom:4px
}
.n2g-cell b{ font-size:var(--fs-n2-kpi); font-weight:700; color:var(--text) }
.n2g-cell b.ok{ color:var(--ok)!important }
.n2g-cell b.bad{ color:var(--bad)!important }

/* ============ Tableau “neo” (flat, sans traits) ============ */
.table-card{
  background:linear-gradient(180deg,rgba(15,23,42,.65),rgba(11,18,36,.6));
  border:1px solid #1f2a44;border-radius:14px;padding:12px;margin:8px 0;
  box-shadow:0 6px 16px rgba(0,0,0,.22);overflow:hidden
}
.table-wrap{width:100%;overflow-x:auto}
table.neo{width:100%;border-collapse:separate;border-spacing:0;table-layout:fixed}

/* en-tête sans bordure */
table.neo thead th{
  font-size:var(--fs-n3-head)!important; letter-spacing:.3px; text-transform:uppercase;
  color:#aab4c3; font-weight:700; text-align:left; padding:10px 12px; border-bottom:0!important; white-space:nowrap
}
/* cellules sans bordure */
table.neo td{
  padding:12px; font-size:var(--fs-n3-cell)!important; color:var(--text); border-bottom:0!important
}
table.neo tbody tr:hover{background:rgba(148,163,184,.06);transition:background .12s ease}

/* largeur cohérente (thead + tbody) */
.table-card .neo th:nth-child(1),.table-card .neo td:nth-child(1){width:var(--col1)}
.table-card .neo th:nth-child(2),.table-card .neo td:nth-child(2){width:var(--col2)}
.table-card .neo th:nth-child(3),.table-card .neo td:nth-child(3){width:var(--col3)}
.table-card .neo th:nth-child(4),.table-card .neo td:nth-child(4){width:var(--col4)}
.table-card .neo th:nth-child(5),.table-card .neo td:nth-child(5){width:var(--col5)}
.table-card .neo th:nth-child(6),.table-card .neo td:nth-child(6){width:var(--col6)}
.table-card .neo th:nth-child(7),.table-card .neo td:nth-child(7){width:var(--col7)}
.table-card .neo th:nth-child(8),.table-card .neo td:nth-child(8){width:var(--col8)}
    

/* pastille + couleurs génériques */
.dot{width:8px;height:8px;background:var(--accent);border-radius:999px;display:inline-block}
.ok{color:var(--ok);font-weight:700}
.bad{color:var(--bad);font-weight:700}

/* ==== NO LINES IN TABLE (.neo) – hard override ==== */
.table-card table.neo, .table-card table.neo * { border:0!important; box-shadow:none!important; }
.table-card table.neo thead th, .table-card table.neo tbody td { border-bottom:0!important; }
.table-card table.neo th + th, .table-card table.neo td + td { border-left:0!important; }

/* Responsive ajustements typographiques */
@media (max-width:1400px){
  :root{
    --fs-n1-title:1.55rem; --fs-n1-kpi:1.02rem;
    --fs-n2-title:1.22rem; --fs-n2-kpi:0.96rem;
    --fs-n3-head:0.90rem;  --fs-n3-cell:0.98rem;
  }
}
@media (min-width:2000px){
  :root{ --fs-n1-title:1.80rem; }
}

/* barres mini */
.mbar-wrap{
  display:flex;
  align-items:center;
  gap:8px;
}
.mbar{
  position:relative;
  height:10px;
  width:160px;
  background:#1f2a44;
  border-radius:999px;
  overflow:hidden;
  flex-shrink:0;
}
.mfill{
  display:block;              /* <-- indispensable, sinon la width est ignorée */
  height:100%;
  border-radius:999px;
  transition:width .35s ease;
}

.mfill.blue{background:#3b82f6}
.mfill.green{background:#22c55e}
.mval{
  font-weight:700;
  color:var(--text);
  font-size:0.95rem;
  min-width:52px;
  text-align:right;
}

/* animation fluide */
@keyframes growBar { from { width:0 } to { width:var(--to, 0%) } }
.mfill.anim{animation:growBar .6s ease-out both}

/* En-têtes N1/N2 : alignement horizontal cohérent */
.hero .mbar-wrap, .section-card .mbar-wrap{
  width:100%;
  max-width:200px;
}

.hero .mval, .section-card .mval{
  min-width:56px;
  margin-left:8px;
  display:inline-block;
}

/* ==== Barres NIVEAU 2 verticales ==== */
.section-card .n2g-cell .mbar-wrap{
  flex-direction: column;         /* place la barre sous le texte */
  align-items: flex-start;        /* aligne à gauche */
  gap: 4px;                       /* petit espace entre texte et barre */
}

.section-card .n2g-cell .mval{
  margin-left: 0;                 /* supprime l'espace horizontal */
  text-align: left;               /* aligne le pourcentage sous la barre */
  font-size: 0.9rem;              /* un peu plus discret */
  color: #aab4c3;
}


</style>
"""

def inject_theme():
    st.markdown(CSS, unsafe_allow_html=True)
