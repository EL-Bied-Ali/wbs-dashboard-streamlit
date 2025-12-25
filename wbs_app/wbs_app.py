# app.py - Sidebar conservee / boutons deplaces a droite (compact)
import streamlit as st
import plotly.graph_objects as go
from theme import inject_theme
from extract_wbs_json import extract_all_wbs, detect_expected_tables, compare_activity_ids, build_preview_rows
import tempfile, os, math
from pathlib import Path

st.set_page_config(page_title="WBS - Projet", layout="wide", initial_sidebar_state="expanded")
inject_theme()
# Inject background glows only once to avoid flash on rerender
if not st.session_state.get("_wbs_bg_once"):
    st.markdown("""
    <div class="bg-vignette"></div>
    <div class="bg-aurora a1"></div>
    <div class="bg-aurora a2"></div>
    <div class="bg-aurora grid"></div>
    """, unsafe_allow_html=True)
    st.session_state["_wbs_bg_once"] = True

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
    base_level=int(node.get("level", 2))

    def _collect_rows(parent:dict):
        for ch in (parent.get("children") or []):
            m=ch.get("metrics") or {}
            lvl=int(ch.get("level", base_level + 1))
            depth=max(0, lvl - base_level)
            depth_display = min(depth, 6)
            rows.append(dict(
                label=ch.get("label",""),
                planned=m.get("planned_finish",""),
                forecast=m.get("forecast_finish",""),
                schedule=_sf(m.get("schedule",0)),
                earned=_sf(m.get("earned",m.get("units",0))),
                ecart=_sf(m.get("ecart",0)),
                impact=_sf(m.get("impact",0)),
                gliss=_to_j(m.get("glissement","0")),
                depth=depth_display,
            ))
            _collect_rows(ch)

    _collect_rows(node)
    def sgn(v): 
        cls="ok" if v>=0 else "bad"
        return f'<span class="{cls}">{("+" if v>0 else "")}{v:.2f}%</span>'
    trs=[]
    for r in rows:
        trs.append(_minify(f"""
        <tr class="depth-{r['depth']}">
          <td class="lvl depth-{r['depth']}" style="--indent:{r['depth']};"><span class="indent"><span class="dot"></span><span class="label">{r['label']}</span></span></td>
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
            <th></th><th>Planned</th><th>Forecast</th><th>Schedule</th><th>Earned</th><th>+Ecart</th><th>Impact</th><th>Glissement</th>
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
        width="stretch",
        config={
            "displaylogo": False,
            "displayModeBar": "hover",
            "modeBarButtonsToRemove": [
                "select2d", "lasso2d", "autoScale2d",
                "zoomIn2d", "zoomOut2d", "toggleSpikelines"
            ],
            "responsive": False,
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
        <div class="n1g-cell"><span class="small">+Ecart</span><b class="{ecls}">{_pct(ecart_v,True)}</b></div>
        <div class="n1g-cell"><span class="small">Impact</span><b class="{icls}">{_pct(impact_v,True)}</b></div>
        <div class="n1g-cell"><span class="small">Glissement</span><b class="{gcls}">{int(gl)}j</b></div>
      </div>
    </div>""")

def _h2(label, level, m, anim_variant:int=0):
    planned  = m.get("planned_finish",""); forecast = m.get("forecast_finish","")
    sched_v  = _sf(m.get("schedule",0)); earn_v = _sf(m.get("earned",m.get("units",0)))
    ecart_v  = _sf(m.get("ecart",0)); impact_v=_sf(m.get("impact",0))
    gl=_to_j(m.get("glissement","0")); ecls="ok" if ecart_v>=0 else "bad"; icls="ok" if impact_v>=0 else "bad"; gcls="ok" if gl>=0 else "bad"
    indent = max(0, int(level) - 2) * 16
    return _minify(f"""
    <div class="n2-grid compact depth-{level}" style="margin-left:{indent}px;">
      <div class="n2g-label"><span class="dot"></span><span class="title">{label}</span></div>
      <div class="n2g-cell"><span class="small">Planned</span><b>{planned}</b></div>
      <div class="n2g-cell"><span class="small">Forecast</span><b>{forecast}</b></div>
        <div class="n2g-cell"><span class="small">Schedule</span>{_bar(sched_v,'blue', anim_variant)}</div>
        <div class="n2g-cell"><span class="small">Earned</span>{_bar(earn_v,'green', anim_variant)}</div>
      <div class="n2g-cell"><span class="small">+Ecart</span><b class="{ecls}">{_pct(ecart_v,True)}</b></div>
      <div class="n2g-cell"><span class="small">Impact</span><b class="{icls}">{_pct(impact_v,True)}</b></div>
      <div class="n2g-cell gliss"><span class="small">Glissement</span><b class="{gcls}">{int(gl)}j</b></div>
    </div>""")

def _slug(s:str)->str: return "".join(ch if ch.isalnum() else "_" for ch in s)
def _node_base(label:str, depth:int, wbs_key:str, path:list[str])->str:
    full = "__".join(_slug(p) for p in (path + [label]) if p)
    return f"n2_open--{full}_{depth}__{wbs_key}"

def render_node(node:dict, depth:int, anim_seq:int=0, wbs_key:str="wbs", debug:bool=False, path:list[str]|None=None):
    path = path or []
    label=node.get("label",""); level=int(node.get("level", depth)); metrics=node.get("metrics") or {}
    children = node.get("children") or []
    has_children=bool(children)
    base=_node_base(label, depth, wbs_key, path); ver_key=f"{base}__ver"
    view_version = (anim_seq + st.session_state.get(ver_key, 0)) % 2
    if base not in st.session_state:
        st.session_state[base] = True if depth == 1 else False
    if ver_key not in st.session_state: st.session_state[ver_key]=0
    bar_variant = (anim_seq + depth) % 2
    if depth == 1:
        st.markdown(_h1(label, metrics, bar_variant), unsafe_allow_html=True)
    else:
        with st.container(key=f"{base}__rowwrap"):
            st.markdown(_h2(label,level,metrics, bar_variant), unsafe_allow_html=True)
            if has_children:
                if st.button(" ", key=f"{base}__rowbtn", width="stretch"):
                    st.session_state[base]=not st.session_state[base]; st.session_state[ver_key]+=1
    if debug:
        st.caption(f"[dbg] base={base} open={st.session_state.get(base)} ver={st.session_state.get(ver_key)} view={view_version} anim_seq={anim_seq}")
    open_self = True if depth == 1 else bool(st.session_state.get(base, False))
    next_path = path + [label]
    if has_children and open_self:
        for child in children:
            render_node(child, depth+1, anim_seq, wbs_key, debug=debug, path=next_path)
        child_open = any(
            st.session_state.get(_node_base(ch.get("label",""), depth + 1, wbs_key, next_path), False)
            for ch in children
        )
        show_summary_chart = len(children) > 1 and not child_open
        if show_summary_chart and depth >= 1:
            with st.container(key=f"{base}__chartwrap_v{view_version}"):
                render_barchart(node, chart_key=f"{base}__chart")


def render_all(root:dict, anim_seq:int=0, wbs_key:str="wbs", debug:bool=False):
    with st.container(key=f"hero_wrap__{anim_seq%2}"):
        render_node(root, 1, anim_seq, wbs_key, debug=debug)
    st.divider()

# ===== Sidebar: importer (unchanged) =====
st.sidebar.markdown('<div class="sidebar-nav-title">Navigation</div>', unsafe_allow_html=True)
st.sidebar.page_link("app.py", label="📊 Project Progress")
st.sidebar.page_link("pages/2_WBS.py", label="🧱 WBS")

with st.sidebar:
    use_test = st.toggle(
        "Use test Excel (artifacts/W_example.xlsx)",
        value=True,
        key="use_test_excel",
    )
    uploaded = st.file_uploader("📁 Upload WBS data (.xlsx)", type=["xlsx","xlsm"], accept_multiple_files=False)
    debug_remount = False
    packs = []
    source_path = None
    tmp_path = None
    test_path = Path("artifacts/W_example.xlsx")
    if use_test:
        if test_path.exists():
            source_path = str(test_path)
        else:
            st.info("Test file not found at artifacts/W_example.xlsx.")
    elif uploaded is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            tmp.write(uploaded.read()); tmp_path = tmp.name
        source_path = tmp_path

    if source_path:
        try:
            packs = extract_all_wbs(source_path)
            st.session_state["_packs"] = packs
            st.session_state["_detected_tables"] = []
            if not packs:
                st.session_state["_detected_tables"] = detect_expected_tables(source_path)
            st.session_state["_table_mismatch"] = compare_activity_ids(source_path)
            st.session_state["_preview_rows"] = build_preview_rows(source_path)
        except Exception as e:
            st.error(f"Erreur d'extraction: {e}")
        finally:
            if tmp_path:
                try: os.unlink(tmp_path)
                except: pass

packs = st.session_state.get("_packs", [])
detected_tables = st.session_state.get("_detected_tables", [])
mismatch = st.session_state.get("_table_mismatch")
if mismatch and (mismatch.get("summary_only") or mismatch.get("assign_only")):
    st.warning(
        "Activity ID mismatch between the two tables. "
        f"Summary unique: {mismatch.get('summary_unique', 0)} | "
        f"Assignments unique: {mismatch.get('assign_unique', 0)}. "
        "They should contain the same unique IDs."
    )
    if mismatch.get("summary_only"):
        sample = ", ".join(mismatch["summary_only"][:10])
        st.markdown(f"- Only in summary: {sample}")
    if mismatch.get("assign_only"):
        sample = ", ".join(mismatch["assign_only"][:10])
        st.markdown(f"- Only in assignments: {sample}")
preview_mode = st.sidebar.toggle("Preview mode (dev)", value=True, key="preview_mode")
if preview_mode:
    st.markdown("### Preview (mapping checks)")
    st.markdown("Source for hierarchy: Ressource Assignments (Activity ID indentation).")
    preview_rows = st.session_state.get("_preview_rows", [])
    if detected_tables:
        st.markdown("Detected tables:")
        for t in detected_tables:
            missing = ", ".join(t.get("missing", [])) or "none"
            st.markdown(f"- {t['type']} | sheet {t['sheet']} | {t['range']} | missing: {missing}")
    if mismatch and (mismatch.get("summary_only") or mismatch.get("assign_only")):
        st.markdown(
            f"Mismatch summary: summary={mismatch.get('summary_unique', 0)} "
            f"assignments={mismatch.get('assign_unique', 0)}"
        )
    if not preview_rows:
        st.info("No preview rows yet. Upload a file or enable the test Excel toggle.")
        st.stop()

    import hashlib
    import random
    from datetime import date, timedelta

    def _rng(key: str) -> random.Random:
        seed = int.from_bytes(hashlib.md5(key.encode("utf-8")).digest()[:4], "little")
        return random.Random(seed)

    def _rand_date(r: random.Random) -> str:
        base = date(2025, 1, 1)
        return (base + timedelta(days=r.randint(0, 330))).strftime("%d-%b-%y")

    def _preview_metrics(label: str) -> dict:
        rng = _rng(label)
        schedule = round(rng.uniform(0, 100), 2)
        earned = round(max(0, min(100, schedule + rng.uniform(-15, 15))), 2)
        return {
            "planned_finish": _rand_date(rng),
            "forecast_finish": _rand_date(rng),
            "schedule": schedule,
            "earned": earned,
            "ecart": round(earned - schedule, 2),
            "impact": round(rng.uniform(-10, 10), 2),
            "glissement": f"{rng.randint(-7, 7)}j",
        }

    def _build_preview_tree(rows: list[dict]) -> dict:
        min_level = min(r.get("level", 0) for r in rows)
        root = None
        stack = []
        for r in rows:
            lvl = (r.get("level", 0) - min_level) + 1
            node = {
                "label": r["label"],
                "level": lvl,
                "metrics": _preview_metrics(r["label"]),
                "children": [],
            }
            if root is None:
                root = node
                stack = [node]
                continue
            while stack and stack[-1]["level"] >= lvl:
                stack.pop()
            if not stack:
                root.setdefault("children", []).append(node)
                stack = [root, node]
            else:
                stack[-1]["children"].append(node)
                stack.append(node)
        return root or {}

    root = _build_preview_tree(preview_rows)
    if not root:
        st.info("No preview tree available.")
        st.stop()
    st.caption("Preview uses placeholder metrics until we map real values.")
    st.session_state.setdefault("_preview_anim_seq", 0)
    render_all(root, st.session_state["_preview_anim_seq"], wbs_key="preview", debug=False)
    st.info("Disable preview in the sidebar to render the WBS.")
    st.stop()

if not packs:
    if detected_tables:
        st.info("Tables detectees, mais format incomplet pour la generation WBS.")
        for t in detected_tables:
            missing = ", ".join(t.get("missing", [])) or "none"
            st.markdown(f"- {t['type']} | sheet {t['sheet']} | {t['range']} | missing: {missing}")
    else:
        st.info("📥 Importe un Excel dans la barre de gauche.")
    st.stop()

# Permet de forcer le remount des blocs animes lorsque l'on change de WBS
st.session_state.setdefault("_anim_seq", 0)
st.session_state.setdefault("_active_ctx", "")
st.session_state.setdefault("_idx_prev", -1)

labels = [f"{i+1}. 🧱 {p.get('wbs',{}).get('label','WBS')}" for i,p in enumerate(packs)]
with st.sidebar:
    if len(labels) > 1:
        idx = st.radio(
            "WBS a afficher",
            options=range(len(labels)),
            format_func=lambda i: labels[i],
            index=0,
            key="wbs_selector_sidebar"
        )
    else:
        idx = 0
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
