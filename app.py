from datetime import datetime, date
from time import perf_counter
from pathlib import Path
from typing import Any
import html

import os
import tempfile
from wbs_app.extract_wbs_json import (
    build_schedule_lookup,
    build_preview_rows,
    build_weekly_progress,
    parse_percent_float,
    as_text,
    get_table_headers,
    suggest_column_mapping,
    SUMMARY_REQUIRED_FIELDS,
    SUMMARY_OPTIONAL_FIELDS,
    ASSIGN_REQUIRED_FIELDS,
    ASSIGN_OPTIONAL_FIELDS,
)

import plotly.graph_objects as go
import streamlit as st

from auth_google import (
    require_login,
    render_auth_sidebar,
    brand_strip_html,
    _custom_logo_data_uri,
    _remove_custom_logo,
)
from charts import s_curve
from data import demo_series, load_from_excel, sample_dashboard_data
from services_kpis import compute_kpis, extract_dates_labels
from ui import inject_theme
from activity_filters import build_activity_filter_sidebar
from shared_excel import (
    persist_shared_excel_state,
    restore_shared_excel_state,
    set_default_excel_if_missing,
)


page_override = st.session_state.get("_page_override")
page_source = st.session_state.get("_page_source")
if page_override and page_source != "S-Curve":
    st.session_state.pop("_page_override", None)
    st.session_state.pop("_page_source", None)
    page_override = None

_icon_path = Path(__file__).resolve().parent / "Wibis_logo.png"
st.set_page_config(
    page_title="Wibis",
    page_icon=str(_icon_path) if _icon_path.exists() else "🧭",
    layout="wide",
)
st.markdown(
    "<style>[data-testid='stSidebarNav']{display:none !important;}</style>",
    unsafe_allow_html=True,
)

user = require_login()
render_auth_sidebar(user)

def _store_shared_upload(uploaded):
    if uploaded is None:
        return st.session_state.get("shared_excel_path")
    file_key = f"{uploaded.name}:{uploaded.size}"
    if st.session_state.get("shared_excel_key") != file_key:
        old_path = st.session_state.get("shared_excel_path")
        if old_path and os.path.exists(old_path):
            try:
                os.unlink(old_path)
            except OSError:
                pass
        data = uploaded.getvalue()
        suffix = Path(uploaded.name).suffix or ".xlsx"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.write(data)
        tmp.close()
        st.session_state["shared_excel_path"] = tmp.name
        st.session_state["shared_excel_key"] = file_key
        st.session_state["shared_excel_name"] = uploaded.name
        persist_shared_excel_state(tmp.name, uploaded.name, file_key)
    return st.session_state.get("shared_excel_path")

def _excel_template_bytes():
    candidates = [
        Path("artifacts") / "Chronoplan_Template.xlsx",
        Path("artifacts") / "W_example.xlsx",
        Path("artifacts") / "wbs_sample.xlsx",
        Path("Progress.xlsx"),
    ]
    for path in candidates:
        if path.exists():
            return path.read_bytes(), path.name
    return None, None

def _time_call(func, *args, **kwargs):
    start = perf_counter()
    result = func(*args, **kwargs)
    return result, (perf_counter() - start) * 1000.0

def _render_perf_stats(stats: dict[str, float]) -> None:
    if not stats:
        st.sidebar.caption("No timings captured yet.")
        return
    st.sidebar.markdown("**Perf timings (ms)**")
    for label, value in stats.items():
        st.sidebar.markdown(f"- {label}: {value:.1f}")

def _file_cache_key(path: str | None) -> tuple[float, int] | None:
    if not path:
        return None
    try:
        stat = os.stat(path)
    except OSError:
        return None
    return (stat.st_mtime, stat.st_size)

@st.cache_data(show_spinner=False)
def _cached_load_from_excel(path: str, file_key: tuple[float, int] | None):
    _ = file_key
    return load_from_excel(path)

@st.cache_data(show_spinner=False)
def _cached_schedule_lookup(
    path: str,
    file_key: tuple[float, int] | None,
    column_mapping: dict | None,
    today_key: str,
):
    _ = file_key
    today = date.fromisoformat(today_key)
    return build_schedule_lookup(path, today=today, column_mapping=column_mapping)

@st.cache_data(show_spinner=False)
def _cached_preview_rows(
    path: str,
    file_key: tuple[float, int] | None,
    prefer_first_table: bool,
    column_mapping: dict | None,
):
    _ = file_key
    return build_preview_rows(
        path,
        table_type="activity_summary",
        prefer_first_table=prefer_first_table,
        column_mapping=column_mapping,
    )

@st.cache_data(show_spinner=False)
def _cached_weekly_progress(
    path: str,
    file_key: tuple[float, int] | None,
    activity_id: str,
    column_mapping: dict | None,
    today_key: str,
):
    _ = file_key
    today = date.fromisoformat(today_key)
    return build_weekly_progress(
        path,
        activity_id,
        today=today,
        column_mapping=column_mapping,
    )

def _render_excel_format_help():
    with st.sidebar.expander("Excel format guide", expanded=False):
        st.page_link("pages/1_Excel_Guide.py", label="Open full guide")
        st.markdown(
            "\n".join(
                [
                    "**Expected structure**",
                    "- Activity Summary table with columns:",
                    "  Activity ID, Activity Name, BL Project Finish (or Planned Finish), Finish (or Forecast Finish), Units % Complete, Variance - BL Project Finish Date",
                    "- Resource Assignments table with columns:",
                    "  Activity ID, Start, Finish, Budgeted Units, Spreadsheet Field",
                    "- Activity IDs must match between the two tables (same set of IDs)",
                    "- Weekly date columns (week start) in Resource Assignments for planned/actual values",
                    "",
                    "**Tips**",
                    "- Keep a single header row at the top of each table",
                    "- Avoid merged header cells",
                    "- Dates can be Excel dates or ISO (YYYY-MM-DD)",
                ]
            ),
            unsafe_allow_html=False,
        )
        st.markdown("**Highly recommended**: use the template below to avoid mapping issues.")
        data, name = _excel_template_bytes()
        if data and name:
            st.download_button(
                "Download recommended template",
                data=data,
                file_name=name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            st.caption("Template file not found in artifacts/ or project root.")

def _init_column_mapping_state() -> dict:
    mapping = st.session_state.get("column_mapping")
    if not isinstance(mapping, dict):
        mapping = {}
    if "activity_summary" not in mapping or not isinstance(mapping.get("activity_summary"), dict):
        mapping["activity_summary"] = {}
    if "resource_assignments" not in mapping or not isinstance(mapping.get("resource_assignments"), dict):
        mapping["resource_assignments"] = {}
    st.session_state["column_mapping"] = mapping
    return mapping

def _sync_mapping_for_upload() -> None:
    excel_key = st.session_state.get("shared_excel_key")
    if st.session_state.get("mapping_source_key") != excel_key:
        st.session_state["column_mapping"] = {
            "activity_summary": {},
            "resource_assignments": {},
        }
        st.session_state["mapping_source_key"] = excel_key
        st.session_state["mapping_open"] = False
        st.session_state["mapping_skipped"] = False

def _missing_required_fields(
    headers: list[Any] | None,
    table_type: str,
    mapping: dict[str, dict[str, str]],
) -> list[str]:
    if not headers:
        return []
    header_list = [str(h).strip() for h in headers if str(h or "").strip()]
    suggested = suggest_column_mapping(headers, table_type)
    if table_type == "activity_summary":
        required_fields = SUMMARY_REQUIRED_FIELDS
    else:
        required_fields = ASSIGN_REQUIRED_FIELDS
    missing: list[str] = []
    table_mapping = mapping.get(table_type, {})
    for field in required_fields:
        mapped = table_mapping.get(field)
        if mapped and mapped in header_list:
            continue
        if field in suggested:
            continue
        missing.append(field)
    return missing

def _render_mapping_form(
    table_type: str,
    headers: list[Any],
    mapping: dict[str, dict[str, str]],
    key_prefix: str,
) -> dict[str, str]:
    if table_type == "activity_summary":
        required_fields = SUMMARY_REQUIRED_FIELDS
        optional_fields = SUMMARY_OPTIONAL_FIELDS
        title = "Activity Summary columns"
    else:
        required_fields = ASSIGN_REQUIRED_FIELDS
        optional_fields = ASSIGN_OPTIONAL_FIELDS
        title = "Resource Assignments columns"
    st.markdown(f"### {title}")
    options = [str(h).strip() for h in headers if str(h or "").strip()]
    suggested = suggest_column_mapping(headers, table_type)
    current_mapping = mapping.get(table_type, {})
    selected: dict[str, str] = {}
    used: set[str] = set()

    for field in required_fields + optional_fields:
        current = current_mapping.get(field) or suggested.get(field) or ""
        option_list = ["-- Not mapped --"] + [
            opt for opt in options if opt not in used or opt == current
        ]
        if current and current not in option_list:
            option_list.insert(1, current)
        label = field if field in required_fields else f"{field} (optional)"
        choice = st.selectbox(
            label,
            option_list,
            index=option_list.index(current) if current in option_list else 0,
            key=f"{key_prefix}_{table_type}_{field}".replace(" ", "_").lower(),
        )
        if choice != "-- Not mapped --":
            selected[field] = choice
            used.add(choice)
    return selected

def _maybe_open_mapping_dialog(shared_path: str | None) -> None:
    if not shared_path:
        return
    _sync_mapping_for_upload()
    mapping = _init_column_mapping_state()

    summary_headers = get_table_headers(shared_path, "activity_summary")
    assign_headers = get_table_headers(shared_path, "resource_assignments")
    summary_missing = _missing_required_fields(
        summary_headers[0] if summary_headers else None,
        "activity_summary",
        mapping,
    )
    assign_missing = _missing_required_fields(
        assign_headers[0] if assign_headers else None,
        "resource_assignments",
        mapping,
    )
    has_missing = bool(summary_missing or assign_missing)

    if has_missing and not st.session_state.get("mapping_skipped"):
        st.session_state["mapping_open"] = True

    if has_missing:
        missing_text = []
        if summary_missing:
            missing_text.append("Activity Summary: " + ", ".join(summary_missing))
        if assign_missing:
            missing_text.append("Resource Assignments: " + ", ".join(assign_missing))
        st.sidebar.warning(
            "Column mapping needed for: " + " | ".join(missing_text)
        )
    if st.sidebar.button("Map columns"):
        st.session_state["mapping_open"] = True

    if not st.session_state.get("mapping_open"):
        return

    dialog_fn = getattr(st, "dialog", None)
    if callable(dialog_fn):
        def _show_dialog() -> None:
            _render_mapping_dialog_body(
                summary_headers,
                assign_headers,
                mapping,
            )
        dialog_fn("Match your Excel columns")(_show_dialog)()
    else:
        st.markdown("## Match your Excel columns")
        _render_mapping_dialog_body(
            summary_headers,
            assign_headers,
            mapping,
        )

def _render_mapping_dialog_body(
    summary_headers: tuple[list[Any], dict[str, Any]] | None,
    assign_headers: tuple[list[Any], dict[str, Any]] | None,
    mapping: dict[str, dict[str, str]],
) -> None:
    st.markdown(
        "Select the column in your Excel file that matches each expected field."
    )
    new_mapping: dict[str, dict[str, str]] = {
        "activity_summary": {},
        "resource_assignments": {},
    }
    if summary_headers:
        new_mapping["activity_summary"] = _render_mapping_form(
            "activity_summary",
            summary_headers[0],
            mapping,
            key_prefix="map",
        )
    else:
        st.info("Activity Summary table not detected.")

    if assign_headers:
        new_mapping["resource_assignments"] = _render_mapping_form(
            "resource_assignments",
            assign_headers[0],
            mapping,
            key_prefix="map",
        )
    else:
        st.info("Resource Assignments table not detected.")

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Apply mapping"):
            st.session_state["column_mapping"] = new_mapping
            st.session_state["mapping_open"] = False
            st.session_state["mapping_skipped"] = False
            st.rerun()
    with col2:
        if st.button("Skip for now"):
            st.session_state["mapping_open"] = False
            st.session_state["mapping_skipped"] = True


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


def _truncate_label(text: str, max_len: int = 44) -> str:
    if not text:
        return ""
    text = str(text)
    if len(text) <= max_len:
        return text
    if max_len <= 3:
        return text[:max_len]
    return text[: max_len - 3] + "..."


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


def metric_card(label: str, value: str, sub: str = "", tone: str | None = None, tip: str | None = None):
    cls = f"value {tone}" if tone else "value"
    info_badge = f'<span class="info-badge" title="{html.escape(tip)}">ℹ</span>' if tip else ""
    st.markdown(
        f"""
        <div class="card metric">
            <div class="label">{label}{info_badge}</div>
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
        transition=dict(duration=850, easing="cubic-in-out"),
    )
    return fig


def gauge_fig(title: str, value: float, color: str, subtitle: str | None = None, tip: str | None = None):
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
            domain={"x": [0.04, 0.88], "y": [0.10, 0.92]},
        )
    )
    fig.add_annotation(
        x=0.46,
        y=0.56,
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
        x=0.46,
        y=0.34,
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
        margin=dict(l=18, r=18, t=20, b=36),
        paper_bgcolor="#0d1330",
        plot_bgcolor="#0d1330",
        transition=dict(duration=850, easing="cubic-in-out"),
    )
    fig.update_traces(gauge_shape="angular")
    return fig

def _parse_week_date(val):
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if not val:
        return None
    s = str(val).strip()
    for fmt in ("%Y-%m-%d", "%d-%b-%y", "%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            continue
    return None


def _short_week_label(raw):
    if not raw:
        return ""
    s = str(raw).strip()
    if "00:00:00" in s:
        s = s.split()[0]
    for fmt in ("%Y-%m-%d", "%d-%b-%y", "%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(s, fmt).strftime("%d-%b")
        except Exception:
            continue
    return s


def _tip_for_hover(tip: str | None) -> str:
    if not tip:
        return ""
    return str(tip).replace("\n", "<br>")

def _hover_with_tip(display: str, tip: str | None) -> str:
    tip_html = _tip_for_hover(tip)
    if tip_html:
        return f"{display}<br>{tip_html}"
    return display


def _build_weekly_window(data, current_week: str | date | None):
    current_date = _parse_week_date(current_week)
    weeks = [d.get("week") for d in data]
    planned_vals = []
    planned_text = []
    planned_tips = []
    actual_vals = []
    actual_text = []
    actual_tips = []
    forecast_vals = []
    forecast_text = []
    forecast_tips = []
    week_labels = []
    week_dates = []

    for d in data:
        label = d.get("week_label") or d.get("week") or ""
        week_labels.append(_short_week_label(label))
        week_dates.append(_parse_week_date(d.get("week_date") or d.get("week")))

        p_val = d.get("planned")
        p_display = d.get("planned_display")
        p_tip = d.get("planned_tip", "")
        p_text = p_display or (f"{p_val:.1f}%" if isinstance(p_val, (int, float)) else "?")
        planned_vals.append(p_val if isinstance(p_val, (int, float)) else 0)
        planned_text.append(p_text)
        planned_tips.append(p_tip)

        a_val = d.get("actual")
        a_display = d.get("actual_display")
        a_tip = d.get("actual_tip", "")
        a_text = a_display or (f"{a_val:.1f}%" if isinstance(a_val, (int, float)) else "?")
        is_future = False
        if week_dates[-1] and current_date:
            is_future = week_dates[-1] > current_date
        if is_future:
            a_tip = a_tip.replace("Actual %", "Forecast %").replace("Actual unavailable", "Forecast unavailable")
            forecast_vals.append(a_val if isinstance(a_val, (int, float)) else None)
            forecast_text.append(a_text)
            forecast_tips.append(a_tip)
            actual_vals.append(None)
            actual_text.append("")
            actual_tips.append("")
        else:
            actual_vals.append(a_val if isinstance(a_val, (int, float)) else None)
            actual_text.append(a_text)
            actual_tips.append(a_tip)
            forecast_vals.append(None)
            forecast_text.append("")
            forecast_tips.append("")

    # Force a 7-week window with the current week in 4th position (index 3)
    current_idx = None
    if current_date and any(week_dates):
        for idx, d in enumerate(week_dates):
            if d == current_date:
                current_idx = idx
                break
    if current_idx is None and current_week in weeks:
        current_idx = weeks.index(current_week)

    window = 7 if len(weeks) >= 7 else len(weeks)
    if window == 0:
        return None

    if current_idx is None:
        start_idx = max(0, len(weeks) - window)
        current_pos = None
    else:
        can_center = (current_idx - 3) >= 0 and (current_idx + 3) < len(weeks)
        if can_center:
            start_idx = current_idx - 3
            current_pos = 3
        else:
            if current_idx < 3:
                start_idx = 0
            elif current_idx + 3 >= len(weeks):
                start_idx = max(0, len(weeks) - window)
            else:
                start_idx = current_idx - 3
            current_pos = current_idx - start_idx

    end_idx = start_idx + window
    slice_idx = list(range(start_idx, end_idx))
    weeks = [weeks[i] for i in slice_idx]
    week_labels = [week_labels[i] for i in slice_idx]
    week_dates = [week_dates[i] for i in slice_idx]
    planned_vals = [planned_vals[i] for i in slice_idx]
    planned_text = [planned_text[i] for i in slice_idx]
    planned_tips = [planned_tips[i] for i in slice_idx]
    actual_vals = [actual_vals[i] for i in slice_idx]
    actual_text = [actual_text[i] for i in slice_idx]
    actual_tips = [actual_tips[i] for i in slice_idx]
    forecast_vals = [forecast_vals[i] for i in slice_idx]
    forecast_text = [forecast_text[i] for i in slice_idx]
    forecast_tips = [forecast_tips[i] for i in slice_idx]
    planned_tips = [_tip_for_hover(t) for t in planned_tips]
    actual_tips = [_tip_for_hover(t) for t in actual_tips]
    forecast_tips = [_tip_for_hover(t) for t in forecast_tips]

    return {
        "weeks": weeks,
        "week_labels": week_labels,
        "week_dates": week_dates,
        "planned_vals": planned_vals,
        "planned_text": planned_text,
        "planned_tips": planned_tips,
        "actual_vals": actual_vals,
        "actual_text": actual_text,
        "actual_tips": actual_tips,
        "forecast_vals": forecast_vals,
        "forecast_text": forecast_text,
        "forecast_tips": forecast_tips,
        "current_pos": current_pos,
    }


def weekly_progress_fig(data, current_week: str | date | None):
    window = _build_weekly_window(data, current_week)
    if not window:
        return base_layout(go.Figure(), height=350)
    weeks = window["weeks"]
    week_labels = window["week_labels"]
    week_dates = window["week_dates"]
    planned_vals = window["planned_vals"]
    planned_text = window["planned_text"]
    planned_tips = window["planned_tips"]
    actual_vals = window["actual_vals"]
    actual_text = window["actual_text"]
    actual_tips = window["actual_tips"]
    forecast_vals = window["forecast_vals"]
    forecast_text = window["forecast_text"]
    forecast_tips = window["forecast_tips"]
    current_pos = window["current_pos"]

    planned_colors = ["#4b6ff4"] * len(weeks)
    actual_colors = ["#2fc192"] * len(weeks)
    forecast_colors = ["#8f7cf6"] * len(weeks)
    if current_pos is not None and 0 <= current_pos < len(weeks):
        planned_colors[current_pos] = "#e9c75f"
        actual_colors[current_pos] = "#f0aa3c"

    fig = go.Figure()
    fig.add_bar(
        name="Planned",
        x=list(range(len(weeks))),
        y=planned_vals,
        marker_color=planned_colors,
        marker_line=dict(color="rgba(255,255,255,0.08)", width=1),
        opacity=0.9,
        text=planned_text,
        textposition="outside",
        textfont=dict(size=14),
        hovertext=planned_tips,
        customdata=week_labels,
        offsetgroup="planned",
        hovertemplate="%{customdata}<br>%{text}<br>%{hovertext}<extra></extra>",
    )

    show_actual = any(v is not None for v in actual_vals)
    if show_actual:
        fig.add_bar(
            name="Actual",
            x=list(range(len(weeks))),
            y=actual_vals,
            marker_color=actual_colors,
            marker_line=dict(color="rgba(255,255,255,0.08)", width=1),
            opacity=0.9,
            text=actual_text,
            textposition="outside",
            textfont=dict(size=14),
            hovertext=actual_tips,
            customdata=week_labels,
            offsetgroup="actual",
            hovertemplate="%{customdata}<br>%{text}<br>%{hovertext}<extra></extra>",
        )

    show_forecast = any(v is not None for v in forecast_vals)
    if show_forecast:
        fig.add_bar(
            name="Forecast",
            x=list(range(len(weeks))),
            y=forecast_vals,
            marker_color=forecast_colors,
            marker_line=dict(color="rgba(255,255,255,0.08)", width=1),
            opacity=0.9,
            text=forecast_text,
            textposition="outside",
            textfont=dict(size=14),
            hovertext=forecast_tips,
            customdata=week_labels,
            offsetgroup="actual",
            hovertemplate="%{customdata}<br>%{text}<br>%{hovertext}<extra></extra>",
        )

    all_vals = [v for v in (planned_vals + actual_vals + forecast_vals) if isinstance(v, (int, float))]
    ymax = max(all_vals) if all_vals else 5
    tick_labels = []
    for idx, raw in enumerate(week_labels):
        if current_pos is not None and idx == current_pos:
            tick_labels.append("Current week")
        else:
            tick_labels.append(raw)

    fig.update_layout(
        barmode="group",
        bargap=0.18,
        bargroupgap=0.14,
        title_text="",
        xaxis=dict(
            showgrid=False,
            tickfont=dict(size=13),
            automargin=True,
            tickmode="array",
            tickvals=list(range(len(weeks))),
            ticktext=tick_labels,
        ),
        yaxis=dict(
            title="%",
            range=[0, ymax * 1.15],
            showgrid=True,
            gridcolor="rgba(255,255,255,0.08)",
            tickfont=dict(size=13),
            automargin=True,
        ),
        legend=dict(x=1, y=1.08, xanchor="right", orientation="h"),
    )
    fig = base_layout(fig, height=350)
    fig.update_layout(margin=dict(l=12, r=40, t=24, b=28))
    return fig


def render_weekly_warnings(info: dict, label: str = "Weekly progress"):
    errors = info.get("errors") if isinstance(info, dict) else None
    if not errors:
        return
    seen = set()
    uniq = []
    for err in errors:
        if not err:
            continue
        if err in seen:
            continue
        seen.add(err)
        uniq.append(err)
    if not uniq:
        return
    message = label + " warnings:\n" + "\n".join(f"- {err}" for err in uniq)
    st.warning(message)


def compute_activity_status_breakdown(activity_rows: list[dict], selected_idx: int | None):
    statuses = ["Completed", "In Progress", "Not Started"]
    totals = {status: 0.0 for status in statuses}
    warnings = []
    error_msg = None
    if not activity_rows or selected_idx is None:
        return totals, warnings, "Activity status unavailable: no activity selected."

    def _to_number(val):
        if val is None:
            return None
        s = str(val).strip()
        if s == "":
            return None
        try:
            return float(s)
        except Exception:
            try:
                return float(s.replace(",", ""))
            except Exception:
                return None

    def _normalize_status(val):
        if val is None:
            return None
        s = str(val).strip().lower()
        mapping = {
            "completed": "Completed",
            "complete": "Completed",
            "in progress": "In Progress",
            "inprogress": "In Progress",
            "not started": "Not Started",
            "notstarted": "Not Started",
        }
        return mapping.get(s)

    parent = activity_rows[selected_idx]
    parent_label = parent.get("label", "selected activity")
    parent_budget = _to_number(parent.get("budgeted_units"))
    if not parent_budget or parent_budget == 0:
        error_msg = f"Budgeted Labor Units missing/0 for {parent_label}."

    parent_level = int(parent.get("level", 0))
    end_idx = len(activity_rows)
    for i in range(selected_idx + 1, len(activity_rows)):
        if int(activity_rows[i].get("level", 0)) <= parent_level:
            end_idx = i
            break

    if selected_idx + 1 >= end_idx:
        candidates = [selected_idx]
    else:
        candidates = list(range(selected_idx + 1, end_idx))

    leaf_indices = []
    for idx in candidates:
        level = int(activity_rows[idx].get("level", 0))
        next_idx = idx + 1
        if next_idx >= end_idx:
            leaf_indices.append(idx)
        else:
            next_level = int(activity_rows[next_idx].get("level", 0))
            if next_level <= level:
                leaf_indices.append(idx)

    for idx in leaf_indices:
        row = activity_rows[idx]
        label = row.get("label", "activity")
        status_raw = row.get("activity_status")
        status = _normalize_status(status_raw)
        if not status:
            warnings.append(f"Ignored leaf '{label}': missing/invalid Activity Status ({status_raw}).")
            continue
        units = _to_number(row.get("budgeted_units"))
        if units is None:
            warnings.append(f"Ignored leaf '{label}': missing Budgeted Labor Units.")
            continue
        totals[status] += units

    if not leaf_indices:
        warnings.append(f"No leaf activities found under '{parent_label}'.")

    if error_msg:
        return {k: 0.0 for k in totals}, warnings, error_msg

    percentages = {}
    for status, total in totals.items():
        percentages[status] = (total / parent_budget * 100) if parent_budget else 0.0
    return percentages, warnings, None


def weekly_sv_fig(data, current_week: str | date | None):
    window = _build_weekly_window(data, current_week)
    if not window:
        return base_layout(go.Figure(), height=260)
    week_labels = window["week_labels"]
    planned_vals = window["planned_vals"]
    planned_text = window["planned_text"]
    planned_tips = window["planned_tips"]
    actual_vals = window["actual_vals"]
    actual_text = window["actual_text"]
    actual_tips = window["actual_tips"]
    forecast_vals = window["forecast_vals"]
    forecast_text = window["forecast_text"]
    forecast_tips = window["forecast_tips"]
    current_pos = window["current_pos"]

    sv_vals = []
    sv_text = []
    sv_tips = []
    for idx in range(len(week_labels)):
        planned_ok = str(planned_text[idx]).strip() != "?"
        if actual_vals[idx] is not None:
            actual_ok = str(actual_text[idx]).strip() != "?"
            if planned_ok and actual_ok:
                sv = planned_vals[idx] - actual_vals[idx]
                sv_vals.append(sv)
                sv_text.append(f"{sv:+.2f}%")
                sv_tips.append(
                    f"SV % = Planned % - Actual %<br>Planned: {planned_text[idx]}<br>Actual: {actual_text[idx]}<br>{planned_tips[idx]}<br>{actual_tips[idx]}"
                )
            else:
                sv_vals.append(0)
                sv_text.append("?")
                sv_tips.append("SV unavailable: planned/actual missing.")
        elif forecast_vals[idx] is not None:
            forecast_ok = str(forecast_text[idx]).strip() != "?"
            if planned_ok and forecast_ok:
                sv = planned_vals[idx] - forecast_vals[idx]
                sv_vals.append(sv)
                sv_text.append(f"{sv:+.2f}%")
                sv_tips.append(
                    f"SV % = Planned % - Forecast %<br>Planned: {planned_text[idx]}<br>Forecast: {forecast_text[idx]}<br>{planned_tips[idx]}<br>{forecast_tips[idx]}"
                )
            else:
                sv_vals.append(0)
                sv_text.append("?")
                sv_tips.append("SV unavailable: planned/forecast missing.")
        else:
            sv_vals.append(0)
            sv_text.append("?")
            sv_tips.append("SV unavailable: missing data.")

    colors = []
    for idx, val in enumerate(sv_vals):
        if sv_text[idx] == "?":
            colors.append("#657089")
        else:
            colors.append("#2fc192" if val >= 0 else "#f97070")
    valid_vals = [v for i, v in enumerate(sv_vals) if sv_text[i] != "?"]
    if valid_vals:
        ymin = min(0, min(valid_vals))
        ymax = max(0, max(valid_vals))
        pad = max(0.6, (ymax - ymin) * 0.2)
    else:
        ymin = -5
        ymax = 5
        pad = 1
    tick_labels = []
    for idx, raw in enumerate(week_labels):
        if current_pos is not None and idx == current_pos:
            tick_labels.append("Current week")
        else:
            tick_labels.append(raw)

    fig = go.Figure()
    fig.add_bar(
        x=list(range(len(week_labels))),
        y=sv_vals,
        name="SV %",
        marker_color=colors,
        opacity=0.7,
        text=sv_text,
        textposition="outside",
        textfont=dict(size=12),
        hovertext=sv_tips,
        customdata=week_labels,
        width=0.55,
        cliponaxis=False,
        hovertemplate="%{customdata}<br>%{text}<br>%{hovertext}<extra></extra>",
    )
    fig.add_trace(
        go.Scatter(
            x=list(range(len(week_labels))),
            y=sv_vals,
            mode="lines+markers",
            line=dict(color="#33e2b6", width=3),
            marker=dict(size=6),
            cliponaxis=False,
            name="Trend",
        )
    )
    fig.add_hline(y=0, line_color="rgba(255,255,255,0.25)", line_width=1)
    fig.update_layout(
        title_text="",
        xaxis=dict(
            showgrid=False,
            tickfont=dict(size=12),
            tickmode="array",
            tickvals=list(range(len(week_labels))),
            ticktext=tick_labels,
        ),
        yaxis=dict(
            title="%",
            showgrid=True,
            gridcolor="rgba(255,255,255,0.08)",
            tickfont=dict(size=13),
            range=[ymin - pad, ymax + pad],
        ),
        legend=dict(x=1, y=1.12, xanchor="right", orientation="h"),
        margin=dict(t=28, b=40),
        bargap=0.25,
    )
    return base_layout(fig, height=280)


def activities_status_fig(data: dict, error_msg: str | None = None, apply_layout: bool = True):
    labels = list(data.keys())
    values = [float(v) if isinstance(v, (int, float)) else 0.0 for v in data.values()]
    colors = ["#2fc192", "#f0aa3c", "#4b6ff4"]

    if error_msg:
        labels = ["Completed", "In Progress", "Not Started"]
        values = [1, 1, 1]

    pie_kwargs = dict(
        labels=labels,
        values=values,
        hole=0.58,
        marker=dict(colors=colors, line=dict(color="#11162d", width=2)),
        textposition="inside",
        textfont=dict(size=14, color="#e6eaf1"),
        insidetextorientation="auto",
        sort=False,
        direction="clockwise",
        rotation=90,
    )
    if error_msg:
        pie_kwargs.update(
            text=["?", "?", "?"],
            textinfo="text",
            hovertemplate=f"%{{label}}: ?<br>{error_msg}<extra></extra>",
        )
    else:
        pie_kwargs.update(
            textinfo="text",
            texttemplate="%{percent:.1%}",
            hovertemplate="%{label}: %{percent:.2%}<extra></extra>",
        )

    fig = go.Figure(go.Pie(**pie_kwargs))
    if error_msg:
        fig.add_annotation(
            text="?",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            font=dict(size=28, color="#9aa5c7", family="Inter, 'Segoe UI', sans-serif"),
        )
    fig.update_layout(
        title_text="",
        showlegend=True,
        legend=dict(orientation="h", x=0.5, y=0, xanchor="center"),
        margin=dict(l=10, r=10, t=10, b=30),
        uniformtext=None,
    )
    if apply_layout:
        return base_layout(fig, height=260)
    return fig


# ---------- Sidebar navigation ----------
st.sidebar.markdown('<div class="sidebar-nav-title">Navigation</div>', unsafe_allow_html=True)
st.sidebar.page_link("app.py", label="Project Progress")
st.sidebar.page_link("pages/3_S_Curve.py", label="S-Curve")
st.sidebar.page_link("pages/2_WBS.py", label="WBS")
st.sidebar.markdown("<hr>", unsafe_allow_html=True)

# ---------- Sidebar selection ----------
page = "S-Curve" if page_override == "S-Curve" else "Dashboard"

# ---------- Shared Excel upload ----------
_render_excel_format_help()
restore_shared_excel_state()
shared_upload = st.sidebar.file_uploader(
    "Upload project Excel (.xlsx)",
    type=["xlsx", "xlsm"],
    key="excel_upload_shared",
    label_visibility="collapsed",
)
shared_path = _store_shared_upload(shared_upload)
if shared_path is None:
    shared_path = set_default_excel_if_missing()
if shared_path and st.session_state.get("shared_excel_name"):
    st.sidebar.caption(f"Current file: {st.session_state['shared_excel_name']}")
file_cache_key = _file_cache_key(shared_path)
today_cache_key = date.today().isoformat()

# Apply theme for both local pages
inject_theme()
perf_stats: dict[str, float] = {}

# ---------- Data (dashboard) ----------
excel_data = None
selected_sheet = None
if page == "Dashboard" and shared_path:
    try:
        (excel_data, ms) = _time_call(
            _cached_load_from_excel,
            shared_path,
            file_cache_key,
        )
        perf_stats["excel_load"] = ms
    except Exception as e:
        st.sidebar.warning(f"Excel read error: {e}")

data = sample_dashboard_data()
m = data["metrics"]
weekly_progress = data["weekly_progress"]
current_week = data["current_week"]
activity_rows = None
schedule_lookup = None
selected_row = None
activity_filter = None

if shared_path:
    try:
        (schedule_lookup, schedule_info_dash), ms = _time_call(
            _cached_schedule_lookup,
            shared_path,
            file_cache_key,
            column_mapping=st.session_state.get("column_mapping"),
            today_key=today_cache_key,
        )
        perf_stats["schedule_lookup"] = ms
        (activity_rows, ms) = _time_call(
            _cached_preview_rows,
            shared_path,
            file_cache_key,
            True,
            column_mapping=st.session_state.get("column_mapping"),
        )
        perf_stats["preview_rows"] = ms
    except Exception as e:
        st.sidebar.warning(f"Excel read error: {e}")

if activity_rows:
    activity_filter = build_activity_filter_sidebar(activity_rows)

def compute_dashboard_metrics_from_activity(row: dict, sched_lu: dict):
    if not row:
        return None
    def _append_tip_sources(tip: str | None, sources: list[str], prefix: str = "Cells") -> str | None:
        items = [s for s in sources if s]
        if not items:
            return tip
        line = f"{prefix}:\n" + "\n".join(f"- {s}" for s in items)
        if tip:
            return f"{tip}\n{line}"
        return line

    activity_id = row.get("activity_id") or row.get("label", "")
    # Planned / Forecast dates
    planned_raw = row.get("bl_project_finish")
    planned_text = as_text(planned_raw)
    forecast_raw = row.get("finish")
    forecast_text = as_text(forecast_raw)
    planned_finish = planned_text or "--"
    forecast_finish = forecast_text or "--"

    # Schedule
    sched_entry = sched_lu.get(activity_id, {}) if sched_lu else {}
    sched_val = sched_entry.get("value")
    if isinstance(sched_val, (int, float)):
        planned_progress = sched_val
        sched_display = sched_entry.get("display") or f"{planned_progress:.2f}%"
    else:
        planned_progress = None
        sched_display = "?"
    schedule_tip = sched_entry.get("tip") if sched_entry else None
    if sched_display == "?":
        schedule_tip = "Schedule unavailable for this activity."
    elif not schedule_tip:
        schedule_tip = "Schedule % = Units (current week) / Budgeted Units"

    # Earned
    earned_raw = row.get("units_complete")
    if earned_raw is None or str(earned_raw).strip() == "":
        actual_progress = None
        earned_display = "?"
    else:
        actual_progress = parse_percent_float(earned_raw)
        earned_display = f"{actual_progress:.2f}%"
    earned_tip = (
        "Earned % = Units % Complete"
        if earned_display != "?"
        else "Earned unavailable: Units % Complete missing."
    )
    earned_tip = _append_tip_sources(
        earned_tip,
        [f"Units % Complete: {row.get('units_complete_cell')}" if row.get("units_complete_cell") else ""],
    )

    # SV = ecart
    if isinstance(actual_progress, (int, float)) and isinstance(planned_progress, (int, float)):
        sv_val = actual_progress - planned_progress
        sv_display = f"{sv_val:+.2f}%"
    else:
        sv_val = None
        sv_display = "?"
    sv_tip = "SV % = Earned % - Schedule %" if sv_display != "?" else "SV unavailable: missing values."
    sv_tip = _append_tip_sources(
        sv_tip,
        [
            f"Earned: {row.get('units_complete_cell')}" if row.get("units_complete_cell") else "",
            f"Schedule: {sched_entry.get('week_cell')}" if sched_entry else "",
            f"Budgeted Units: {sched_entry.get('budget_cell')}" if sched_entry else "",
        ],
        prefix="Sources",
    )

    # SPI = earned / schedule
    if isinstance(actual_progress, (int, float)) and isinstance(planned_progress, (int, float)) and planned_progress != 0:
        spi_val = actual_progress / planned_progress
        spi_display = f"{spi_val * 100:.1f} %"
    else:
        spi_val = None
        spi_display = "?"
    spi_tip = "SPI = Earned % / Schedule %" if spi_display != "?" else "SPI unavailable: missing values."
    spi_tip = _append_tip_sources(
        spi_tip,
        [
            f"Earned: {row.get('units_complete_cell')}" if row.get("units_complete_cell") else "",
            f"Schedule: {sched_entry.get('week_cell')}" if sched_entry else "",
            f"Budgeted Units: {sched_entry.get('budget_cell')}" if sched_entry else "",
        ],
        prefix="Sources",
    )

    # Delay/Ahead = glissement
    gliss_raw = row.get("variance_days")
    if gliss_raw is None or str(gliss_raw).strip() == "":
        delay_display = "?"
        delay_val = None
    else:
        try:
            delay_val = int(float(gliss_raw))
            delay_display = f"{delay_val} days"
        except Exception:
            delay_display = "?"
            delay_val = None
    delay_tip = (
        "Delay/Ahead = Variance - BL Project Finish Date (days)"
        if delay_display != "?"
        else "Delay/Ahead unavailable: variance missing."
    )
    delay_tip = _append_tip_sources(
        delay_tip,
        [f"Variance - BL Project Finish Date: {row.get('variance_days_cell')}" if row.get("variance_days_cell") else ""],
    )

    planned_tip = "Planned = BL Project Finish" if planned_text else "Planned unavailable: BL Project Finish missing."
    planned_tip = _append_tip_sources(
        planned_tip,
        [f"BL Project Finish: {row.get('bl_project_finish_cell')}" if row.get("bl_project_finish_cell") else ""],
    )
    forecast_tip = "Forecast = Finish" if forecast_text else "Forecast unavailable: Finish missing."
    forecast_tip = _append_tip_sources(
        forecast_tip,
        [f"Finish: {row.get('finish_cell')}" if row.get("finish_cell") else ""],
    )

    return {
        "planned_progress": planned_progress if planned_progress is not None else 0,
        "planned_progress_display": sched_display,
        "planned_progress_tip": schedule_tip,
        "actual_progress": actual_progress if actual_progress is not None else 0,
        "actual_progress_display": earned_display,
        "actual_progress_tip": earned_tip,
        "planned_start": "--",
        "planned_finish": planned_finish,
        "planned_tip": planned_tip,
        "forecast_finish": forecast_finish,
        "forecast_tip": forecast_tip,
        "delay_days": delay_val if delay_val is not None else "?",
        "delay_display": delay_display,
        "delay_val": delay_val,
        "delay_tip": delay_tip,
        "sv_pct": sv_val if sv_val is not None else 0,
        "sv_display": sv_display,
        "sv_val": sv_val,
        "sv_tip": sv_tip,
        "spi": spi_val if spi_val is not None else 0,
        "spi_display": spi_display,
        "spi_val": spi_val,
        "spi_tip": spi_tip,
    }

# ---------- Pages ----------
def render_dashboard():
    local_m = dict(m)
    local_weekly_progress = list(weekly_progress)
    local_current_week = current_week
    local_weekly_info = {}
    local_status_values = data["activities_status"]
    local_status_warnings = []
    local_status_error = None
    selected_key = None
    if activity_filter:
        selected_key = st.session_state.get("activity_select", activity_filter["default_key"])
        if selected_key not in activity_filter["filtered_options"]:
            selected_key = activity_filter["filtered_options"][0]
        st.session_state["active_activity_key"] = selected_key
        selected_row = activity_filter["activity_rows_map"][selected_key]
        mapped = compute_dashboard_metrics_from_activity(selected_row, schedule_lookup or {})
        if mapped:
            local_m.update(
                {
                    "planned_progress": mapped.get("planned_progress", 0),
                    "actual_progress": mapped.get("actual_progress", 0),
                    "planned_start": mapped.get("planned_start", "--"),
                    "planned_finish": mapped.get("planned_finish", "--"),
                    "forecast_finish": mapped.get("forecast_finish", "--"),
                    "delay_days": mapped.get("delay_days", "?"),
                    "delay_display": mapped.get("delay_display"),
                    "delay_val": mapped.get("delay_val"),
                    "sv_pct": mapped.get("sv_pct", 0),
                    "sv_display": mapped.get("sv_display"),
                    "sv_val": mapped.get("sv_val"),
                    "spi": mapped.get("spi", 0),
                    "spi_display": mapped.get("spi_display"),
                    "spi_val": mapped.get("spi_val"),
                    "planned_progress_tip": mapped.get("planned_progress_tip"),
                    "actual_progress_tip": mapped.get("actual_progress_tip"),
                    "planned_tip": mapped.get("planned_tip"),
                    "forecast_tip": mapped.get("forecast_tip"),
                    "delay_tip": mapped.get("delay_tip"),
                    "sv_tip": mapped.get("sv_tip"),
                    "spi_tip": mapped.get("spi_tip"),
                }
            )
        if shared_path and selected_row:
            activity_key = selected_row.get("activity_id") or selected_row.get("label", "")
            (weekly_series, weekly_info), ms = _time_call(
                _cached_weekly_progress,
                shared_path,
                file_cache_key,
                activity_key,
                column_mapping=st.session_state.get("column_mapping"),
                today_key=today_cache_key,
            )
            perf_stats["weekly_progress_dashboard"] = ms
            if weekly_series:
                local_weekly_progress = weekly_series
                local_current_week = (
                    weekly_info.get("current_week_date")
                    or weekly_info.get("week_date")
                    or weekly_info.get("current_week_label")
                    or local_current_week
                )
            local_weekly_info = weekly_info or {}
        if activity_filter.get("activity_rows") and selected_row:
            status_vals, status_warnings, status_error = compute_activity_status_breakdown(
                activity_filter["activity_rows"], selected_row.get("_idx")
            )
            local_status_values = status_vals
            local_status_warnings = status_warnings
            local_status_error = status_error

    company_logo = _custom_logo_data_uri("company")
    client_logo = _custom_logo_data_uri("client")
    header_logos: list[tuple[str, str, str]] = []
    if company_logo:
        header_logos.append(("company", "Company", company_logo))
    if client_logo:
        header_logos.append(("client", "Client", client_logo))

    if header_logos:
        with st.container(key="brand_logo_row_header"):
            logo_cols = st.columns(len(header_logos), gap="small")
            for col, (role, label, src) in zip(logo_cols, header_logos):
                with col:
                    with st.container(key=f"brand_logo_item_{role}"):
                        st.markdown(
                            f'<div class="brand-pill brand-pill--header" title="{html.escape(label)} logo">'
                            f'<img src="{src}" alt="{html.escape(label)} logo" /></div>',
                            unsafe_allow_html=True,
                        )
                        if st.button("×", key=f"brand_remove_{role}", help=f"Remove {label} logo"):
                            _remove_custom_logo(role)
                            st.session_state.pop(f"_logo_upload_{role}_key", None)
                            st.rerun()

    st.markdown(
        """
        <div class="pulse-hero">
          <div class="scurve-hero-title">▸ Progress Pulse</div>
          <div class="scurve-hero-sub">Planned vs actual status and schedule health</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    layout_top = st.columns([2.0, 2.8])

    with layout_top[0]:
        gauges_row = st.columns(2)
        with gauges_row[0]:
            planned_tip = local_m.get("planned_progress_tip")
            if planned_tip:
                st.markdown(
                    f"<div class='gauge-help' title='{html.escape(planned_tip)}'>ℹ</div>",
                    unsafe_allow_html=True,
                )
            st.plotly_chart(
                gauge_fig(
                    "Planned Progress",
                    local_m["planned_progress"],
                    "#4b6ff4",
                    tip=local_m.get("planned_progress_tip"),
                ),
                width="stretch",
                config={"displayModeBar": False, "responsive": False},
            )
        with gauges_row[1]:
            actual_tip = local_m.get("actual_progress_tip")
            if actual_tip:
                st.markdown(
                    f"<div class='gauge-help' title='{html.escape(actual_tip)}'>ℹ</div>",
                    unsafe_allow_html=True,
                )
            st.plotly_chart(
                gauge_fig(
                    "Actual Progress",
                    local_m["actual_progress"],
                    "#2fc192",
                    tip=local_m.get("actual_progress_tip"),
                ),
                width="stretch",
                config={"displayModeBar": False, "responsive": False},
            )

    with layout_top[1]:
        st.markdown("<div style='height:72px'></div>", unsafe_allow_html=True)
        row_a = st.columns(3)
        with row_a[0]:
            if activity_filter:
                active_key = selected_key or activity_filter["default_key"]
                selected_key = st.selectbox(
                    "Select activity",
                    activity_filter["filtered_options"],
                    index=activity_filter["filtered_options"].index(active_key),
                    format_func=lambda k: activity_filter["activity_display"].get(k, k),
                    key="activity_select",
                )
                st.session_state["active_activity_key"] = selected_key
        with row_a[1]:
            metric_card("Planned Finish", fmt_date(local_m["planned_finish"]), tip=local_m.get("planned_tip"))
        with row_a[2]:
            metric_card("Forecast Finish", fmt_date(local_m["forecast_finish"]), tip=local_m.get("forecast_tip"))

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        row_b = st.columns(3)
        with row_b[0]:
            delay_display = local_m.get("delay_display")
            if delay_display is None:
                delay_display = f"{local_m['delay_days']} days"
            delay_val = local_m.get("delay_val", local_m.get("delay_days"))
            delay_tone = None
            if isinstance(delay_val, (int, float)):
                delay_tone = "positive" if delay_val > 0 else "negative" if delay_val < 0 else None
            metric_card("Delay/Ahead", delay_display, tone=delay_tone, tip=local_m.get("delay_tip"))
        with row_b[1]:
            sv_display = local_m.get("sv_display")
            if sv_display is None:
                sv_display = fmt_pct(local_m["sv_pct"], signed=True, decimals=1)
            sv_val = local_m.get("sv_val", local_m.get("sv_pct"))
            sv_tone = pct_tone(sv_val) if isinstance(sv_val, (int, float)) else None
            if sv_display == "?":
                sv_tone = None
            metric_card("SV %", sv_display, tone=sv_tone, tip=local_m.get("sv_tip"))
        with row_b[2]:
            spi_display = local_m.get("spi_display")
            if spi_display is None:
                spi_pct = local_m["spi"] * 100 if local_m.get("spi") is not None else None
                spi_display = fmt_pct(spi_pct, decimals=1)
            spi_val = local_m.get("spi_val", local_m.get("spi"))
            spi_pct_val = spi_val * 100 if isinstance(spi_val, (int, float)) else None
            spi_tone = pct_tone(spi_pct_val) if isinstance(spi_pct_val, (int, float)) else None
            if spi_display == "?":
                spi_tone = None
            metric_card("SPI", spi_display, tone=spi_tone, tip=local_m.get("spi_tip"))

    with st.container():
        st.markdown(
            '<div class="chart-heading">▸ Weekly Momentum <span class="info-badge" title="Planned vs actual weekly % for the selected activity (actual appears when available).">ℹ</span></div>',
            unsafe_allow_html=True,
        )
        st.plotly_chart(
            weekly_progress_fig(local_weekly_progress, local_current_week),
            width="stretch",
            config={"displayModeBar": False, "responsive": False},
        )
        render_weekly_warnings(local_weekly_info)

    bottom = st.columns([1.7, 1.0])
    with bottom[0]:
        with st.container():
            st.markdown(
                '<div class="chart-heading">▸ Schedule Gap <span class="info-badge" title="Weekly Schedule Variance (Earned % minus Schedule %).">ℹ</span></div>',
                unsafe_allow_html=True,
            )
            st.plotly_chart(
                weekly_sv_fig(local_weekly_progress, local_current_week),
                width="stretch",
                config={"displayModeBar": False, "responsive": False},
            )

    with bottom[1]:
        with st.container():
            st.markdown(
                '<div class="chart-heading">▸ Activity Mix <span class="info-badge" title="Share of activities by status (placeholder until real mapping).">ℹ</span></div>',
                unsafe_allow_html=True,
            )
            st.plotly_chart(
                activities_status_fig(local_status_values, error_msg=local_status_error),
                width="stretch",
                config={"displayModeBar": False, "responsive": False},
            )
            if local_status_warnings:
                st.warning(
                    "Activities Status warnings:\n"
                    + "\n".join(f"- {w}" for w in local_status_warnings)
                )

    st.caption("Placeholder visuals with simulated data. Replace the sample data functions when real inputs are ready.")


def render_s_curve_page():

    with st.container():
        head_cols = st.columns([2.2, 1.2])
        with head_cols[0]:
            st.markdown(
                """
                <div class="scurve-hero-title">▸ Cumulative Progress</div>
                <div class="scurve-hero-sub">Cumulative planned vs actual vs forecast</div>
                """,
                unsafe_allow_html=True,
            )
        with head_cols[1]:
            if activity_filter:
                selected_key = st.session_state.get("activity_select", activity_filter["default_key"])
                if selected_key not in activity_filter["filtered_options"]:
                    selected_key = activity_filter["filtered_options"][0]
                selected_key = st.selectbox(
                    "Select activity",
                    activity_filter["filtered_options"],
                    index=activity_filter["filtered_options"].index(selected_key),
                    format_func=lambda k: activity_filter["activity_display"].get(k, k),
                    key="activity_select",
                )
                st.session_state["active_activity_key"] = selected_key

        weekly_series = []
        weekly_info = {}
        planned_hover = None
        actual_hover = None
        selected_row = None
        if activity_filter:
            selected_row = activity_filter["activity_rows_map"].get(selected_key)
        if shared_path and selected_row:
            activity_key = selected_row.get("activity_id") or selected_row.get("label", "")
            (weekly_series, weekly_info), ms = _time_call(
                _cached_weekly_progress,
                shared_path,
                file_cache_key,
                activity_key,
                column_mapping=st.session_state.get("column_mapping"),
                today_key=today_cache_key,
            )
            perf_stats["weekly_progress_scurve"] = ms

        if weekly_series:
            x = [row.get("week_date") for row in weekly_series]
            planned_hover = []
            planned_curve = []
            last_known = None
            for row in weekly_series:
                display = row.get("planned_cum_display") or "?"
                val = row.get("planned_cum")
                if isinstance(val, (int, float)):
                    capped = min(100.0, val)
                    last_known = capped
                    planned_curve.append(capped)
                    planned_hover.append(
                        _hover_with_tip(f"{capped:.2f}%", row.get("planned_cum_tip"))
                    )
                else:
                    if isinstance(last_known, (int, float)) and last_known >= 100:
                        planned_curve.append(100.0)
                        planned_hover.append(
                            _hover_with_tip("100.00%", row.get("planned_cum_tip"))
                        )
                    else:
                        planned_curve.append(None)
                        planned_hover.append(
                            _hover_with_tip(display, row.get("planned_cum_tip"))
                        )

            n = len(x)
            actual_curve = []
            actual_hover = []
            last_actual = None
            for row in weekly_series:
                budget_units = row.get("budgeted_units")
                budget_cell = row.get("budgeted_units_cell")
                cum_units = row.get("actual_cum_units")
                val = (
                    (cum_units / budget_units) * 100.0
                    if isinstance(cum_units, (int, float))
                    and isinstance(budget_units, (int, float))
                    and budget_units != 0
                    else None
                )
                display = f"{val:.2f}%" if isinstance(val, (int, float)) else "?"
                if isinstance(val, (int, float)):
                    capped = min(100.0, val)
                    last_actual = capped
                    actual_curve.append(capped)
                    tip = "Actual % = Cum Actual Units / Budgeted Units"
                    sources = []
                    week_cell = row.get("actual_week_cell")
                    if week_cell:
                        sources.append(f"Week: {week_cell}")
                    if budget_cell:
                        sources.append(f"Budgeted Units: {budget_cell}")
                    if sources:
                        tip += "\nCells:\n" + "\n".join(f"- {s}" for s in sources)
                    actual_hover.append(_hover_with_tip(f"{capped:.2f}%", tip))
                else:
                    if isinstance(last_actual, (int, float)) and last_actual >= 100:
                        actual_curve.append(100.0)
                        actual_hover.append(_hover_with_tip("100.00%", None))
                    else:
                        actual_curve.append(None)
                        actual_hover.append(_hover_with_tip(display, None))
            weekly_actual = [
                round(actual_curve[i] - actual_curve[i - 1], 2)
                if i > 0
                and isinstance(actual_curve[i], (int, float))
                and isinstance(actual_curve[i - 1], (int, float))
                else (actual_curve[i] if isinstance(actual_curve[i], (int, float)) else None)
                for i in range(n)
            ]

            forecast_curve = [None] * n
            forecast_hover = ["" for _ in range(n)]

            def _forecast_pct(row: dict) -> float | None:
                cum_units = row.get("forecast_cum_units")
                budget_units = row.get("budgeted_units")
                if (
                    isinstance(cum_units, (int, float))
                    and isinstance(budget_units, (int, float))
                    and budget_units != 0
                ):
                    return (cum_units / budget_units) * 100.0
                return None

            def _forecast_tip(row: dict) -> str | None:
                sources = []
                week_cell = row.get("forecast_week_cell")
                units_cell = row.get("budgeted_units_cell")
                if week_cell:
                    sources.append(f"Week: {week_cell}")
                if units_cell:
                    sources.append(f"Budgeted Units: {units_cell}")
                if not sources:
                    return None
                tip = "Forecast % = Cum Remaining Early Units / Budgeted Units"
                tip += "\nCells:\n" + "\n".join(f"- {s}" for s in sources)
                return tip

            third_vals = [_forecast_pct(row) for row in weekly_series]
            last_actual_idx = None
            last_actual_val = None
            for idx, row in enumerate(weekly_series):
                budget_units = row.get("budgeted_units")
                cum_units = row.get("actual_cum_units")
                val = (
                    (cum_units / budget_units) * 100.0
                    if isinstance(cum_units, (int, float))
                    and isinstance(budget_units, (int, float))
                    and budget_units != 0
                    else None
                )
                if isinstance(val, (int, float)):
                    last_actual_idx = idx
                    last_actual_val = min(100.0, val)

            first_forecast_idx = None
            if last_actual_idx is not None:
                for idx in range(last_actual_idx, n):
                    if isinstance(third_vals[idx], (int, float)):
                        first_forecast_idx = idx
                        break

            case1 = False
            case2 = False
            if last_actual_idx is not None and first_forecast_idx is not None:
                last_date = weekly_series[last_actual_idx].get("week_date")
                first_date = weekly_series[first_forecast_idx].get("week_date")
                if isinstance(last_date, date) and isinstance(first_date, date):
                    gap_days = (first_date - last_date).days
                    case1 = gap_days == 7
                    case2 = gap_days == 0

            if case2 and isinstance(last_actual_val, (int, float)):
                forecast_curve[last_actual_idx] = last_actual_val
                forecast_hover[last_actual_idx] = _hover_with_tip(
                    f"{last_actual_val:.2f}%",
                    _forecast_tip(weekly_series[last_actual_idx]) or
                    "Forecast starts at last actual.",
                )
                prev_forecast = last_actual_val
                next_idx = last_actual_idx + 1
                if next_idx < n:
                    v0 = third_vals[first_forecast_idx]
                    v1 = third_vals[next_idx]
                    if isinstance(v0, (int, float)) and isinstance(v1, (int, float)):
                        prev_forecast = min(100.0, prev_forecast + v0 + v1)
                        forecast_curve[next_idx] = prev_forecast
                        forecast_hover[next_idx] = _hover_with_tip(
                            f"{prev_forecast:.2f}%",
                            _forecast_tip(weekly_series[next_idx]),
                        )
                    else:
                        forecast_curve[next_idx] = None
                        forecast_hover[next_idx] = ""
                for idx in range(last_actual_idx + 2, n):
                    prev_third = third_vals[idx - 1]
                    curr_third = third_vals[idx]
                    if not isinstance(prev_third, (int, float)) or not isinstance(curr_third, (int, float)):
                        forecast_curve[idx] = None
                        forecast_hover[idx] = ""
                        continue
                    delta = curr_third - prev_third
                    prev_forecast = min(100.0, prev_forecast + delta)
                    forecast_curve[idx] = prev_forecast
                    forecast_hover[idx] = _hover_with_tip(
                        f"{prev_forecast:.2f}%",
                        _forecast_tip(weekly_series[idx]),
                    )
            elif case1 and isinstance(last_actual_val, (int, float)):
                forecast_curve[last_actual_idx] = last_actual_val
                forecast_hover[last_actual_idx] = _hover_with_tip(
                    f"{last_actual_val:.2f}%",
                    _forecast_tip(weekly_series[last_actual_idx]) or
                    "Forecast starts at last actual.",
                )
                prev_forecast = last_actual_val
                for idx in range(last_actual_idx + 1, n):
                    prev_third = third_vals[idx]
                    if prev_third is None:
                        forecast_curve[idx] = None
                        forecast_hover[idx] = ""
                        continue
                    if idx == first_forecast_idx:
                        delta = prev_third
                    else:
                        prev_prev_third = third_vals[idx - 1]
                        if prev_prev_third is None:
                            forecast_curve[idx] = None
                            forecast_hover[idx] = ""
                            continue
                        delta = prev_third - prev_prev_third
                    prev_forecast = min(100.0, prev_forecast + delta)
                    forecast_curve[idx] = prev_forecast
                    forecast_hover[idx] = _hover_with_tip(
                        f"{prev_forecast:.2f}%",
                        _forecast_tip(weekly_series[idx]),
                    )
            else:
                planned_last = None
                for v in reversed(planned_curve):
                    if isinstance(v, (int, float)):
                        planned_last = v
                        break
                if isinstance(planned_last, (int, float)) or isinstance(last_actual, (int, float)):
                    base = max([v for v in [planned_last, last_actual] if isinstance(v, (int, float))])
                    forecast_target = min(100.0, base + 5.0)
                    if n > 1:
                        forecast_curve = [round(forecast_target * (i / (n - 1)), 2) for i in range(n)]
                    else:
                        forecast_curve = [forecast_target]
        else:
            x, weekly_actual, actual_curve, planned_curve, forecast_curve = demo_series()
            forecast_hover = None
            actual_hover = None

        fig = s_curve(
            x,
            weekly_actual,
            actual_curve,
            planned_curve,
            forecast_curve,
            planned_hover=planned_hover,
            actual_hover=actual_hover,
            forecast_hover=forecast_hover,
        )
        fig.update_layout(title_text="")

        st.markdown('<div class="scurve-hero-chart-title">▸ Progress Curve</div>', unsafe_allow_html=True)
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False, "responsive": False})
        st.markdown(
            '<div class="scurve-hero-note">Planned, actual, and forecast are all % of Budgeted Units. Actual uses Cum Actual Units; forecast uses Cum Remaining Early Units when available.</div>',
            unsafe_allow_html=True,
        )
        render_weekly_warnings(weekly_info, label="S-Curve")




if page == "Dashboard":
    render_dashboard()
elif page == "S-Curve":
    render_s_curve_page()
