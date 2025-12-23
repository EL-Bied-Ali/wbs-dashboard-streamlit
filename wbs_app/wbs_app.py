# app.py — Sidebar conservée / boutons déplacés à DROITE (compact)
import streamlit as st
import plotly.graph_objects as go
from theme import inject_theme
from extract_wbs_json import extract_all_wbs
import tempfile, os, math

st.set_page_config(page_title="WBS – Projet", layout="wide", initial_sidebar_state="expanded")
inject_theme()
st.markdown("""
<div class="bg-aurora a1"></div>
<div class="bg-aurora a2"></div>
<div class="bg-aurora grid"></div>
""", unsafe_allow_html=True)

def _minify(s:str)->str: return "".join(l.strip() for l in s.splitlines())
def _sf(x): 
    try: return float(x)
    except: return 0.0
def _pct(x,signed=False):
    try:
        v=float(x); sign="+" if signed and v>=0 else ""; t=f"{v:.2f}".rstrip("0").rstrip(".")
        return f"{sign}{t}%"
    except: return str(x)
def _to_j(v): 
    try: return float(str(v).replace("j","").strip())
    except: return 0.0
def _bar(v,color, variant:int|None=None):
    v=max(0,min(100,v or 0))
    variant = 0 if variant is None else int(variant)%2
    return f'<span class="mbar-wrap"><span class="mbar"><span class="mfill anim av{variant} {color}" style="--to:{v}%;"></span></span><span class="mval">{v:.2f}%</span></span>'

def render_detail_table(node:dict, anim_variant:int=0):
    rows=[]
    for ch in (node.get("children") or []):
        m=ch.get("metrics") or {}
        rows.append(dict(
            label=ch.get("label",""),
            planned=m.get("planned_finish",""),
            forecast=m.get("forecast_finish",""),
            schedule=_sf(m.get("schedule",0)),
            earned=_sf(m.get("earned",m.get("units",0))),
            ecart=_sf(m.get("ecart",0)),
            impact=_sf(m.get("impact",0)),
            gliss=_to_j(m.get("glissement","0")),
        ))
    def sgn(v): 
        cls="ok" if v>=0 else "bad"
        return f'<span class="{cls}">{("+" if v>0 else "")}{v:.2f}%</span>'
    trs=[]
    for r in rows:
        trs.append(_minify(f"""
        <tr>
          <td class="lvl"><span class="dot"></span><b>{r['label']}</b></td>
          <td class="col-date">{r['planned']}</td>
          <td class="col-date">{r['forecast']}</td>
          <td class="col-bar">{_bar(r['schedule'],'blue', anim_variant)}</td>
          <td class="col-bar">{_bar(r['earned'],'green', anim_variant)}</td>
          <td class="col-sign">{sgn(r['ecart'])}</td>
          <td class="col-sign">{sgn(r['impact'])}</td>
          <td class="col-gliss"><span class='{"ok" if r["gliss"]>=0 else "bad"}'>{int(r["gliss"])}j</span></td>
        </tr>"""))
    st.markdown(_minify(f"""
    <div class="table-card compact">
      <div class="table-wrap">
        <table class="neo">
          <thead><tr>
            <th></th><th>Planned</th><th>Forecast</th><th>Schedule</th><th>Earned</th><th>Écart</th><th>Impact</th><th>Glissement</th>
          </tr></thead>
          <tbody>{''.join(trs)}</tbody>
        </table>
      </div>
    </div>
    """), unsafe_allow_html=True)

def render_barchart(node:dict, chart_key:str|None=None)->bool:
    labels=[]; schedule=[]; earned=[]
    for ch in (node.get("children") or []):
        labels.append(ch.get("label","")); m=ch.get("metrics") or {}
        schedule.append(_sf(m.get("schedule",0))); earned.append(_sf(m.get("earned",m.get("units",0))))
    if not labels: return False
    vmax=max([0]+schedule+earned); ymax=100 if vmax<=100 else math.ceil(vmax/5)*5
    c_text="#e5e7eb"; c_grid="rgba(42,59,98,.55)"; c_sched="#3b82f6"; c_earn="#22c55e"
    n=len(labels); idx=list(range(n)); d=0.16; w=0.26; gloss=0.45
    fig=go.Figure()
    fig.add_bar(name="Schedule %", x=[i-d for i in idx], y=[v*1.02 for v in schedule], width=w,
                marker=dict(color=c_sched), opacity=1, hoverinfo="skip", showlegend=False, cliponaxis=False)
    fig.add_bar(name="Schedule %", x=[i-d for i in idx], y=schedule, width=w,
                marker=dict(color=f"rgba(96,165,250,{gloss})", line=dict(color="#93c5fd", width=0.8)),
                text=[f"{v:.1f}%" for v in schedule], textposition="outside", textfont=dict(size=11, color=c_text),
                hovertemplate="<b>%{customdata}</b><br>Schedule: %{y:.2f}%<extra></extra>", customdata=labels, cliponaxis=False)
    fig.add_bar(name="Earned %", x=[i+d for i in idx], y=[v*1.02 for v in earned], width=w,
                marker=dict(color=c_earn), opacity=1, hoverinfo="skip", showlegend=False, cliponaxis=False)
    fig.add_bar(name="Earned %", x=[i+d for i in idx], y=earned, width=w,
                marker=dict(color=f"rgba(34,197,94,{gloss})", line=dict(color="#86efac", width=0.8)),
                text=[f"{v:.1f}%" for v in earned], textposition="outside", textfont=dict(size=11, color=c_text),
                hovertemplate="<b>%{customdata}</b><br>Earned: %{y:.2f}%<extra></extra>", customdata=labels, cliponaxis=False)
    shapes=[]
    if ymax==100: shapes.append(dict(type="line", xref="paper", x0=0, x1=1, y0=100, y1=100, line=dict(width=1, dash="dot", color=c_grid)))
    fig.update_xaxes(type="linear", tickmode="array", tickvals=idx, ticktext=labels,
                     tickfont=dict(size=12, color=c_text), range=[-0.6, n-0.4], showgrid=False, zeroline=False)
    fig.update_layout(barmode="overlay", bargap=0.3, height=300, margin=dict(l=8,r=18,t=6,b=44),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(size=12, color=c_text),
        legend=dict(orientation="h", y=-0.28, x=0.5, xanchor="center", itemclick=False, itemdoubleclick=False,
                    font=dict(size=11, color="#cbd5e1")),
        yaxis=dict(title="", range=[0, ymax*1.08], ticksuffix="%", dtick=25 if ymax==100 else None,
                   showgrid=True, gridcolor=c_grid, zeroline=False),
        hovermode="closest", hoverlabel=dict(bgcolor="#0f172a", font=dict(color=c_text, size=11)), shapes=shapes)
    element_key = chart_key or f"plt_{len(labels)}"
    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "displaylogo": False,
            "displayModeBar": "hover",
            "modeBarButtonsToRemove": [
                "select2d", "lasso2d", "autoScale2d",
                "zoomIn2d", "zoomOut2d", "toggleSpikelines"
            ],
            "responsive": True,
        },
        key=element_key,
    )
    return True


def _h1(label, m, anim_variant:int=0):
    planned  = m.get("planned_finish",""); forecast = m.get("forecast_finish","")
    sched_v  = _sf(m.get("schedule",0)); earn_v = _sf(m.get("earned",m.get("units",0)))
    ecart_v  = _sf(m.get("ecart",0)); impact_v=_sf(m.get("impact",0))
    gl=_to_j(m.get("glissement","0")); ecls="ok" if ecart_v>=0 else "bad"; icls="ok" if impact_v>=0 else "bad"; gcls="ok" if gl>=0 else "bad"
    return _minify(f"""
    <div class="hero compact">
      <div class="n1-grid">
        <div class="n1g-label"><span class="dot"></span><span class="title">{label}</span></div>
        <div class="n1g-cell"><span class="small">Planned</span><b>{planned}</b></div>
        <div class="n1g-cell"><span class="small">Forecast</span><b>{forecast}</b></div>
        <div class="n1g-cell"><span class="small">Schedule</span>{_bar(sched_v,'blue', anim_variant)}</div>
        <div class="n1g-cell"><span class="small">Earned</span>{_bar(earn_v,'green', anim_variant)}</div>
        <div class="n1g-cell"><span class="small">Écart</span><b class="{ecls}">{_pct(ecart_v,True)}</b></div>
        <div class="n1g-cell"><span class="small">Impact</span><b class="{icls}">{_pct(impact_v,True)}</b></div>
        <div class="n1g-cell"><span class="small">Glissement</span><b class="{gcls}">{int(gl)}j</b></div>
      </div>
    </div>""")

def _h2(label, level, m, anim_variant:int=0):
    planned  = m.get("planned_finish",""); forecast = m.get("forecast_finish","")
    sched_v  = _sf(m.get("schedule",0)); earn_v = _sf(m.get("earned",m.get("units",0)))
    ecart_v  = _sf(m.get("ecart",0)); impact_v=_sf(m.get("impact",0))
    gl=_to_j(m.get("glissement","0")); ecls="ok" if ecart_v>=0 else "bad"; icls="ok" if impact_v>=0 else "bad"; gcls="ok" if gl>=0 else "bad"
    return _minify(f"""
    <div class="n2-grid compact">
      <div class="n2g-label"><span class="dot"></span><span class="title">{label}</span></div>
      <div class="n2g-cell"><span class="small">Planned</span><b>{planned}</b></div>
      <div class="n2g-cell"><span class="small">Forecast</span><b>{forecast}</b></div>
        <div class="n2g-cell"><span class="small">Schedule</span>{_bar(sched_v,'blue', anim_variant)}</div>
        <div class="n2g-cell"><span class="small">Earned</span>{_bar(earn_v,'green', anim_variant)}</div>
      <div class="n2g-cell"><span class="small">Écart</span><b class="{ecls}">{_pct(ecart_v,True)}</b></div>
      <div class="n2g-cell"><span class="small">Impact</span><b class="{icls}">{_pct(impact_v,True)}</b></div>
      <div class="n2g-cell gliss"><span class="small">Glissement</span><b class="{gcls}">{int(gl)}j</b></div>
    </div>""")

def _slug(s:str)->str: return "".join(ch if ch.isalnum() else "_" for ch in s)

def render_section_level2(node:dict, anim_seq:int=0, wbs_key:str="wbs", debug:bool=False):
    label=node.get("label",""); level=node.get("level",2); metrics=node.get("metrics") or {}
    has_children=bool(node.get("children"))
    base=f"n2_open--{_slug(label)}_{level}__{wbs_key}"; ver_key=f"{base}__ver"
    view_version = (anim_seq + st.session_state.get(ver_key, 0)) % 2
    if base not in st.session_state: st.session_state[base]=False
    if ver_key not in st.session_state: st.session_state[ver_key]=0
    bar_variant = anim_seq % 2
    l, r = st.columns([0.985, 0.015], gap="small")
    with l:
        st.markdown(_h2(label,level,metrics, bar_variant), unsafe_allow_html=True)
        if has_children:
            if st.button(" ", key=f"{base}__rowbtn", use_container_width=True):
                st.session_state[base]=not st.session_state[base]; st.session_state[ver_key]+=1
    if debug:
        st.caption(f"[dbg] base={base} open={st.session_state.get(base)} ver={st.session_state.get(ver_key)} view={view_version} anim_seq={anim_seq}")
    if has_children and st.session_state[base]:
        with st.container(key=f"{base}__mount_{anim_seq%2}_{st.session_state[ver_key]%2}"):
            with st.expander("", expanded=True):
                st.markdown(f'<div class="n3load v{view_version}"></div>', unsafe_allow_html=True)
                render_detail_table(node, anim_variant=view_version)
                render_barchart(node, chart_key=f"{base}__chart_v{view_version}")


def render_all(root:dict, anim_seq:int=0, wbs_key:str="wbs", debug:bool=False):
    with st.container(key=f"hero_wrap__{anim_seq%2}"):
        st.markdown(_h1(root.get("label","GLOBAL"), root.get("metrics",{}) or {}, anim_seq%2), unsafe_allow_html=True)
    st.divider()
    for n2 in root.get("children",[]) or []: render_section_level2(n2, anim_seq, wbs_key, debug=debug)

# ===== Sidebar: importer (inchangé) =====
with st.sidebar:
    st.header("📁 Import Excel")
    uploaded = st.file_uploader("Importer un fichier Excel (.xlsx)", type=["xlsx","xlsm"], accept_multiple_files=False)
    debug_remount = False
    packs=[]
    if uploaded is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            tmp.write(uploaded.read()); tmp_path=tmp.name
        try:
            packs=extract_all_wbs(tmp_path); st.session_state["_packs"]=packs
            if not packs: st.warning("Aucun tableau valide détecté.")
        except Exception as e:
            st.error(f"Erreur d’extraction: {e}")
        finally:
            try: os.unlink(tmp_path)
            except: pass

# ===== Page layout: FULL content + fixed right panel =====
# (à mettre APRÈS la définition de render_all(...) et APRÈS le bloc with st.sidebar)



packs = st.session_state.get("_packs", [])
if not packs:
    st.info("Importe un Excel dans la barre de gauche.")
    st.stop()

# Permet de forcer le remount des blocs animés lorsque l'on change de WBS
st.session_state.setdefault("_anim_seq", 0)
st.session_state.setdefault("_active_ctx", "")
st.session_state.setdefault("_idx_prev", -1)

labels = [f"{i+1}. {p.get('wbs',{}).get('label','WBS')}" for i,p in enumerate(packs)]
idx = st.radio(
    "WBS à afficher",
    options=range(len(labels)),
    format_func=lambda i: labels[i],
    index=0,
    label_visibility="collapsed",
    key="wbs_selector_onpage"
)
wbs_idx = idx
sel = packs[wbs_idx]
root = sel["wbs"]
wbs_key = _slug(sel.get("sheet","sheet")) + "__" + _slug(sel.get("range","range")) + "__" + _slug(root.get("label","wbs")) + f"__{wbs_idx}"
if st.session_state["_active_ctx"] != wbs_key or st.session_state["_idx_prev"] != wbs_idx:
    st.session_state["_anim_seq"] += 1
    st.session_state["_active_ctx"] = wbs_key
st.session_state["_idx_prev"] = wbs_idx

if debug_remount:
    st.sidebar.caption(f"[dbg] anim_seq={st.session_state['_anim_seq']} active_ctx={st.session_state['_active_ctx']} idx_prev={st.session_state['_idx_prev']}")
with st.container(key="glass_wrap"):
    with st.container(key=f"anim_wrap__{st.session_state['_anim_seq']%2}"):
        render_all(root, st.session_state["_anim_seq"], wbs_key, debug=debug_remount)
