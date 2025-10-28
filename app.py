# app.py — upload Excel -> extraction WBS instantanée
import streamlit as st
import plotly.graph_objects as go
from theme import inject_theme
from data import load_all_wbs
from extract_wbs_json import extract_all_wbs  # <- utilise ton script d’extraction
import pandas as pd
import tempfile, os
import math  # <- NEW

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
        sign = "+" if signed and v >= 0 else ""
        txt = f"{v:.2f}".rstrip("0").rstrip(".")
        return f"{sign}{txt}%"
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




def render_barchart(node: dict) -> bool:
    labels, schedule, earned = [], [], []
    for ch in (node.get("children") or []):
        labels.append(ch.get("label",""))
        m = (ch.get("metrics") or {})
        schedule.append(_safe_float(m.get("schedule",0)))
        earned.append(_safe_float(m.get("earned", m.get("units",0))))

    if not labels:
        return False  # rien à tracer

    vmax = max([0]+schedule+earned)
    ymax = 100 if vmax <= 100 else math.ceil(vmax/5)*5

    # Couleurs (loader): bleu = Schedule, vert = Earned
    c_text="#e5e7eb"; c_grid="rgba(42,59,98,.55)"
    c_sched="#3b82f6"; c_earn="#22c55e"

    n=len(labels)
    idx=list(range(n))
    delta=0.16      # rapproche les barres
    w=0.26          # plus fines
    gloss_alpha=0.45  # intensité du reflet

    fig=go.Figure()

    # Glossy trick = superposer 2 barres : base + reflet clair semi-transparent
    # --- Schedule ---
    fig.add_bar(
        name="Schedule %", x=[i - delta for i in idx], y=[v*1.02 for v in schedule],
        width=w, marker=dict(color=c_sched), opacity=1,
        hoverinfo="skip", showlegend=False, cliponaxis=False
    )
    fig.add_bar(
        name="Schedule %", x=[i - delta for i in idx], y=schedule,
        width=w, marker=dict(
            color=f"rgba(96,165,250,{gloss_alpha})", line=dict(color="#93c5fd", width=0.8)
        ),
        text=[f"{v:.1f}%" for v in schedule], textposition="outside",
        textfont=dict(size=12, color=c_text),
        hovertemplate="<b>%{customdata}</b><br>Schedule: %{y:.2f}%<extra></extra>",
        customdata=labels, cliponaxis=False
    )

    # --- Earned ---
    fig.add_bar(
        name="Earned %", x=[i + delta for i in idx], y=[v*1.02 for v in earned],
        width=w, marker=dict(color=c_earn), opacity=1,
        hoverinfo="skip", showlegend=False, cliponaxis=False
    )
    fig.add_bar(
        name="Earned %", x=[i + delta for i in idx], y=earned,
        width=w, marker=dict(
            color=f"rgba(34,197,94,{gloss_alpha})", line=dict(color="#86efac", width=0.8)
        ),
        text=[f"{v:.1f}%" for v in earned], textposition="outside",
        textfont=dict(size=12, color=c_text),
        hovertemplate="<b>%{customdata}</b><br>Earned: %{y:.2f}%<extra></extra>",
        customdata=labels, cliponaxis=False
    )

    # Centrage parfait
    fig.update_xaxes(
        type="linear", tickmode="array", tickvals=idx, ticktext=labels,
        tickfont=dict(size=13, color=c_text),
        range=[-0.6, n-0.4], showgrid=False, zeroline=False, showspikes=False
    )

    shapes=[]
    if ymax==100:
        shapes.append(dict(type="line", xref="paper", x0=0, x1=1, y0=100, y1=100,
                           line=dict(width=1, dash="dot", color=c_grid)))

    fig.update_layout(
        barmode="overlay", bargap=0.3,
        height=320, margin=dict(l=8, r=24, t=12, b=60),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(size=13, color=c_text),
        legend=dict(
            orientation="h", y=-0.30, x=0.5, xanchor="center",
            itemclick=False, itemdoubleclick=False,
            font=dict(size=12, color="#cbd5e1")
        ),
        yaxis=dict(
            title="", range=[0, ymax*1.1], ticksuffix="%",
            dtick=25 if ymax==100 else None,
            showgrid=True, gridcolor=c_grid, zeroline=False,
            tickfont=dict(size=12, color=c_text), showspikes=False
        ),
        hovermode="closest",
        hoverlabel=dict(bgcolor="#0f172a", font=dict(color=c_text, size=12)),
        shapes=shapes,
        transition=None
    )

    st.plotly_chart(fig, use_container_width=True, config={
        "displaylogo": False, "displayModeBar": "hover",
        "modeBarButtonsToRemove": [
            "select2d","lasso2d","autoScale2d","zoomIn2d","zoomOut2d","toggleSpikelines"
        ], "responsive": True
    })
    return True   # ← ajoute ceci



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
def _slug(s: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in s)

def render_section_level2(parent_node: dict):
    label = parent_node.get("label","")
    level = parent_node.get("level", 2)
    metrics = parent_node.get("metrics") or {}
    has_children = bool(parent_node.get("children"))

    base = f"n2_open--{_slug(label)}_{level}"
    if base not in st.session_state:
        st.session_state[base] = False

    # ----- Ligne visuelle
    left, right = st.columns([0.985, 0.015], gap="small")
    # ... dans render_section_level2(...)
    with left:
        st.markdown(header_level2_grid(label, level, metrics), unsafe_allow_html=True)
        if has_children:
            if st.button(" ", key=f"{base}__rowbtn", use_container_width=True):  # <- pas de help=
                st.session_state[base] = not st.session_state[base]

    # ----- supprime totalement la flèche de droite (Option A) -----
    # with right:  # <- retire ce bloc si tu n'en veux plus
    #     if has_children:
    #         if st.button("▾", key=f"{base}__btn"):
    #             st.session_state[base] = not st.session_state[base]

    # ----- N3 -----
    if has_children and st.session_state[base]:
        st.markdown('<div class="n3load v1"></div>', unsafe_allow_html=True)
        render_detail_table(parent_node)
        _ = render_barchart(parent_node)  # pas de wrapper n3chart -> plus de div vide


        # n'affiche la section chart que si un vrai graphe est rendu
        has_chart_data = parent_node.get("children") and any(
            c.get("metrics") for c in parent_node["children"]
        )
        if has_chart_data:
            st.markdown('<div class="n3chart">', unsafe_allow_html=True)
            render_barchart(parent_node)
            st.markdown('</div>', unsafe_allow_html=True)








































def render_all_open_native(root: dict):
    st.markdown(
        header_level1_grid(root.get("label", "CONSTRUCTION NEUVE"),
                           root.get("metrics", {}) or {}),
        unsafe_allow_html=True
    )
    st.divider()
    # ⛔️ supprime ce conteneur borduré
    # with st.container(border=True):
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
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        tmp.write(uploaded.read())
        tmp_path = tmp.name
    try:
        packs = extract_all_wbs(tmp_path)
        if not packs:
            st.sidebar.warning("Aucun tableau valide détecté dans ce fichier. Vérifie les en-têtes requis.")
        else:
            sheets = ", ".join(sorted({p.get("sheet", "?") for p in packs}))
            st.sidebar.success(f"{len(packs)} tableau(x) WBS détecté(s) • Feuilles: {sheets}")
    except Exception as e:
        st.sidebar.error(f"Erreur d’extraction: {e}")
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
labels = [f"{i+1}. {p.get('wbs',{}).get('label','WBS')}" for i, p in enumerate(packs)]

idx = st.sidebar.radio(
    "WBS à afficher",
    options=range(len(labels)),
    format_func=lambda i: labels[i],
    index=0 if packs else 0,
)

sel = packs[idx]
st.sidebar.caption(f"Feuille: {sel.get('sheet','?')} • Zone: {sel.get('range','?')}")
root = sel["wbs"]







render_all_open_native(root)

# Ajoute un petit espace visuel en bas de la page
st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)

