# ui.py - theming + reusable UI kit (auto dark/light)
import streamlit as st
from textwrap import dedent

def inject_theme():
    css = """
    <style>
      :root{
        --bg:#0d1330;
        --card:#161d3a;
        --border:rgba(255,255,255,0.08);
        --text:#e8eefc;
        --muted:#9da8c6;
        --accent:#e9c75f;
        --accent-2:#2fc192;
        --accent-3:#4b6ff4;
        --danger:#f97070;
        --radius:14px;
        --shadow:0 16px 40px rgba(0,0,0,0.45);
      }
      body, [data-testid="stAppViewContainer"], .main{
        background:var(--bg);
        color:var(--text);
        font-family: 'Inter','Segoe UI',sans-serif;
        font-size:16px;
      }
      .block-container{ padding:18px 24px 40px 24px; }
      header,[data-testid="stToolbar"]{ background:transparent !important; }
      [data-testid="stSidebar"]{ background:var(--bg) !important; }

      .card{
        background:var(--card);
        border:1px solid var(--border);
        border-radius:var(--radius);
        box-shadow:var(--shadow);
        padding:10px 12px;
      }
      .chart-card{ padding:8px 10px; overflow:hidden; }
      .chart-heading{ font-size:16px; font-weight:700; color:var(--text); margin:0 0 8px 0; }
      div[data-testid="stVerticalBlock"]:has(.chart-heading){
        background:var(--card);
        border:1px solid var(--border);
        border-radius:var(--radius);
        box-shadow:var(--shadow);
        padding:0;
        overflow:hidden;
      }
      div[data-testid="stVerticalBlock"]:has(.chart-heading) .chart-heading{
        padding:12px 14px 4px 14px;
      }
      div[data-testid="stVerticalBlock"]:has(.chart-heading) .stPlotlyChart{
        padding:0 12px 12px 12px;
        box-sizing:border-box;
      }
      /* Allow metric cards to size naturally (no inner scroll) */
      div[data-testid="stElementContainer"]:has(.card.metric){
        overflow: visible !important;
        height: auto !important;
      }
      /* Keep Plotly containers managed by Streamlit sizing but no inner scroll */
      div[data-testid="stElementContainer"]:has(.stPlotlyChart){
        overflow: visible !important;
      }
      /* Lock Plotly chart containers to their assigned heights to prevent growth */
      div[data-testid="stElementContainer"][height="260px"]:has(.stPlotlyChart){
        height: 260px !important;
        max-height: 260px !important;
      }
      div[data-testid="stElementContainer"][height="280px"]:has(.stPlotlyChart){
        height: 280px !important;
        max-height: 280px !important;
      }
      div[data-testid="stElementContainer"][height="300px"]:has(.stPlotlyChart){
        height: 300px !important;
        max-height: 300px !important;
      }
      div[data-testid="stElementContainer"][height="330px"]:has(.stPlotlyChart){
        height: 330px !important;
        max-height: 330px !important;
      }
      div[data-testid="stElementContainer"][height="520px"]:has(.stPlotlyChart){
        height: 520px !important;
        max-height: 520px !important;
      }
      div[data-testid="stElementContainer"][height="260px"]:has(.stPlotlyChart) .stPlotlyChart,
      div[data-testid="stElementContainer"][height="280px"]:has(.stPlotlyChart) .stPlotlyChart,
      div[data-testid="stElementContainer"][height="300px"]:has(.stPlotlyChart) .stPlotlyChart,
      div[data-testid="stElementContainer"][height="330px"]:has(.stPlotlyChart) .stPlotlyChart,
      div[data-testid="stElementContainer"][height="520px"]:has(.stPlotlyChart) .stPlotlyChart{
        height: 100% !important;
      }
      div[data-testid="stElementContainer"][height="260px"]:has(.stPlotlyChart) .js-plotly-plot,
      div[data-testid="stElementContainer"][height="280px"]:has(.stPlotlyChart) .js-plotly-plot,
      div[data-testid="stElementContainer"][height="300px"]:has(.stPlotlyChart) .js-plotly-plot,
      div[data-testid="stElementContainer"][height="330px"]:has(.stPlotlyChart) .js-plotly-plot,
      div[data-testid="stElementContainer"][height="520px"]:has(.stPlotlyChart) .js-plotly-plot{
        height: 100% !important;
      }
      .metric{
        display:flex;
        flex-direction:column;
        gap:4px;
        min-height:96px;
      }
      .metric .label{ color:var(--muted); font-weight:600; font-size:15px; letter-spacing:0.1px; }
      .metric .value{ color:var(--text); font-weight:800; font-size:28px; }
      .metric .value.positive{ color:var(--accent-2); }
      .metric .value.warn{ color:var(--accent); }
      .metric .value.negative{ color:var(--danger); }
      .metric .sub{ color:var(--muted); font-size:12px; }

      .page-header{ display:flex; flex-direction:column; gap:2px; margin:12px 8px 18px 8px; padding:0 4px; }
      .page-header .title{ font-size:22px; font-weight:800; color:var(--text); }
      .muted{ color:var(--muted); font-size:14px; }

      /* Prevent plotly overflow */
      .stPlotlyChart, .js-plotly-plot, .plot-container{ width:100% !important; max-width:100% !important; }
      .js-plotly-plot .main-svg{ width:100% !important; }

      .app-bg{
        position:fixed; inset:0; pointer-events:none; z-index:-1;
        background:
          radial-gradient(900px 600px at 10% -10%, rgba(75,111,244,.18), transparent 40%),
          radial-gradient(900px 600px at 90% 20%, rgba(47,193,146,.14), transparent 45%),
          var(--bg);
      }

      /* Responsive tweaks: let Streamlit columns wrap/stack on narrow viewports */
      div[data-testid="stHorizontalBlock"]{
        flex-wrap: wrap;
        gap: 12px;
      }
      /* Prevent inner scrollbars on gauge + metric rows */
      div[data-testid="stHorizontalBlock"]:has(.stPlotlyChart),
      div[data-testid="stHorizontalBlock"]:has(.card.metric){
        overflow: visible !important;
        height: auto !important;
      }
      div[data-testid="stColumn"]{
        min-width: 320px;
        flex: 1 1 320px !important;
      }
      /* Left sidebar: larger nav + labels, custom names with emojis */
      section[data-testid="stSidebar"]{
        font-size: 20px;
      }
      section[data-testid="stSidebar"] [data-testid="stSidebarNav"]{
        display: none !important;
      }
      section[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]{
        font-size: 28px !important;
        font-weight: 800;
        line-height: 1.1;
        display: block;
        padding: 4px 0 !important;
      }
      section[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] [data-testid="stMarkdownContainer"] p{
        font-size: 28px !important;
        font-weight: 800;
        line-height: 1.1;
        margin: 0 !important;
      }
      section[data-testid="stSidebar"] .sidebar-nav-title{
        font-size: 34px !important;
        font-weight: 800;
        line-height: 1.1;
        margin: 0 0 8px 0;
      }
      section[data-testid="stSidebar"] [data-testid="stPageLink"]{
        margin: 2px 0 6px 0 !important;
      }
      section[data-testid="stSidebar"] [data-testid="stElementContainer"]:has([data-testid="stPageLink"]){
        margin: 0 !important;
        padding: 0 !important;
      }
      section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p{
        font-size: 22px;
        font-weight: 700;
      }
      section[data-testid="stSidebar"] .stRadio [data-testid="stMarkdownContainer"] p{
        font-size: 22px;
      }
      @media (max-width: 900px){
        div[data-testid="stColumn"]{
          min-width: 260px;
          flex: 1 1 260px !important;
        }
      }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
    st.markdown('<div class="app-bg"></div>', unsafe_allow_html=True)


def page_header(title:str, right=None):
    st.markdown(f"""
      <div class="glass card fade-in">
        <div style="display:flex; align-items:center; justify-content:space-between; gap:12px;">
          <div class="title" style="font-size:22px;">{title}</div>
          <div class="toolbar">{right or ""}</div>
        </div>
      </div>
    """, unsafe_allow_html=True)

def badge(text:str, color:str="accent"):
    dot = {"accent":"var(--accent)","success":"var(--accent-2)",
           "warn":"var(--warn)","danger":"var(--danger)","muted":"var(--muted)"}[color]
    return f'<span class="badge"><span style="width:8px;height:8px;border-radius:999px;background:{dot};display:inline-block"></span>{text}</span>'

def card(title:str, body_html:str, right=None):
    st.markdown(f"""
      <div class="glass card fade-in">
        <div style="display:flex; align-items:flex-start; justify-content:space-between;">
          <div class="title" style="font-size:16px">{title}</div>
          <div class="toolbar">{right or ""}</div>
        </div>
        <div style="margin-top:8px">{body_html}</div>
      </div>
    """, unsafe_allow_html=True)

def stat(label:str, value:str, sub:str=""):
    st.markdown(f"""
      <div class="glass card fade-in">
        <div class="stat"><div class="val">{value}</div><div class="muted">{label}</div></div>
        <div class="muted" style="margin-top:6px">{sub}</div>
      </div>
    """, unsafe_allow_html=True)

def grid_start(cols12:bool=True):
    st.markdown(f'<div class="grid {"cols-12" if cols12 else ""}">', unsafe_allow_html=True)

def grid_end():
    st.markdown('</div>', unsafe_allow_html=True)

def sidebar_rcv_buttons(options, key_prefix:str, title="RCV / Lots / Sous Lots"):
    # unchanged: keep your existing implementation if you had one, otherwise simple select
    st.markdown(f"<div class='muted' style='font-weight:700;margin-bottom:6px'>{title}</div>", unsafe_allow_html=True)
    return st.selectbox("", ["__ALL__"] + list(options), index=0, key=f"{key_prefix}_rcv")

def kpi_group(items):
    # items: list of dicts {label, value, sub}
    st.markdown('<div class="kpi-rail fade-in">', unsafe_allow_html=True)
    cols = st.columns(len(items))
    for i, it in enumerate(items):
        with cols[i]:
            stat(it["label"], it["value"], it.get("sub",""))
    st.markdown('</div>', unsafe_allow_html=True)
    
import plotly.graph_objects as go

def gauge(title: str, value: float):
    v = max(0, min(100, float(value or 0)))
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=v,
        number={"font":{"size":36}},
        title={"text": title, "font":{"size":14}},
        gauge={
            "axis":{"range":[0,100], "tickwidth":1},
            "bar":{"color":"#16a34a", "thickness":0.35},
            "bgcolor":"rgba(255,255,255,0.02)",
            "borderwidth":0,
            "steps":[
                {"range":[0,50], "color":"rgba(22,163,74,.15)"},
                {"range":[50,80], "color":"rgba(34,197,94,.12)"},
                {"range":[80,100], "color":"rgba(59,130,246,.12)"},
            ],
            "shape":"angular"
        }
    ))
    fig.update_layout(height=220, margin=dict(l=10,r=10,t=30,b=10))
    return fig
    
def kpi_chip(label:str, value:str, sub:str=""):
    return f"""
      <div class="chip">
        <div class="val">{value}</div>
        <div class="lab">{label}</div>
        <div class="sub">{sub}</div>
      </div>
    """

def kpi_chip_row(items):
    html = '<div class="chip-row">'
    for it in items:
        html += kpi_chip(it["label"], str(it["value"]), it.get("sub",""))
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)








