from datetime import datetime
from pathlib import Path

import os

import plotly.graph_objects as go
import streamlit as st

from charts import s_curve
from data import demo_series, load_from_excel, sample_dashboard_data
from services_kpis import compute_kpis, extract_dates_labels
from ui import inject_theme


st.set_page_config(page_title="Project Progress", layout="wide")

# ---------- Cross-app links ----------
def _env_or_secret(key: str) -> str | None:
    try:
        if key in st.secrets:
            return st.secrets[key]
    except FileNotFoundError:
        # No local secrets file; fall back to env
        pass
    return os.environ.get(key)


def build_wbs_url():
    # 1) explicit override via secrets or env
    url = _env_or_secret("WBS_URL")
    if url:
        return url
    # 2) assume local dual-port dev: dashboard on 8501, WBS on 8502
    port = os.environ.get("STREAMLIT_SERVER_PORT", "8501")
    if port == "8501":
        return "http://localhost:8502"
    # 3) fallback: same host/path (if both apps are deployed under different paths)
    return "http://localhost:8502"



# ---------- Helpers ----------
def fmt_date(dt):
    if dt is None:
        return "--"
    if isinstance(dt, str):
        return dt
    try:
        return dt.strftime("%d %b %y")
    except Exception:
        return str(dt)


def fmt_pct(val, decimals=2, signed=False):
    if val is None:
        return "--"
    sign = "+" if signed and val > 0 else ""
    return f"{sign}{val:.{decimals}f} %"


def pct_tone(val):
    try:
        v = float(val)
    except Exception:
        return None
    if v < 80:
        return "negative"
    if v < 100:
        return "warn"
    return "positive"


def metric_card(label: str, value: str, sub: str = "", tone: str | None = None):
    cls = f"value {tone}" if tone else "value"
    st.markdown(
        f"""
        <div class="card metric">
            <div class="label">{label}</div>
            <div class="{cls}">{value}</div>
            <div class="sub">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def base_layout(fig, height=220):
    fig.update_layout(
        height=height,
        autosize=False,
        paper_bgcolor="#11162d",
        plot_bgcolor="#11162d",
        font=dict(color="#e8eefc", size=14, family="Inter, 'Segoe UI', sans-serif"),
        margin=dict(l=12, r=40, t=16, b=12),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(size=13),
        ),
    )
    return fig


def gauge_fig(title: str, value: float, color: str, subtitle: str | None = None):
    v = max(0, min(100, float(value)))
    subtitle_html = (
        f"<br><span style='font-size:12px;color:#9da8c6'>{subtitle}</span>"
        if subtitle
        else ""
    )
    fig = go.Figure(
        go.Indicator(
            mode="gauge",
            value=v,
            number={"suffix": "", "font": {"size": 1}, "valueformat": ".1f"},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#4b5878", "tickfont": {"size": 15}},
                "bar": {"color": color, "thickness": 0.38},
                "bgcolor": "rgba(255,255,255,0.04)",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 50], "color": "rgba(255,255,255,0.02)"},
                    {"range": [50, 100], "color": "rgba(255,255,255,0.03)"},
                ],
            },
            domain={"x": [0.10, 0.90], "y": [0.12, 0.98]},
        )
    )
    fig.add_annotation(
        x=0.5,
        y=0.50,
        xref="paper",
        yref="paper",
        text=(
            f"<span style='font-size:16px;font-weight:800;color:{color}'>{title}</span>"
            f"{subtitle_html}"
        ),
        showarrow=False,
        font={"size": 16, "color": color, "family": "Inter, 'Segoe UI', sans-serif", "weight": 800},
        align="center",
        bgcolor="rgba(0,0,0,0)",
        bordercolor="rgba(0,0,0,0)",
        borderwidth=0,
        borderpad=2,
    )
    fig.add_annotation(
        x=0.5,
        y=0.30,
        xref="paper",
        yref="paper",
        text=f"{v:.1f} %",
        showarrow=False,
        font={"size": 32, "color": color, "family": "Inter, 'Segoe UI', sans-serif", "weight": 900},
        align="center",
        bgcolor="rgba(0,0,0,0)",
        bordercolor="rgba(0,0,0,0)",
        borderwidth=0,
        borderpad=0,
        opacity=1,
    )
    fig.update_layout(
        height=300,
        autosize=False,
        margin=dict(l=6, r=6, t=24, b=24),
        paper_bgcolor="#0d1330",
        plot_bgcolor="#0d1330",
    )
    fig.update_traces(gauge_shape="angular")
    return fig

def weekly_progress_fig(data, current_week: str):
    weeks = [d["week"] for d in data]
    planned = [d["planned"] for d in data]
    actual = [d["actual"] for d in data]

    planned_colors = ["#4b6ff4" if w != current_week else "#e9c75f" for w in weeks]
    actual_colors = ["#2fc192" if w != current_week else "#f0aa3c" for w in weeks]

    fig = go.Figure()
    fig.add_bar(
        name="Planned",
        x=weeks,
        y=planned,
        marker_color=planned_colors,
        opacity=0.9,
        text=[f"{p:.1f}%" for p in planned],
        textposition="outside",
        textfont=dict(size=14),
    )
    fig.add_bar(
        name="Actual",
        x=weeks,
        y=actual,
        marker_color=actual_colors,
        opacity=0.9,
        text=[f"{a:.1f}%" for a in actual],
        textposition="outside",
        textfont=dict(size=14),
    )

    ymax = max(planned + actual) if (planned + actual) else 5
    if current_week in weeks:
        fig.add_annotation(
            x=current_week,
            y=ymax * 1.03,
            text="This Week",
            showarrow=False,
            font=dict(color="#e9c75f", size=14, family="Inter, 'Segoe UI', sans-serif"),
        )

    fig.update_layout(
        barmode="group",
        bargap=0.18,
        title_text="",
        xaxis=dict(showgrid=False, tickfont=dict(size=13)),
        yaxis=dict(
            title="%",
            range=[0, ymax * 1.15],
            showgrid=True,
            gridcolor="rgba(255,255,255,0.08)",
            tickfont=dict(size=13),
        ),
        legend=dict(x=1, y=1.08, xanchor="right", orientation="h"),
        margin=dict(t=24),
    )
    return base_layout(fig, height=330)


def weekly_sv_fig(series):
    weeks = [d["week"] for d in series]
    sv_vals = [d["sv"] for d in series]
    colors = ["#2fc192" if v >= 0 else "#f97070" for v in sv_vals]

    fig = go.Figure()
    fig.add_bar(
        x=weeks,
        y=sv_vals,
        name="SV %",
        marker_color=colors,
        opacity=0.7,
        text=[f"{v:+.1f}%" for v in sv_vals],
        textposition="outside",
        textfont=dict(size=12),
    )
    fig.add_trace(
        go.Scatter(
            x=weeks,
            y=sv_vals,
            mode="lines+markers",
            line=dict(color="#33e2b6", width=3),
            marker=dict(size=6),
            name="Trend",
        )
    )
    fig.add_hline(y=0, line_color="rgba(255,255,255,0.25)", line_width=1)
    fig.update_layout(
        title_text="",
        xaxis=dict(showgrid=False, tickfont=dict(size=12), tickmode="array", tickvals=weeks[::2], ticktext=weeks[::2]),
        yaxis=dict(title="%", showgrid=True, gridcolor="rgba(255,255,255,0.08)", tickfont=dict(size=13)),
        legend=dict(x=1, y=1.12, xanchor="right", orientation="h"),
        margin=dict(t=20),
    )
    return base_layout(fig, height=260)


def activities_status_fig(data: dict):
    labels = list(data.keys())
    values = list(data.values())
    colors = ["#2fc192", "#f0aa3c", "#4b6ff4"]

    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.68,
            marker=dict(colors=colors, line=dict(color="#11162d", width=2)),
            textinfo="percent",
            hovertemplate="%{label}: %{value:.2f}%<extra></extra>",
        )
    )
    fig.update_layout(
        title_text="",
        showlegend=True,
        legend=dict(orientation="h", x=0.5, y=0, xanchor="center"),
        margin=dict(l=10, r=10, t=10, b=30),
    )
    return base_layout(fig, height=260)


# ---------- Sidebar navigation ----------
st.sidebar.markdown('<div class="sidebar-nav-title">Navigation</div>', unsafe_allow_html=True)
st.sidebar.page_link("app.py", label="📊 Project Progress")
st.sidebar.page_link("pages/2_WBS.py", label="🧱 WBS")

# ---------- Sidebar selection ----------
page = st.sidebar.radio(
    "Pages",
    ["Dashboard", "S-Curve"],
    index=0,
    format_func=lambda x: "📊 Dashboard" if x == "Dashboard" else "📈 S-Curve",
)

# Apply theme for both local pages
inject_theme()

# ---------- Data (dashboard) ----------
uploaded_dashboard = None
excel_data = None
selected_sheet = None
if page == "Dashboard":
    uploaded_dashboard = st.sidebar.file_uploader(
        "📁 Upload Excel data (Project Progress KPIs)",
        type=["xlsx"],
        key="excel_upload_dashboard",
    )
    if uploaded_dashboard:
        try:
            excel_data = load_from_excel(uploaded_dashboard)
            if excel_data and excel_data.get("sheet_names"):
                selected_sheet = st.sidebar.selectbox(
                    "Sheet",
                    excel_data["sheet_names"],
                    index=excel_data["sheet_names"].index(excel_data["chosen_sheet"]),
                )
                if selected_sheet != excel_data["chosen_sheet"]:
                    excel_data = load_from_excel(uploaded_dashboard, sheet=selected_sheet)
        except Exception as e:
            st.sidebar.warning(f"Erreur de lecture Excel : {e}")

data = sample_dashboard_data()
m = data["metrics"]

if excel_data and excel_data.get("df") is not None:
    labels, planned_finish_dt, forecast_finish_dt = extract_dates_labels(excel_data["df"], excel_data.get("colmap"))
    planned_start_label, planned_finish_label, forecast_finish_label = labels
    planned_pct, actual_pct, sv_pct, spi, delay_days = compute_kpis(
        excel_data["df"], excel_data.get("colmap"), planned_finish_dt=planned_finish_dt, forecast_finish_dt=forecast_finish_dt
    )
    m = {
        "planned_progress": planned_pct or 0,
        "actual_progress": actual_pct or 0,
        "planned_start": planned_start_label or planned_finish_dt,
        "planned_finish": planned_finish_label or planned_finish_dt,
        "forecast_finish": forecast_finish_label or forecast_finish_dt,
        "delay_days": delay_days if delay_days != "_" else 0,
        "sv_pct": sv_pct if sv_pct != "_" else 0,
        "spi": spi if spi != "_" else 0,
    }


# ---------- Pages ----------
def render_dashboard():
    st.markdown(
        f"""
        <div style="margin:12px 0 18px 0; padding:0 8px;">
            <div class="page-header">
              <div class="title">Project Progress Overview 🚀</div>
              <div class="muted" style="margin-top:8px;">Demo data - replace later with your own sources</div>
              <div class="muted" style="font-size:12px; margin-top:8px;">Last updated: {datetime.now().strftime('%d %b %Y, %H:%M')}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    layout_top = st.columns([2.0, 2.8])

    with layout_top[0]:
        gauges_row = st.columns(2)
        with gauges_row[0]:
            st.plotly_chart(
                gauge_fig("Planned Progress", m["planned_progress"], "#4b6ff4"),
                width="stretch",
                config={"displayModeBar": False, "responsive": False},
            )
        with gauges_row[1]:
            st.plotly_chart(
                gauge_fig("Actual Progress", m["actual_progress"], "#2fc192"),
                width="stretch",
                config={"displayModeBar": False, "responsive": False},
            )

    with layout_top[1]:
        row_a = st.columns(3)
        with row_a[0]:
            metric_card("Planned Start", fmt_date(m["planned_start"]))
        with row_a[1]:
            metric_card("Planned Finish", fmt_date(m["planned_finish"]))
        with row_a[2]:
            metric_card("Forecast Finish", fmt_date(m["forecast_finish"]))

        # Add a bit of breathing room before the second row of cards
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        row_b = st.columns(3)
        with row_b[0]:
            delay_tone = "positive" if m["delay_days"] > 0 else "negative" if m["delay_days"] < 0 else None
            metric_card("Delay/Ahead", f"{m['delay_days']} days", tone=delay_tone)
        with row_b[1]:
            sv_tone = pct_tone(m["sv_pct"])
            metric_card("SV %", fmt_pct(m["sv_pct"], signed=True, decimals=1), tone=sv_tone)
        with row_b[2]:
            spi_pct = m["spi"] * 100 if m.get("spi") is not None else None
            spi_tone = pct_tone(spi_pct)
            metric_card("SPI", fmt_pct(spi_pct, decimals=1), tone=spi_tone)

    with st.container():
        st.markdown('<div class="chart-heading">Weekly Progress 📆</div>', unsafe_allow_html=True)
        st.plotly_chart(
            weekly_progress_fig(data["weekly_progress"], data["current_week"]),
            width="stretch",
            config={"displayModeBar": False, "responsive": False},
        )

    bottom = st.columns([1.7, 1.0])
    with bottom[0]:
        with st.container():
            st.markdown('<div class="chart-heading">Weekly SV % 📉</div>', unsafe_allow_html=True)
            st.plotly_chart(
                weekly_sv_fig(data["weekly_sv"]),
                width="stretch",
                config={"displayModeBar": False, "responsive": False},
            )

    with bottom[1]:
        with st.container():
            st.markdown('<div class="chart-heading">Activities Status ✅</div>', unsafe_allow_html=True)
            st.plotly_chart(
                activities_status_fig(data["activities_status"]),
                width="stretch",
                config={"displayModeBar": False, "responsive": False},
            )

    st.caption("Placeholder visuals with simulated data. Replace the sample data functions when real inputs are ready.")


def render_s_curve_page():
    st.markdown(
        """
        <div style="margin:12px 0 18px 0; padding:0 8px;">
          <div class="page-header">
              <div class="title">S-Curve</div>
              <div class="muted" style="margin-top:8px;">Cumulative planned vs actual vs forecast</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    x, weekly_actual, actual_curve, planned_curve, forecast_curve = demo_series()
    fig = s_curve(x, weekly_actual, actual_curve, planned_curve, forecast_curve)
    fig.update_layout(title_text="")
    st.markdown('<div class="chart-heading">Progress S-Curve</div>', unsafe_allow_html=True)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False, "responsive": False})
    st.caption("Simulated data for demo. Hook to your real cumulative series when ready.")


if page == "Dashboard":
    render_dashboard()
elif page == "S-Curve":
    render_s_curve_page()
