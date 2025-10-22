# app.py — upload Excel -> extraction WBS instantanée
import streamlit as st
import plotly.graph_objects as go
from theme import inject_theme
from data import load_all_wbs
from extract_wbs_json import extract_all_wbs  # <- utilise ton script d’extraction
import pandas as pd
import tempfile, os

st.set_page_config(page_title="WBS – Projet", layout="wide", initial_sidebar_state="expanded")
inject_theme()

# ---------- Helpers ----------
def _minify(html: str) -> str:
    return "".join(line.strip() for line in html.splitlines())

def _safe_float(x):
    try:
        return float(x)
    except Exception:
        return 0.0

def fmt_pct(x, signed=False):
    try:
        v = float(x)
        sign = "+" if signed and v > 0 else ""
        return f"{sign}{v:.2f}%"
    except Exception:
        return str(x)

def to_number_j(val):
    s = str(val).replace("j", "").strip()
    try:
        return float(s)
    except:
        return 0.0

def bar_html(pct: float, color: str, vertical: bool = True) -> str:
    safe = max(0, min(100, pct or 0))
    cls = "mbar-wrap v" if vertical else "mbar-wrap"
    return f"""
    <span class="{cls}">
      <span class="mbar">
        <span class="mfill anim {color}" style="--to:{safe}%;"></span>
      </span>
      <span class="mval">{safe:.2f}%</span>
    </span>
    """







# ---------- Rendu N3 (table détail) ----------
def render_detail_table(node: dict, compact: bool = False):
    rows = []
    for ch in node.get("children", []) or []:
        m = ch.get("metrics", {}) or {}
        rows.append({
            "label":    ch.get("label",""),
            "planned":  m.get("planned_finish",""),
            "forecast": m.get("forecast_finish",""),
            "schedule": _safe_float(m.get("schedule",0)),
            "earned":   _safe_float(m.get("earned", m.get("units", 0))),
            "ecart":    _safe_float(m.get("ecart",0)),
            "impact":   _safe_float(m.get("impact",0)),
            "gliss":    to_number_j(m.get("glissement","0")),
        })

    def signed_span(v):
        s = f"{'+' if v>0 else ''}{v:.2f}%"
        cls = "ok" if v >= 0 else "bad"
        return f'<span class="{cls}">{s}</span>'

    trs = []
    for r in rows:
        trs.append(_minify(f"""
          <tr>
            <td class="lvl"><span class="dot"></span> <b>{r['label']}</b></td>
            <td class="col-date">{r['planned']}</td>
            <td class="col-date">{r['forecast']}</td>
            <td class="col-bar">{bar_html(r['schedule'], 'blue')}</td>
            <td class="col-bar">{bar_html(r['earned'],   'green')}</td>
            <td class="col-sign">{signed_span(r['ecart'])}</td>
            <td class="col-sign">{signed_span(r['impact'])}</td>
            <td class="col-gliss"><span class="{'ok' if r['gliss']>=0 else 'bad'}">{int(r['gliss'])}j</span></td>
          </tr>
        """))

    st.markdown(_minify(f"""
    <div class="table-card">
      <div class="table-wrap">
        <table class="neo">
          <thead>
            <tr>
              <th></th>
              <th>Planned</th>
              <th>Forecast</th>
              <th>Schedule</th>
              <th>Earned</th>
              <th>Écart</th>
              <th>Impact</th>
              <th>Glissement</th>
            </tr>
          </thead>
          <tbody>{''.join(trs)}</tbody>
        </table>
      </div>
    </div>
    """), unsafe_allow_html=True)

# ---------- Graph barres ----------
def render_barchart(node: dict):
    labels, schedule, earned = [], [], []
    for ch in node.get("children", []) or []:
        labels.append(ch.get("label", ""))
        m = ch.get("metrics", {}) or {}
        schedule.append(_safe_float(m.get("schedule", 0)))
        earned.append(_safe_float(m.get("earned", m.get("units", 0))))

    if not labels:
        st.info("Aucun enfant pour le graphique.")
        return

    fig = go.Figure()
    fig.add_bar(name="Schedule %", x=labels, y=schedule, offsetgroup="g1",
                marker=dict(color="#3b82f6", line=dict(width=0)),
                hovertemplate="Schedule: %{y:.2f}%<extra>%{x}</extra>")
    fig.add_bar(name="Units %", x=labels, y=earned, offsetgroup="g2",
                marker=dict(color="#22c55e", line=dict(width=0)),
                hovertemplate="Units: %{y:.2f}%<extra>%{x}</extra>")
    fig.update_layout(
        barmode="group", bargroupgap=0.18, bargap=0.26,
        height=280, margin=dict(l=20, r=20, t=8, b=60),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.32, xanchor="center", x=0.5,
            itemclick=False, itemdoubleclick=False,
            font=dict(size=12, color="#cbd5e1")
        ),
        xaxis=dict(
            title="", showgrid=False, tickfont=dict(size=13, color="#e5e7eb"), zeroline=False
        ),
        yaxis=dict(
            title="", showgrid=True, gridcolor="rgba(42,59,98,.55)", zeroline=False,
            tickfont=dict(size=12, color="#cbd5e1"), range=[0, 100]
        ),
        hoverlabel=dict(bgcolor="#0f172a", font=dict(color="#e5e7eb")),
    )

    # 👇 Add this line for smooth animated redraws
    fig.update_layout(transition={'duration': 400})

    st.plotly_chart(fig, use_container_width=True)

# ---------- En-têtes N1/N2 (avec loaders KPI) ----------
def header_level1_grid(label_n1: str, m: dict) -> str:
    planned  = m.get("planned_finish","")
    forecast = m.get("forecast_finish","")

    sched_v  = _safe_float(m.get("schedule",0))
    earn_v   = _safe_float(m.get("earned", m.get("units",0)))

    ecart_v  = _safe_float(m.get("ecart",0))
    impact_v = _safe_float(m.get("impact",0))
    ecart    = fmt_pct(ecart_v,  signed=True)
    impact   = fmt_pct(impact_v, signed=True)

    ecls = "ok" if ecart_v  >= 0 else "bad"
    icls = "ok" if impact_v >= 0 else "bad"

    gnum = to_number_j(m.get("glissement","0"))
    gcls = "ok" if gnum >= 0 else "bad"
    gliss = f"{int(gnum)}j"

    return _minify(f"""
    <div class="hero">
      <div class="n1-grid">
        <div class="n1g-label">
          <span class="dot"></span>
          <span class="title">{label_n1}</span>
          <span class="badge">WBS Niveau 1</span>
        </div>

        <div class="n1g-cell"><span class="small">Planned</span><b>{planned}</b></div>
        <div class="n1g-cell"><span class="small">Forecast</span><b>{forecast}</b></div>

        <div class="n1g-cell"><span class="small">Schedule</span>{bar_html(sched_v, 'blue')}</div>
        <div class="n1g-cell"><span class="small">Earned</span>{bar_html(earn_v, 'green')}</div>

        <div class="n1g-cell"><span class="small">Écart</span><b class="{ecls}">{ecart}</b></div>
        <div class="n1g-cell"><span class="small">Impact</span><b class="{icls}">{impact}</b></div>
        <div class="n1g-cell"><span class="small">Glissement</span><b class="{gcls}">{gliss}</b></div>
      </div>
    </div>
    """)

def header_level2_grid(label, level, m):
    planned  = m.get("planned_finish","")
    forecast = m.get("forecast_finish","")

    sched_v  = _safe_float(m.get("schedule",0))
    earn_v   = _safe_float(m.get("earned", m.get("units",0)))

    ecart_v  = _safe_float(m.get("ecart",0))
    impact_v = _safe_float(m.get("impact",0))
    ecart    = fmt_pct(ecart_v,  signed=True)
    impact   = fmt_pct(impact_v, signed=True)

    ecls = "ok" if ecart_v  >= 0 else "bad"
    icls = "ok" if impact_v >= 0 else "bad"

    gnum   = to_number_j(m.get("glissement","0"))
    gcls   = "ok" if gnum >= 0 else "bad"
    gliss  = f"{int(gnum)}j"

    return _minify(f"""
    <div class="n2-grid">
      <div class="n2g-label">
        <span class="dot"></span>
        <span class="title">{label}</span>
        <span class="badge">WBS Niveau {level}</span>
      </div>

      <div class="n2g-cell"><span class="small">Planned</span><b>{planned}</b></div>
      <div class="n2g-cell"><span class="small">Forecast</span><b>{forecast}</b></div>

      <div class="n2g-cell"><span class="small">Schedule</span>{bar_html(sched_v, 'blue')}</div>
      <div class="n2g-cell"><span class="small">Earned</span>{bar_html(earn_v, 'green')}</div>

      <div class="n2g-cell"><span class="small">Écart</span><b class="{ecls}">{ecart}</b></div>
      <div class="n2g-cell"><span class="small">Impact</span><b class="{icls}">{impact}</b></div>
      <div class="n2g-cell gliss"><span class="small">Glissement</span><b class="{gcls}">{gliss}</b></div>
    </div>
    """)

# ---------- Rendu global ----------
def render_section_level2(parent_node: dict):
    label   = parent_node.get("label","")
    level   = parent_node.get("level",2)
    metrics = parent_node.get("metrics",{}) or {}

    header_html = header_level2_grid(label, level, metrics)

    # On met un titre minimal dans l'expander, mais on affiche le vrai header juste dedans
    with st.expander("", expanded=False):
        st.markdown(f'<div class="section-card">{header_html}</div>', unsafe_allow_html=True)
        render_detail_table(parent_node)
        render_barchart(parent_node)









def render_all_open_native(root: dict):
    st.markdown(
        header_level1_grid(
            root.get("label", "CONSTRUCTION NEUVE"),
            root.get("metrics", {}) or {}
        ),
        unsafe_allow_html=True
    )
    st.divider()
    with st.container(border=True):
        for n2 in root.get("children", []) or []:
            render_section_level2(n2)

# ---------- Sources de données ----------
st.sidebar.markdown("### Import WBS")
uploaded = st.sidebar.file_uploader(
    "Charger un Excel de suivi (.xlsx)",
    type=["xlsx","xlsm"],
    accept_multiple_files=False,
    help="L’app détecte automatiquement les tableaux contenant Planned/Forecast/Schedule/Earned etc. et reconstruit le WBS."
)
packs = []

if uploaded is not None:
    # sauvegarder en fichier temp pour openpyxl
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        tmp.write(uploaded.read())
        tmp_path = tmp.name
    try:
        packs = extract_all_wbs(tmp_path)  # ← renvoie une liste [{sheet, range, wbs}, ...]
        if not packs:
            st.warning("Aucun tableau valide détecté dans ce fichier. Vérifie les en-têtes requis.")
        else:
            st.success(f"{len(packs)} tableau(x) WBS détecté(s) • Feuilles: " + ", ".join({p['sheet'] for p in packs}))
    except Exception as e:
        st.error(f"Erreur d’extraction: {e}")
    finally:
        try:
            os.unlink(tmp_path)
        except:
            pass

# Aucun fichier uploadé : on reste vide
if not packs:
    st.info("🔹 Veuillez importer un fichier Excel pour générer le WBS.")
    st.stop()

# ---------- Sélecteur et rendu ----------
labels = [f"{i+1}. {p.get('wbs',{}).get('label','WBS')}  [{p.get('sheet','') or '?'} {p.get('range','') or ''}]"
          for i, p in enumerate(packs)]
idx = st.sidebar.selectbox("WBS à afficher", options=range(len(labels)), format_func=lambda i: labels[i], index=0 if packs else 0)
root = packs[idx]["wbs"] if packs else {"label":"Aucun WBS","level":1,"metrics":{},"children":[]}

render_all_open_native(root)
st.caption("Import Excel → extraction auto → rendu hiérarchique. Les colonnes requises: Planned/Forecast/Schedule/Earned/ecart/impact/Glissement.")
