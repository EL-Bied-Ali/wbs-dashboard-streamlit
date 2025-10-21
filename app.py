# app.py — upload Excel -> extraction WBS instantanée
import streamlit as st
import plotly.graph_objects as go
from theme import inject_theme
from data import load_all_wbs
from extract_wbs_json import extract_all_wbs  # <- utilise ton script d’extraction
import pandas as pd
import tempfile, os

st.set_page_config(page_title="WBS – Projet", layout="wide")
inject_theme()

# ---------- Helpers ----------
def _minify(html: str) -> str: return "".join(line.strip() for line in html.splitlines())
def _safe_float(x):
    try: return float(x)
    except Exception: return 0.0
def fmt_pct(x, signed=False):
    try:
        v = float(x); sign = "+" if signed and v > 0 else ""
        return f"{sign}{v:.2f}%"
    except Exception: return str(x)
def to_number_j(val):
    s = str(val).replace("j","").strip()
    try: return float(s)
    except: return 0.0

def kpi_html(m: dict):
    planned = m.get("planned_finish","")
    forecast = m.get("forecast_finish","")
    schedule = fmt_pct(m.get("schedule",0))
    earned   = fmt_pct(m.get("earned", m.get("units", 0)))
    ecart    = fmt_pct(m.get("ecart",0), signed=True)
    impact   = fmt_pct(m.get("impact",0), signed=True)

    # --- glissement: classe ok/bad + suffixe "j"
    glis_raw = str(m.get("glissement","0"))
    gnum = to_number_j(glis_raw)
    gliss = f"{int(gnum)}j"
    glis_cls = "ok" if gnum >= 0 else "bad"

    ecart_cls  = "ok" if _safe_float(m.get("ecart",0))  >= 0 else "bad"
    impact_cls = "ok" if _safe_float(m.get("impact",0)) >= 0 else "bad"

    return _minify(f"""
    <div class="kpis">
      <span class="kpi"><span class="small">Planned:</span> <b>{planned}</b></span>
      <span class="kpi"><span class="small">Forecast:</span> <b>{forecast}</b></span>
      <span class="kpi"><span class="small">Schedule %:</span> <b>{schedule}</b></span>
      <span class="kpi"><span class="small">Earned %:</span> <b>{earned}</b></span>
      <span class="kpi"><span class="small">Écart:</span> <b class="{ecart_cls}">{ecart}</b></span>
      <span class="kpi"><span class="small">Impact:</span> <b class="{impact_cls}">{impact}</b></span>
      <span class="kpi"><span class="small">Glissement:</span> <b class="{glis_cls}">{gliss}</b></span>
    </div>""")


def header_html(label, level, metrics, big=False, show_dot=True):
    return _minify(f"""
    <div class="row">
      <div class="left">
        {'<span class="dot"></span>' if show_dot else '<span style="width:8px"></span>'}
        <span class="title {'title-lg' if big else ''}">{label}</span>
        <span class="badge">WBS Niveau {level}</span>
      </div>
      {kpi_html(metrics)}
    </div>""")

def card_block(label, level, metrics, big=False, show_dot=True, extra_cls=""):
    header = header_html(label, level, metrics, big=big, show_dot=show_dot)
    cls = "hero" if extra_cls == "hero" else "card"
    return _minify(f'<div class="{cls}">{header}</div>')

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

    def bar(val, color):
        width = max(0, min(100, val))
        return f'''
        <div class="mbar"><div class="mfill {color}" style="width:{width}%;"></div></div>
        <div class="mval">{val:.2f}%</div>
        '''

    trs = []
    for r in rows:
        trs.append(_minify(f"""
          <tr>
            <td class="lvl"><span class="dot"></span> <b>{r['label']}</b></td>
            <td class="col-date">{r['planned']}</td>
            <td class="col-date">{r['forecast']}</td>
            <td class="col-bar">{bar(r['schedule'], 'blue')}</td>
            <td class="col-bar">{bar(r['earned'],   'green')}</td>
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
        legend=dict(orientation="h", yanchor="bottom", y=-0.32, xanchor="center", x=0.5,
                    itemclick=False, itemdoubleclick=False, font=dict(size=12, color="#cbd5e1")),
        xaxis=dict(title="", showgrid=False, tickfont=dict(size=13, color="#e5e7eb"), zeroline=False),
        yaxis=dict(title="", showgrid=True, gridcolor="rgba(42,59,98,.55)", zeroline=False,
                   tickfont=dict(size=12, color="#cbd5e1"), range=[0, 100]),
        hoverlabel=dict(bgcolor="#0f172a", font=dict(color="#e5e7eb")),
    )
    st.plotly_chart(fig, use_container_width=True)

def render_section_level2(parent_node: dict):
    st.markdown(
        _minify(f'<div class="section-card">{header_level2_grid(parent_node.get("label",""), parent_node.get("level",2), parent_node.get("metrics",{}) or {})}</div>'),
        unsafe_allow_html=True
    )
    if parent_node.get("children"):
        render_detail_table(parent_node)
        render_barchart(parent_node)
    else:
        st.info("Aucun niveau 3 pour cette section.")

def render_all_open_native(root: dict):
    st.markdown(card_block(root.get("label",""), root.get("level",1), root.get("metrics",{}) or {}, big=True, show_dot=False, extra_cls="hero"), unsafe_allow_html=True)
    st.divider()
    with st.container(border=True):
        for n2 in root.get("children", []) or []:
            render_section_level2(n2)
            
def header_level2_grid(label, level, m):
    planned  = m.get("planned_finish","")
    forecast = m.get("forecast_finish","")
    schedule = fmt_pct(m.get("schedule",0))
    earned   = fmt_pct(m.get("earned", m.get("units",0)))
    ecart    = fmt_pct(m.get("ecart",0),  signed=True)
    impact   = fmt_pct(m.get("impact",0), signed=True)

    # classes couleur
    ecls = "ok" if _safe_float(m.get("ecart",0))  >= 0 else "bad"
    icls = "ok" if _safe_float(m.get("impact",0)) >= 0 else "bad"

    # glissement N2
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

      <div class="n2g-cell"><span class="small">Schedule</span><b>{schedule}</b></div>
      <div class="n2g-cell"><span class="small">Earned</span><b>{earned}</b></div>

      <div class="n2g-cell"><span class="small">Écart</span><b class="{ecls}">{ecart}</b></div>
      <div class="n2g-cell"><span class="small">Impact</span><b class="{icls}">{impact}</b></div>
      <div class="n2g-cell gliss"><span class="small">Glissement</span><b class="{gcls}">{gliss}</b></div>
    </div>
    """)



# ---------- Sources de données ----------
st.sidebar.markdown("### Import WBS")
uploaded = st.sidebar.file_uploader("Charger un Excel de suivi (.xlsx)", type=["xlsx","xlsm"], accept_multiple_files=False, help="L’app détecte automatiquement les tableaux contenant Planned/Forecast/Schedule/Earned etc. et reconstruit le WBS.")
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
        try: os.unlink(tmp_path)
        except: pass

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
