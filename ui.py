# ui.py - theming + reusable UI kit (auto dark/light)
import streamlit as st
from textwrap import dedent

def inject_theme():
    anim_seq = st.session_state.get("_plotly_anim_seq", 0) + 1
    st.session_state["_plotly_anim_seq"] = anim_seq
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
        --ui-zoom:1;
      }
      @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

      body, [data-testid="stAppViewContainer"], .main{
        background:var(--bg);
        color:var(--text);
        font-family: 'DM Sans','Segoe UI',sans-serif;
        font-size:15px;
      }
      .block-container{ padding:18px 24px 40px 24px; }
      header,[data-testid="stToolbar"]{ background:transparent !important; }
      [data-testid="stSidebar"]{ background:var(--bg) !important; }

      .card{
        position: relative;
        --glow-height: min(55%, calc(2.8em + 32px));
        background: linear-gradient(180deg, rgba(22,29,58,.96), rgba(13,19,48,.92));
        border:1px solid var(--border);
        border-radius:var(--radius);
        box-shadow:var(--shadow);
        padding:10px 12px;
        overflow: hidden;
      }
      .card::before{
        content:"";
        position:absolute;
        inset:-12% -10% auto -10%;
        height:var(--glow-height);
        background:
          radial-gradient(520px 240px at 12% 0%, rgba(75,111,244,.20), transparent 60%),
          radial-gradient(520px 240px at 88% 10%, rgba(47,193,146,.16), transparent 62%);
        opacity:.9;
        pointer-events:none;
      }
      .card > *{
        position: relative;
        z-index: 1;
      }
      .chart-card{ padding:8px 10px; overflow:hidden; }
      .chart-heading{ font-size:17px; font-weight:700; color:var(--text); margin:0 0 8px 0; font-family:'Space Grotesk','DM Sans',sans-serif; letter-spacing:0.2px; }
      div[data-testid="stVerticalBlock"]:has(.chart-heading){
        position: relative;
        --glow-height: min(55%, calc(2.8em + 32px));
        background: linear-gradient(180deg, rgba(22,29,58,.96), rgba(13,19,48,.92));
        border:1px solid var(--border);
        border-radius:var(--radius);
        box-shadow:var(--shadow);
        padding:0;
        overflow:hidden;
      }
      div[data-testid="stVerticalBlock"]:has(.chart-heading)::before{
        content:"";
        position:absolute;
        inset:-12% -10% auto -10%;
        height:var(--glow-height);
        background:
          radial-gradient(520px 240px at 12% 0%, rgba(75,111,244,.20), transparent 60%),
          radial-gradient(520px 240px at 88% 10%, rgba(47,193,146,.16), transparent 62%);
        opacity:.9;
        pointer-events:none;
      }
      div[data-testid="stVerticalBlock"]:has(.chart-heading) > *{
        position: relative;
        z-index: 1;
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
      .stPlotlyChart{
        animation: chartFadeUp__ANIM_SEQ__ 1400ms cubic-bezier(.22,.7,.2,1) both;
        animation-delay: 250ms;
        will-change: transform, opacity;
      }
      .stPlotlyChart .main-svg .trace .bars path{
        transform-origin: bottom;
        transform-box: fill-box;
        animation: barGrow__ANIM_SEQ__ 1400ms cubic-bezier(.22,.7,.2,1) both;
      }
      .stPlotlyChart .main-svg .trace .lines path{
        stroke-dasharray: 1200;
        stroke-dashoffset: 1200;
        animation: lineDraw__ANIM_SEQ__ 1800ms cubic-bezier(.22,.7,.2,1) both;
      }
      .stPlotlyChart .main-svg .trace .points path{
        transform-origin: center;
        transform-box: fill-box;
        animation: pointPop__ANIM_SEQ__ 1200ms cubic-bezier(.22,.7,.2,1) both;
      }
      .stPlotlyChart .main-svg .trace.pie path,
      .stPlotlyChart .main-svg .pie .slice path{
        transform-origin: center;
        transform-box: fill-box;
        animation: pieGrow__ANIM_SEQ__ 1400ms cubic-bezier(.22,.7,.2,1) both;
      }
      .stPlotlyChart .main-svg .pielayer .slice path.surface,
      .stPlotlyChart .main-svg .pielayer .slice path{
        transform-origin: center;
        transform-box: fill-box;
        animation: pieGrow__ANIM_SEQ__ 1400ms cubic-bezier(.22,.7,.2,1) both;
      }
      .stPlotlyChart .main-svg .pielayer .slicetext{
        animation: valuePop__ANIM_SEQ__ 1200ms cubic-bezier(.22,.7,.2,1) both;
      }
      .stPlotlyChart .main-svg .indicatorlayer .value-arc path{
        transform-origin: center;
        transform-box: fill-box;
        animation: gaugeSweep__ANIM_SEQ__ 1400ms cubic-bezier(.22,.7,.2,1) both;
      }
      .stPlotlyChart .main-svg .indicatorlayer .value-arc{
        transform-origin: center;
        transform-box: fill-box;
      }
      .stPlotlyChart .main-svg .trace.indicator path,
      .stPlotlyChart .main-svg .indicator path{
        transform-origin: center;
        transform-box: fill-box;
        animation: gaugeSweep__ANIM_SEQ__ 1400ms cubic-bezier(.22,.7,.2,1) both;
      }
      .stPlotlyChart .main-svg .trace.indicator text,
      .stPlotlyChart .main-svg .indicator text,
      .stPlotlyChart .main-svg .infolayer .annotation-text{
        animation: valuePop__ANIM_SEQ__ 1200ms cubic-bezier(.22,.7,.2,1) both;
      }
      @keyframes chartFadeUp__ANIM_SEQ__{
        from{ opacity:0; transform: translateY(10px) scale(0.995); }
        to{ opacity:1; transform: translateY(0) scale(1); }
      }
      @keyframes barGrow__ANIM_SEQ__{
        from{ transform: scaleY(0); }
        to{ transform: scaleY(1); }
      }
      @keyframes lineDraw__ANIM_SEQ__{
        to{ stroke-dashoffset: 0; }
      }
      @keyframes pointPop__ANIM_SEQ__{
        from{ opacity:0; transform: scale(0.3); }
        to{ opacity:1; transform: scale(1); }
      }
      @keyframes pieGrow__ANIM_SEQ__{
        from{ opacity:0; transform: scale(0.6); }
        to{ opacity:1; transform: scale(1); }
      }
      @keyframes gaugeSweep__ANIM_SEQ__{
        from{ opacity:0; transform: scaleX(0.2); }
        to{ opacity:1; transform: scaleX(1); }
      }
      @keyframes valuePop__ANIM_SEQ__{
        from{ opacity:0; transform: translateY(6px) scale(0.98); }
        to{ opacity:1; transform: translateY(0) scale(1); }
      }
      @media (prefers-reduced-motion: reduce){
        .stPlotlyChart{ animation: none !important; }
        .stPlotlyChart .main-svg .trace .bars path,
        .stPlotlyChart .main-svg .trace .lines path,
        .stPlotlyChart .main-svg .trace .points path,
        .stPlotlyChart .main-svg .trace.pie path,
        .stPlotlyChart .main-svg .pie .slice path,
        .stPlotlyChart .main-svg .pielayer .slice path.surface,
        .stPlotlyChart .main-svg .pielayer .slice path,
        .stPlotlyChart .main-svg .pielayer .slicetext,
        .stPlotlyChart .main-svg .indicatorlayer .value-arc path,
        .stPlotlyChart .main-svg .indicatorlayer .value-arc,
        .stPlotlyChart .main-svg .trace.indicator path,
        .stPlotlyChart .main-svg .indicator path,
        .stPlotlyChart .main-svg .trace.indicator text,
        .stPlotlyChart .main-svg .indicator text,
        .stPlotlyChart .main-svg .infolayer .annotation-text{
          animation: none !important;
        }
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

      .page-header-card{ margin:12px 8px 18px 8px; padding:12px 16px; }
      .page-header{ display:flex; flex-direction:column; gap:2px; margin:0; padding:0; }
      .page-header .title{ font-size:66px; font-weight:800; color:var(--text); font-family:'Space Grotesk','DM Sans',sans-serif; letter-spacing:0.3px; margin-top:2px; }
      .muted{ color:var(--muted); font-size:14px; }
      .page-header--brand{ flex-direction: column; gap: 6px; }
      .page-header--brand .page-header-main{ display:flex; flex-direction:column; gap:2px; }
      .page-header--brand .title-row{
        display:flex;
        align-items:center;
        justify-content:flex-start;
        gap: 16px;
        flex-wrap: wrap;
      }
      .page-header--brand .title-row .brand-strip{
        margin-left: 12px;
      }

      .brand-row{
        display:flex;
        justify-content:flex-end;
        margin: 6px 0 14px 0;
      }
      .brand-strip{
        display:flex;
        align-items:center;
        gap:8px;
      }
      .brand-pill{
        height:216px;
        min-width:216px;
        padding:6px 8px;
        border-radius:28px;
        border:1px solid rgba(148,163,184,.18);
        background: rgba(15,23,42,.55);
        box-shadow: 0 12px 26px rgba(0,0,0,.25);
        display:inline-flex;
        align-items:center;
        justify-content:center;
      }
      .brand-pill img{
        height:100%;
        width:auto;
        object-fit:contain;
      }
      .brand-strip--hero .brand-pill{
        height:252px;
        min-width:252px;
        padding:8px 12px;
        border-radius:32px;
      }
      .brand-strip--page .brand-pill{
        height:288px;
        min-width:288px;
        padding:8px 12px;
        border-radius:36px;
      }
      .brand-pill--header{
        height:288px;
        min-width:288px;
        padding:18px 18px 12px 18px;
        border-radius:36px;
      }

      div.st-key-brand_logo_row > div[data-testid="stHorizontalBlock"]{
        justify-content:flex-end;
        gap:12px;
        flex-wrap: nowrap;
      }
      div.st-key-brand_logo_row_scurve > div[data-testid="stHorizontalBlock"],
      div.st-key-brand_logo_row_wbs > div[data-testid="stHorizontalBlock"]{
        justify-content: flex-end;
        gap: 12px;
        flex-wrap: nowrap;
      }
      div.st-key-brand_logo_row div[data-testid="stColumn"]{
        flex: 0 0 auto !important;
        min-width: 0 !important;
      }
      div[class*="st-key-brand_logo_item_"]{
        position: relative;
        width: 288px;
        height: 288px;
        display: grid;
        grid-template-areas: "stack";
        align-items: center;
        justify-items: center;
      }
      div[class*="st-key-brand_logo_item_"] > div{
        grid-area: stack;
      }
      div[class*="st-key-brand_logo_item_"] .stButton{
        align-self: center;
        justify-self: center;
        z-index: 5;
        pointer-events: auto;
        margin: 0 !important;
      }
      div[class*="st-key-brand_logo_item_"] .stButton button{
        width: 44px;
        height: 44px;
        border-radius: 999px;
        border: 1px solid rgba(148,163,184,.45);
        background: rgba(10,14,26,.85);
        color: var(--text);
        font-weight: 900;
        font-size: 22px;
        line-height: 1;
        box-shadow: 0 6px 14px rgba(0,0,0,.25);
      }
      div[class*="st-key-brand_logo_item_"] .stButton button:hover{
        border-color: rgba(96,165,250,.7);
        background: rgba(23,35,60,.9);
        box-shadow: 0 10px 18px rgba(0,0,0,.35);
      }
      div[class*="st-key-brand_logo_item_"] .brand-pill{
        position: relative;
        z-index: 1;
        pointer-events: none;
      }
      .brand-label{
        font-size: 13px;
        font-weight: 700;
        color: var(--muted);
        margin: 4px 0 8px 0;
      }

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
      .app-bg::after{
        content:"";
        position:absolute;
        inset:-10%;
        background:
          radial-gradient(1200px 700px at 50% -10%, rgba(0,0,0,.35), transparent 60%),
          radial-gradient(900px 600px at 50% 120%, rgba(0,0,0,.45), transparent 60%);
        opacity:.55;
        pointer-events:none;
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
      /* Left sidebar: modern nav + pages */
      section[data-testid="stSidebar"]{
        font-size: 16px;
      }
      section[data-testid="stSidebar"] [data-testid="stSidebarNav"]{
        display: none !important;
      }
      section[data-testid="stSidebar"] .sidebar-nav-title{
        font-size: 12px !important;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.14em;
        color: rgba(157,168,198,.85);
        margin: 6px 0 10px 0;
      }
      section[data-testid="stSidebar"] [data-testid="stPageLink"]{
        margin: 6px 0 !important;
      }
      section[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]{
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 10px 12px !important;
        border-radius: 12px;
        border: 1px solid rgba(148,163,184,.18);
        background: rgba(15,23,42,.55);
        box-shadow: 0 10px 24px rgba(0,0,0,.25);
        font-size: 20px !important;
        font-weight: 700;
        line-height: 1.1;
        transition: border-color .2s ease, background .2s ease, box-shadow .2s ease;
      }
      section[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"][aria-current="page"]{
        border-color: rgba(75,111,244,.65);
        background: rgba(75,111,244,.18);
        box-shadow: 0 10px 26px rgba(18, 40, 110, .35);
      }
      section[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover{
        border-color: rgba(96,165,250,.5);
        background: rgba(30,41,59,.7);
      }
      section[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] [data-testid="stMarkdownContainer"] p{
        font-size: 20px !important;
        font-weight: 700;
        line-height: 1.1;
        margin: 0 !important;
      }
      section[data-testid="stSidebar"] [data-testid="stElementContainer"]:has([data-testid="stPageLink"]){
        margin: 0 !important;
        padding: 0 !important;
      }
      /* Sidebar auth card */
      section[data-testid="stSidebar"] div.st-key-auth_card{
        margin: 6px 0 18px 0;
        padding: 12px 54px 18px 12px;
        border-radius: 14px;
        background: linear-gradient(180deg, rgba(15,23,42,.72), rgba(11,18,36,.65));
        border: 1px solid rgba(148,163,184,.18);
        box-shadow: 0 12px 26px rgba(0,0,0,.28);
        position: relative;
      }
      section[data-testid="stSidebar"] div.st-key-auth_card [data-testid="column"]{
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
      }
      section[data-testid="stSidebar"] .auth-title{
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.14em;
        color: rgba(157,168,198,.85);
        margin-bottom: 8px;
      }
      section[data-testid="stSidebar"] .auth-row{
        display: flex;
        align-items: center;
        gap: 10px;
      }
      section[data-testid="stSidebar"] .auth-avatar{
        width: 38px;
        height: 38px;
        border-radius: 999px;
        object-fit: cover;
        border: 1px solid rgba(148,163,184,.3);
        box-shadow: 0 6px 14px rgba(0,0,0,.25);
      }
      section[data-testid="stSidebar"] .auth-avatar.placeholder{
        display: flex;
        align-items: center;
        justify-content: center;
        background: rgba(75,111,244,.18);
        color: var(--text);
        font-weight: 800;
      }
      section[data-testid="stSidebar"] .auth-meta{
        display: flex;
        flex-direction: column;
        gap: 2px;
      }
      section[data-testid="stSidebar"] .auth-name{
        font-size: 16px;
        font-weight: 800;
        color: var(--text);
      }
      section[data-testid="stSidebar"] .auth-email{
        font-size: 12px;
        color: var(--muted);
        word-break: break-word;
      }
      section[data-testid="stSidebar"] div.st-key-auth_card div.st-key-auth_logout_btn{
        position: absolute;
        top: 10px;
        right: 10px;
        margin: 0 !important;
        padding: 0 !important;
      }
      section[data-testid="stSidebar"] div.st-key-auth_card div.st-key-auth_logout_btn .stButton{
        display: flex;
        justify-content: flex-end;
      }
      section[data-testid="stSidebar"] div.st-key-auth_card div.st-key-auth_logout_btn .stButton button{
        width: 40px !important;
        height: 40px !important;
        min-width: 0 !important;
        padding: 0 !important;
        border-radius: 999px !important;
        border: 1px solid rgba(148,163,184,.3) !important;
        background: rgba(15,23,42,.7) !important;
        color: var(--text) !important;
        font-weight: 700 !important;
        font-size: 16px !important;
        line-height: 1 !important;
        box-shadow: inset 0 0 0 1px rgba(255,255,255,.04);
      }
      section[data-testid="stSidebar"] div.st-key-auth_card div.st-key-auth_logout_btn .stButton button:hover{
        border-color: rgba(96,165,250,.6) !important;
        background: rgba(30,41,59,.9) !important;
      }
      /* Sidebar branding card */
      section[data-testid="stSidebar"] div.st-key-brand_card{
        margin: 18px 0 0 0;
        padding: 12px;
        border-radius: 14px;
        background: linear-gradient(180deg, rgba(15,23,42,.72), rgba(11,18,36,.65));
        border: 1px solid rgba(148,163,184,.18);
        box-shadow: 0 12px 26px rgba(0,0,0,.28);
        margin-top: auto;
      }
      section[data-testid="stSidebar"] .brand-title{
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.14em;
        color: rgba(157,168,198,.85);
        margin-bottom: 10px;
      }
      section[data-testid="stSidebar"] .brand-note{
        font-size: 12px;
        color: var(--muted);
        margin: -2px 0 10px 0;
      }
      section[data-testid="stSidebar"] .brand-label{
        font-size: 12px;
        font-weight: 700;
        color: var(--muted);
        margin: 2px 0 6px 0;
      }
      section[data-testid="stSidebarContent"]{
        display: flex;
        flex-direction: column;
        height: 100%;
      }
      section[data-testid="stSidebarUserContent"]{
        flex: 1 1 auto;
        display: flex;
        flex-direction: column;
      }
      section[data-testid="stSidebarUserContent"] > div{
        flex: 1 1 auto;
        display: flex;
        flex-direction: column;
      }
      section[data-testid="stSidebarUserContent"] [data-testid="stVerticalBlock"]{
        flex: 1 1 auto;
        display: flex;
        flex-direction: column;
        height: 100%;
      }
      section[data-testid="stSidebar"] .sidebar-spacer{
        flex: 1 1 auto;
        min-height: 24px;
      }
      section[data-testid="stSidebar"] div[data-testid="stLayoutWrapper"]:has(.st-key-brand_card),
      section[data-testid="stSidebar"] div[data-testid="stElementContainer"]:has(.st-key-brand_card),
      section[data-testid="stSidebar"] .st-key-brand_card{
        order: 999;
        margin-top: auto !important;
      }
      section[data-testid="stSidebar"] .brand-preview{
        width: 100%;
        height: 64px;
        border-radius: 10px;
        border: 1px dashed rgba(148,163,184,.28);
        background: rgba(15,23,42,.55);
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
      }
      section[data-testid="stSidebar"] .brand-preview img{
        max-width: 100%;
        max-height: 100%;
        object-fit: contain;
      }
      section[data-testid="stSidebar"] .brand-preview.placeholder{
        color: var(--muted);
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.12em;
      }
      section[data-testid="stSidebar"] div.st-key-brand_card [data-testid="stFileUploader"]{
        margin-top: 8px;
      }
      section[data-testid="stSidebar"] div.st-key-brand_card [data-testid="stFileUploaderDropzone"]{
        padding: 6px 8px;
        min-height: 40px;
        border-radius: 10px;
      }
      section[data-testid="stSidebar"] div.st-key-brand_card [data-testid="stFileUploaderDropzoneInstructions"]{
        display: none;
      }
      section[data-testid="stSidebar"] div.st-key-brand_card [data-testid="stBaseButton-secondary"]{
        width: 100%;
      }
      section[data-testid="stSidebar"] .stRadio [data-testid="stWidgetLabel"] p{
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.14em;
        color: rgba(157,168,198,.85);
        margin: 12px 0 8px 0;
      }
      section[data-testid="stSidebar"] .stRadio [role="radiogroup"][aria-label="Pages"]{
        display: flex;
        flex-direction: column;
        gap: 6px;
      }
      section[data-testid="stSidebar"] .stRadio [role="radiogroup"][aria-label="Pages"] label[data-baseweb="radio"]{
        padding: 8px 12px;
        border-radius: 10px;
        border: 1px solid rgba(148,163,184,.16);
        background: rgba(15,23,42,.45);
        transition: border-color .2s ease, background .2s ease;
      }
      section[data-testid="stSidebar"] .stRadio [role="radiogroup"][aria-label="Pages"] label[data-baseweb="radio"] > div:first-child{
        display: none;
      }
      section[data-testid="stSidebar"] .stRadio [role="radiogroup"][aria-label="Pages"] label[data-baseweb="radio"]:has(input:checked){
        border-color: rgba(75,111,244,.55);
        background: rgba(75,111,244,.16);
      }
      section[data-testid="stSidebar"] .stRadio [role="radiogroup"][aria-label="Pages"] label[data-baseweb="radio"]:hover{
        border-color: rgba(96,165,250,.45);
        background: rgba(30,41,59,.6);
      }
      section[data-testid="stSidebar"] .stRadio [role="radiogroup"][aria-label="Pages"] [data-testid="stMarkdownContainer"] p{
        font-size: 18px;
        font-weight: 700;
        margin: 0;
      }
      section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p{
        font-size: 16px;
        font-weight: 700;
      }
      section[data-testid="stSidebar"] [data-testid="stSelectbox"]{
        background: rgba(15,23,42,.45);
        border: 1px solid rgba(148,163,184,.16);
        border-radius: 12px;
        padding: 8px 10px;
        box-shadow: 0 10px 22px rgba(0,0,0,.25);
      }
      section[data-testid="stSidebar"] [data-testid="stSelectbox"] [data-testid="stWidgetLabel"] p{
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.14em;
        color: rgba(157,168,198,.85);
        margin: 0 0 6px 0;
      }
      section[data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"]{
        background: transparent;
      }
      section[data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"] [value]{
        font-size: 16px;
        font-weight: 700;
        color: var(--text);
      }
      @media (max-width: 900px){
        div[data-testid="stColumn"]{
          min-width: 260px;
          flex: 1 1 260px !important;
        }
      }
    
      
      /* Activity tree in sidebar */
      section[data-testid="stSidebar"] div[class*="st-key-activity_tree"] .tree-title{
        font-size: 18px; font-weight: 700; color: var(--muted);
        margin: 8px 0 6px 0;
      }
      section[data-testid="stSidebar"] div[class*="st-key-activity_tree"] .stElementContainer{
        width: 100% !important;
      }
      section[data-testid="stSidebar"] div[class*="st-key-activity_tree"] .stButton{
        margin: 4px 0;
        width: 100%;
      }
      section[data-testid="stSidebar"] div[class*="st-key-activity_tree"] .stButton button{
        width: 100%;
        display: flex;
        justify-content: flex-start;
        align-items: center;
        text-align: left;
        white-space: pre;
        padding: 6px 10px;
        border-radius: 10px;
        border: 1px solid rgba(148,163,184,.18);
        background: rgba(15,23,42,.45);
        color: var(--text);
        font-size: 15px;
        font-weight: 600;
        line-height: 1.2;
      }
      section[data-testid="stSidebar"] div[class*="st-key-activity_tree"] .stButton button > div{
        width: 100%;
        display: flex;
        justify-content: flex-start;
      }
      section[data-testid="stSidebar"] div[class*="st-key-activity_tree"] [data-testid="stMarkdownContainer"]{
        width: 100%;
        text-align: left;
      }
      section[data-testid="stSidebar"] div[class*="st-key-activity_tree"] .stButton button:hover{
        border-color: rgba(125,211,252,.6);
        background: rgba(30,41,59,.6);
      }
      section[data-testid="stSidebar"] div[class*="st-key-activity_tree"] .stButton button:focus{
        outline: none;
        box-shadow: inset 0 0 0 1px rgba(96,165,250,.35);
        border-color: rgba(96,165,250,.8);
      }
      .gauge-help{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 22px;
        height: 22px;
        border-radius: 999px;
        border: 1px solid rgba(148,163,184,.35);
        background: rgba(15,23,42,.6);
        color: var(--muted);
        font-size: 12px;
        font-weight: 700;
        text-transform: none;
        margin: 0 4px 2px 0;
        cursor: help;
        transition: border-color .2s ease, background .2s ease, color .2s ease, box-shadow .2s ease;
      }
      .gauge-help:hover{
        color: var(--text);
        border-color: rgba(96,165,250,.6);
        background: rgba(75,111,244,.22);
        box-shadow: 0 6px 16px rgba(0,0,0,.25);
      }
      .info-badge{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 22px;
        height: 22px;
        border-radius: 999px;
        border: 1px solid rgba(148,163,184,.45);
        background: linear-gradient(180deg, rgba(75,111,244,.25), rgba(15,23,42,.75));
        color: #c9d6ff;
        font-size: 12px;
        font-weight: 700;
        text-transform: none;
        margin-left: 6px;
        vertical-align: middle;
        box-shadow: 0 2px 6px rgba(0,0,0,.25);
        cursor: help;
        transition: border-color .2s ease, background .2s ease, color .2s ease, box-shadow .2s ease;
      }
      .info-badge:hover{
        color: #f8fbff;
        border-color: rgba(96,165,250,.7);
        background: linear-gradient(180deg, rgba(96,165,250,.35), rgba(15,23,42,.7));
        box-shadow: 0 6px 16px rgba(0,0,0,.3);
      }
      .filter-title{
        font-size: 14px;
        font-weight: 700;
        color: var(--muted);
        margin-bottom: 6px;
      }
      div[data-testid="stVerticalBlock"]:has(.filter-title){
        background: rgba(15,23,42,.55);
        border: 1px solid rgba(148,163,184,.16);
        border-radius: 14px;
        padding: 10px 12px 6px;
        margin: 8px 0 10px;
      }
      div[data-testid="stVerticalBlock"]:has(.filter-title) [data-testid="stSelectbox"]{
        width: 100%;
      }
      div[data-testid="stVerticalBlock"]:has(.filter-title) [data-baseweb="select"]{
        max-width: 100%;
      }
      div[data-testid="stVerticalBlock"]:has(.filter-title) [data-baseweb="select"] [value]{
        max-width: 100%;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      div[data-testid="stVerticalBlock"]:has(.filter-title) [data-baseweb="select"] input{
        max-width: 100%;
      }
      div[class*="st-key-activity_select"]{
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        box-shadow: var(--shadow);
        padding: 10px 12px;
      }
      div[class*="st-key-activity_select"] [data-testid="stWidgetLabel"] p{
        font-size: 15px;
        font-weight: 600;
        color: var(--muted);
        letter-spacing: 0.1px;
        line-height: 1.1;
        margin: 0 0 6px 0;
      }
      div[class*="st-key-activity_select"] [data-baseweb="select"] div[value]{
        font-size: 26px;
        font-weight: 800;
        color: var(--text);
        line-height: 1.1;
      }
      div[class*="st-key-activity_select"] [data-baseweb="select"] input{
        font-size: 26px;
        font-weight: 800;
        color: var(--text);
      }
      div[data-testid="stVerticalBlock"]:has(.scurve-hero-title){
        position: relative;
        --glow-height: 120%;
        background: linear-gradient(180deg, rgba(22,29,58,.96), rgba(13,19,48,.92));
        border: 1px solid var(--border);
        border-radius: calc(var(--radius) + 6px);
        box-shadow: var(--shadow);
        padding: 18px 18px 12px;
        overflow: hidden;
      }
      div[data-testid="stVerticalBlock"]:has(.scurve-hero-title)::before{
        content: "";
        position: absolute;
        inset: -15% -10% -15% -10%;
        height: var(--glow-height);
        background:
          radial-gradient(520px 240px at 12% 0%, rgba(75,111,244,.20), transparent 60%),
          radial-gradient(520px 240px at 88% 10%, rgba(47,193,146,.16), transparent 62%),
          radial-gradient(640px 280px at 50% 90%, rgba(75,111,244,.14), transparent 70%);
        pointer-events: none;
      }
      .scurve-hero-title{
        font-size: 26px;
        font-weight: 800;
        color: var(--text);
        margin: 0 0 4px 0;
        font-family:'Space Grotesk','DM Sans',sans-serif;
        letter-spacing:0.2px;
      }
      .scurve-hero-sub{
        font-size: 14px;
        color: var(--muted);
        margin: 0 0 8px 0;
      }
      .scurve-hero-chart-title{
        font-size: 17px;
        font-weight: 700;
        color: var(--text);
        margin: 6px 0 8px 0;
        font-family:'Space Grotesk','DM Sans',sans-serif;
        letter-spacing:0.2px;
      }
      .scurve-hero-note{
        color: var(--muted);
        font-size: 12px;
        margin: 6px 0 0 0;
      }
      div[data-testid="stVerticalBlock"]:has(.scurve-hero-title) [data-testid="stSelectbox"]{
        margin-top: 6px;
      }
      div[data-testid="stVerticalBlock"]:has(.scurve-hero-title) .stPlotlyChart{
        padding: 0 2px 6px 2px;
        box-sizing: border-box;
      }

    </style>
    """
    css = css.replace("__ANIM_SEQ__", str(anim_seq))
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








