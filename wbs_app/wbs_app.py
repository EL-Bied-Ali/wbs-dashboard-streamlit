# wbs_app.py - Compact layout with sidebar preserved
import os
import math
import sys
import tempfile
import html
from pathlib import Path
from typing import Any

import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from auth_google import require_login, render_auth_sidebar
from activity_filters import build_activity_filter_sidebar, ROOT_ACTIVITY_ALL
from shared_excel import (
    persist_shared_excel_state,
    restore_shared_excel_state,
    set_default_excel_if_missing,
)
from extract_wbs_json import (
    extract_all_wbs,
    detect_expected_tables,
    compare_activity_ids,
    build_preview_rows,
    build_schedule_lookup,
    parse_percent_float,
    as_text,
    get_table_headers,
    suggest_column_mapping,
    SUMMARY_REQUIRED_FIELDS,
    SUMMARY_OPTIONAL_FIELDS,
    ASSIGN_REQUIRED_FIELDS,
    ASSIGN_OPTIONAL_FIELDS,
)
from theme import inject_theme

_icon_path = ROOT / "chronoplan_logo.png"
st.set_page_config(
    page_title="Wibis",
    page_icon=str(_icon_path) if _icon_path.exists() else "🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(
    "<style>[data-testid='stSidebarNav']{display:none !important;}</style>",
    unsafe_allow_html=True,
)
user = require_login()
render_auth_sidebar(user, show_branding=False)
inject_theme()
PREVIEW_ENABLED = os.getenv("PREVIEW_MODE", "").strip().lower() in {"1", "true", "yes", "on"}

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

def _render_excel_format_help():
    with st.sidebar.expander("Excel format guide", expanded=False):
        st.page_link("pages/1_Excel_Guide.py", label="Open full guide")
        st.markdown(
            "\n".join(
                [
                    "**Expected structure**",
                    "- Two tables: Activity Summary + Resource Assignments (any sheets).",
                    "- Activity IDs must match across both tables, including indentation.",
                    "- Activity Summary required: Activity ID, Activity Name, Activity Status, BL Project Finish (or Planned Finish), Finish (or Forecast Finish), Units % Complete, Variance - BL Project Finish Date, Budgeted Labor Units.",
                    "- Leaf rule: Activity Name only for leaf activities; when Activity Name is filled, Activity Status must be filled.",
                    "- Resource Assignments required: Activity ID, Budgeted Units, Spreadsheet Field (optional Start/Finish).",
                    "- Spreadsheet Field values: Cum Budgeted Units, Cum Actual Units, Cum Remaining Early Units.",
                    "- Weekly date columns (week start) are used for curves.",
                    "",
                    "**Tips**",
                    "- One header row per table, no merged cells.",
                    "- Dates can be Excel dates or YYYY-MM-DD.",
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

def _maybe_open_mapping_dialog(source_path: str | None) -> None:
    if not source_path:
        return
    _sync_mapping_for_upload()
    mapping = _init_column_mapping_state()

    summary_headers = get_table_headers(source_path, "activity_summary")
    assign_headers = get_table_headers(source_path, "resource_assignments")
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

def _minify(s:str)->str: return "".join(l.strip() for l in s.splitlines())
def _sf(x): 
    try: return float(x)
    except: return 0.0
def _pct(x,signed=False):
    try:
        v=float(x); sign="+" if signed and v>=0 else ""; t=f"{v:.2f}".rstrip("0").rstrip(".")
        return f"{sign}{t}%"
    except: return str(x)
def _signed_class(val, display=None):
    if display == "?" or val is None:
        return "muted"
    return "ok" if val >= 0 else "bad"
def _fmt_signed(val, display=None, tip=None):
    if display is None:
        if val is None:
            display = "?"
        else:
            display = _pct(val, True)
    cls = _signed_class(val, display)
    title = f' title="{tip}"' if tip else ""
    return f'<b class="{cls}"{title}>{display}</b>'
def _fmt_days(val, display=None, tip=None):
    if display is None:
        if val is None:
            display = "?"
        else:
            display = f"{int(val)}d"
    cls = _signed_class(val, display)
    title = f' title="{tip}"' if tip else ""
    return f'<b class="{cls}"{title}>{display}</b>'
def _fmt_text(val, display=None, tip=None):
    if display is None:
        display = val if val not in (None, "") else "?"
    cls = _signed_class(None, display)
    title = f' title="{tip}"' if tip else ""
    return f'<b class="{cls}"{title}>{display}</b>'
def _to_j(v): 
    try: return float(str(v).replace("j","").strip())
    except: return 0.0
def _bar(v, color, variant: int | None = None, display: str | None = None, tip: str | None = None):
    variant = 0 if variant is None else int(variant) % 2
    val = v if isinstance(v, (int, float)) else None
    width = max(0, min(100, val if val is not None else 0))
    if display is None:
        display = f"{width:.2f}%"
    title = f' title="{tip}"' if tip else ""
    return (
        f'<span class="mbar-wrap"{title}>'
        f'<span class="mbar"><span class="mfill anim av{variant} {color}" style="--to:{width}%;"></span></span>'
        f'<span class="mval">{display}</span>'
        f'</span>'
    )

def _truncate_label(text: str, max_len: int = 42) -> str:
    if not text:
        return ""
    text = str(text)
    if len(text) <= max_len:
        return text
    if max_len <= 3:
        return text[:max_len]
    return text[: max_len - 3] + "..."

def _find_node_by_activity_id(root: dict, activity_id: str) -> dict | None:
    if not root or not activity_id:
        return None
    target = str(activity_id).strip()
    stack = [root]
    while stack:
        node = stack.pop()
        node_id = str(node.get("activity_id") or node.get("label", "")).strip()
        if node_id == target:
            return node
        children = node.get("children") or []
        stack.extend(reversed(children))
    return None

def _rebase_tree_levels(node: dict, delta: int) -> dict:
    if not node:
        return {}
    level = int(node.get("level", 1))
    rebased = {
        **node,
        "level": max(1, level - delta),
        "children": [_rebase_tree_levels(ch, delta) for ch in (node.get("children") or [])],
    }
    return rebased

def _normalize_label(value: str) -> str:
    return " ".join(str(value or "").replace("\u00a0", " ").split()).lower()

def _normalize_activity_id(value: str) -> str:
    return " ".join(str(value or "").replace("\u00a0", " ").split()).lower()

def _extract_activity_id(label: str) -> str:
    if not label:
        return ""
    if " - " in label:
        return label.split(" - ", 1)[0].strip()
    parts = str(label).split()
    return parts[0].strip() if parts else label.strip()

def _build_display_label_maps(
    rows: list[dict],
) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    label_by_id: dict[str, str] = {}
    label_by_name: dict[str, str] = {}
    name_by_id: dict[str, str] = {}
    for row in rows:
        activity_id = str(row.get("activity_id") or "").strip()
        display = row.get("display_label") or row.get("label") or activity_id
        if activity_id and display:
            label_by_id[_normalize_activity_id(activity_id)] = display
            if " - " in display:
                name_by_id[_normalize_activity_id(activity_id)] = display.split(" - ", 1)[1].strip()
        name = str(row.get("activity_name") or "").strip()
        if not name and display and " - " in display:
            name = display.split(" - ", 1)[1].strip()
        if name and display:
            label_by_name[_normalize_label(name)] = display
            if activity_id:
                name_by_id[_normalize_activity_id(activity_id)] = name
    return label_by_id, label_by_name, name_by_id

def _apply_display_labels(
    node: dict,
    label_by_id: dict[str, str],
    label_by_name: dict[str, str],
    name_by_id: dict[str, str],
) -> None:
    if not node or (not label_by_id and not label_by_name):
        return
    activity_id = str(node.get("activity_id") or "").strip()
    if activity_id and " - " in activity_id:
        activity_id = activity_id.split(" - ", 1)[0].strip()
    activity_key = _normalize_activity_id(activity_id)
    if not activity_key:
        activity_key = _normalize_activity_id(_extract_activity_id(node.get("label", "")))
    display = label_by_id.get(activity_key)
    if not display:
        label = str(node.get("label") or "").strip()
        if " - " in label:
            label_id = label.split(" - ", 1)[0].strip()
            display = label_by_id.get(_normalize_activity_id(label_id))
            if not display:
                label_name = label.split(" - ", 1)[1].strip()
                display = label_by_name.get(_normalize_label(label_name))
        if not display and label:
            display = label_by_name.get(_normalize_label(label))
    if not display and activity_key:
        name = name_by_id.get(activity_key)
        if name:
            display = f"{activity_id or _extract_activity_id(node.get('label', ''))} - {name}".strip()
    if display:
        node["label"] = display
    for child in node.get("children") or []:
        _apply_display_labels(child, label_by_id, label_by_name, name_by_id)

def _title_span(full_label: str, display_label: str) -> str:
    safe_display = html.escape(display_label)
    safe_full = html.escape(full_label)
    title_attr = f' title="{safe_full}"' if safe_display != safe_full else ""
    return f'<span class="title"{title_attr}>{safe_display}</span>'

def render_detail_table(node:dict, anim_variant:int=0, truncate_labels: bool = True):
    rows=[]
    base_level=int(node.get("level", 2))

    def _collect_rows(parent:dict):
        for ch in (parent.get("children") or []):
            m=ch.get("metrics") or {}
            lvl=int(ch.get("level", base_level + 1))
            depth=max(0, lvl - base_level)
            depth_display = min(depth, 6)
            full_label = ch.get("label","")
            display_label = _truncate_label(full_label) if truncate_labels else full_label
            rows.append(dict(
                label=display_label,
                label_full=full_label,
                planned=m.get("planned_finish",""),
                planned_display=m.get("planned_display"),
                planned_tip=m.get("planned_tip"),
                forecast=m.get("forecast_finish",""),
                forecast_display=m.get("forecast_display"),
                forecast_tip=m.get("forecast_tip"),
                schedule=m.get("schedule"),
                schedule_display=m.get("schedule_display"),
                schedule_tip=m.get("schedule_tip"),
                earned=m.get("earned", m.get("units", 0)),
                earned_display=m.get("earned_display"),
                earned_tip=m.get("earned_tip"),
                ecart=m.get("ecart"),
                ecart_display=m.get("ecart_display"),
                ecart_tip=m.get("ecart_tip"),
                impact=m.get("impact"),
                impact_display=m.get("impact_display"),
                impact_tip=m.get("impact_tip"),
                gliss=m.get("glissement"),
                gliss_display=m.get("glissement_display"),
                gliss_tip=m.get("glissement_tip"),
                depth=depth_display,
            ))
            _collect_rows(ch)

    _collect_rows(node)
    def sgn(v, display=None, tip=None): 
        if display is None:
            if v is None:
                display = "?"
            else:
                display = f'{("+" if v>0 else "")}{v:.2f}%'
        cls = _signed_class(v, display)
        title = f' title="{tip}"' if tip else ""
        return f'<span class="{cls}"{title}>{display}</span>'
    trs=[]
    for r in rows:
        label_text = html.escape(r.get("label",""))
        label_full = html.escape(r.get("label_full",""))
        label_title = f' title="{label_full}"' if label_full and label_full != label_text else ""
        trs.append(_minify(f"""
        <tr class="depth-{r['depth']}">
          <td class="lvl depth-{r['depth']}" style="--indent:{r['depth']};"><span class="indent"><span class="dot"></span><span class="label"{label_title}>{label_text}</span></span></td>
          <td class="col-date">{_fmt_text(r['planned'], r.get('planned_display'), r.get('planned_tip'))}</td>
          <td class="col-date">{_fmt_text(r['forecast'], r.get('forecast_display'), r.get('forecast_tip'))}</td>
          <td class="col-bar">{_bar(r['schedule'],'blue', anim_variant, display=r.get('schedule_display'), tip=r.get('schedule_tip'))}</td>
          <td class="col-bar">{_bar(r['earned'],'green', anim_variant, display=r.get('earned_display'), tip=r.get('earned_tip'))}</td>
          <td class="col-sign">{sgn(r['ecart'], r.get('ecart_display'), r.get('ecart_tip'))}</td>
          <td class="col-sign">{sgn(r['impact'], r.get('impact_display'), r.get('impact_tip'))}</td>
          <td class="col-gliss">{_fmt_days(r["gliss"], r.get("gliss_display"), r.get("gliss_tip"))}</td>
        </tr>"""))
    st.markdown(_minify(f"""
    <div class="table-card compact">
      <div class="table-wrap">
        <table class="neo">
          <thead><tr>
            <th></th><th>Planned</th><th>Forecast</th><th>Schedule</th><th>Earned</th><th>+Variance</th><th>Impact</th><th>Slip</th>
          </tr></thead>
          <tbody>{''.join(trs)}</tbody>
        </table>
      </div>
    </div>
    """), unsafe_allow_html=True)

def render_barchart(node:dict, chart_key:str|None=None, truncate_labels: bool = True)->bool:
    labels_full=[]; labels_display=[]; schedule=[]; earned=[]; schedule_text=[]; earned_text=[]
    for ch in (node.get("children") or []):
        full_label = ch.get("label","")
        display_label = _truncate_label(full_label) if truncate_labels else full_label
        labels_full.append(full_label)
        labels_display.append(display_label)
        m=ch.get("metrics") or {}
        sched_val = m.get("schedule")
        if isinstance(sched_val, (int, float)):
            schedule.append(sched_val)
            schedule_text.append(f"{sched_val:.1f}%")
        else:
            schedule.append(0)
            schedule_text.append("")
        earn_val = m.get("earned", m.get("units", 0))
        if isinstance(earn_val, (int, float)):
            earned.append(earn_val)
            earned_text.append(f"{earn_val:.1f}%")
        else:
            earned.append(0)
            earned_text.append("")
    if not labels_full: return False
    vmax=max([0]+schedule+earned); ymax=100 if vmax<=100 else math.ceil(vmax/5)*5
    c_text="#e5e7eb"; c_grid="rgba(42,59,98,.55)"; c_sched="#3b82f6"; c_earn="#22c55e"
    n=len(labels_full); idx=list(range(n)); d=0.16; w=0.26; gloss=0.45
    fig=go.Figure()
    fig.add_bar(name="Schedule %", x=[i-d for i in idx], y=[v*1.02 for v in schedule], width=w,
                marker=dict(color=c_sched), opacity=1, hoverinfo="skip", showlegend=False, cliponaxis=False)
    fig.add_bar(name="Schedule %", x=[i-d for i in idx], y=schedule, width=w,
                marker=dict(color=f"rgba(96,165,250,{gloss})", line=dict(color="#93c5fd", width=0.8)),
                text=schedule_text, textposition="outside", textfont=dict(size=11, color=c_text),
                hovertemplate="<b>%{customdata}</b><br>Schedule: %{y:.2f}%<extra></extra>", customdata=labels_full, cliponaxis=False)
    fig.add_bar(name="Earned %", x=[i+d for i in idx], y=[v*1.02 for v in earned], width=w,
                marker=dict(color=c_earn), opacity=1, hoverinfo="skip", showlegend=False, cliponaxis=False)
    fig.add_bar(name="Earned %", x=[i+d for i in idx], y=earned, width=w,
                marker=dict(color=f"rgba(34,197,94,{gloss})", line=dict(color="#86efac", width=0.8)),
                text=earned_text, textposition="outside", textfont=dict(size=11, color=c_text),
                hovertemplate="<b>%{customdata}</b><br>Earned: %{y:.2f}%<extra></extra>", customdata=labels_full, cliponaxis=False)
    shapes=[]
    if ymax==100: shapes.append(dict(type="line", xref="paper", x0=0, x1=1, y0=100, y1=100, line=dict(width=1, dash="dot", color=c_grid)))
    fig.update_xaxes(type="linear", tickmode="array", tickvals=idx, ticktext=labels_display,
                     tickfont=dict(size=12, color=c_text), range=[-0.6, n-0.4], showgrid=False, zeroline=False)
    fig.update_layout(barmode="overlay", bargap=0.3, height=300, margin=dict(l=8,r=18,t=6,b=44),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(size=12, color=c_text),
        legend=dict(orientation="h", y=-0.28, x=0.5, xanchor="center", itemclick=False, itemdoubleclick=False,
                    font=dict(size=11, color="#cbd5e1")),
        yaxis=dict(title="", range=[0, ymax*1.08], ticksuffix="%", dtick=25 if ymax==100 else None,
                   showgrid=True, gridcolor=c_grid, zeroline=False),
        hovermode="closest", hoverlabel=dict(bgcolor="#0f172a", font=dict(color=c_text, size=11)), shapes=shapes,
        transition=dict(duration=850, easing="cubic-in-out"))
    element_key = chart_key or f"plt_{len(labels_full)}"
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


def _h1(label, m, anim_variant:int=0, display_label: str | None = None):
    planned = m.get("planned_finish","")
    planned_display = m.get("planned_display")
    planned_tip = m.get("planned_tip")
    forecast = m.get("forecast_finish","")
    forecast_display = m.get("forecast_display")
    forecast_tip = m.get("forecast_tip")
    sched_v  = m.get("schedule")
    sched_display = m.get("schedule_display")
    sched_tip = m.get("schedule_tip")
    earn_v = m.get("earned", m.get("units", 0))
    earn_display = m.get("earned_display")
    earn_tip = m.get("earned_tip")
    ecart_v  = m.get("ecart")
    ecart_display = m.get("ecart_display")
    ecart_tip = m.get("ecart_tip")
    impact_v = m.get("impact")
    impact_display = m.get("impact_display")
    impact_tip = m.get("impact_tip")
    gl = m.get("glissement")
    gl_display = m.get("glissement_display")
    gl_tip = m.get("glissement_tip")
    label_html = _title_span(label, display_label or label)
    return _minify(f"""
    <div class="hero compact">
      <div class="n1-grid">
        <div class="n1g-label"><span class="dot"></span>{label_html}</div>
        <div class="n1g-cell"><span class="small">Planned</span>{_fmt_text(planned, planned_display, planned_tip)}</div>
        <div class="n1g-cell"><span class="small">Forecast</span>{_fmt_text(forecast, forecast_display, forecast_tip)}</div>
        <div class="n1g-cell"><span class="small">Schedule</span>{_bar(sched_v,'blue', anim_variant, display=sched_display, tip=sched_tip)}</div>
        <div class="n1g-cell"><span class="small">Earned</span>{_bar(earn_v,'green', anim_variant, display=earn_display, tip=earn_tip)}</div>
        <div class="n1g-cell"><span class="small">+Variance</span>{_fmt_signed(ecart_v, ecart_display, ecart_tip)}</div>
        <div class="n1g-cell"><span class="small">Impact</span>{_fmt_signed(impact_v, impact_display, impact_tip)}</div>
        <div class="n1g-cell"><span class="small">Slip</span>{_fmt_days(gl, gl_display, gl_tip)}</div>
      </div>
    </div>""")

def _h2(label, level, m, anim_variant:int=0, leaf_html: str = "", display_label: str | None = None):
    planned = m.get("planned_finish","")
    planned_display = m.get("planned_display")
    planned_tip = m.get("planned_tip")
    forecast = m.get("forecast_finish","")
    forecast_display = m.get("forecast_display")
    forecast_tip = m.get("forecast_tip")
    sched_v  = m.get("schedule")
    sched_display = m.get("schedule_display")
    sched_tip = m.get("schedule_tip")
    earn_v = m.get("earned", m.get("units", 0))
    earn_display = m.get("earned_display")
    earn_tip = m.get("earned_tip")
    ecart_v  = m.get("ecart")
    ecart_display = m.get("ecart_display")
    ecart_tip = m.get("ecart_tip")
    impact_v = m.get("impact")
    impact_display = m.get("impact_display")
    impact_tip = m.get("impact_tip")
    gl = m.get("glissement")
    gl_display = m.get("glissement_display")
    gl_tip = m.get("glissement_tip")
    indent = max(0, int(level) - 2) * 16
    label_html = _title_span(label, display_label or label)
    return _minify(f"""
    <div class="n2-grid compact depth-{level}" style="margin-left:{indent}px;">
      <div class="n2g-label"><span class="dot"></span>{label_html}{leaf_html}</div>
      <div class="n2g-cell"><span class="small">Planned</span>{_fmt_text(planned, planned_display, planned_tip)}</div>
      <div class="n2g-cell"><span class="small">Forecast</span>{_fmt_text(forecast, forecast_display, forecast_tip)}</div>
        <div class="n2g-cell"><span class="small">Schedule</span>{_bar(sched_v,'blue', anim_variant, display=sched_display, tip=sched_tip)}</div>
        <div class="n2g-cell"><span class="small">Earned</span>{_bar(earn_v,'green', anim_variant, display=earn_display, tip=earn_tip)}</div>
      <div class="n2g-cell"><span class="small">+Variance</span>{_fmt_signed(ecart_v, ecart_display, ecart_tip)}</div>
      <div class="n2g-cell"><span class="small">Impact</span>{_fmt_signed(impact_v, impact_display, impact_tip)}</div>
      <div class="n2g-cell gliss"><span class="small">Slip</span>{_fmt_days(gl, gl_display, gl_tip)}</div>
    </div>""")

def _slug(s:str)->str: return "".join(ch if ch.isalnum() else "_" for ch in s)
def _node_base(label:str, depth:int, wbs_key:str, path:list[str], node_id:int|None=None)->str:
    label_key = f"{label}__{node_id}" if node_id is not None else label
    full = "__".join(_slug(p) for p in (path + [label_key]) if p)
    return f"n2_open--{full}_{depth}__{wbs_key}"

def _max_tree_depth(node: dict, depth: int = 1) -> int:
    children = node.get("children") or []
    if not children:
        return depth
    return max(_max_tree_depth(child, depth + 1) for child in children)

def _collect_nodes_by_depth(
    node: dict,
    target_depth: int,
    current_depth: int = 1,
    path: list[str] | None = None,
    node_id: int | None = None,
) -> list[tuple[dict, list[str], int | None]]:
    path = path or []
    label = node.get("label", "")
    label_key = f"{label}__{node_id}" if node_id is not None else label
    if current_depth == target_depth:
        return [(node, path, node_id)]
    children = node.get("children") or []
    next_path = path + [label_key]
    results: list[tuple[dict, list[str], int | None]] = []
    for idx, child in enumerate(children):
        results.extend(
            _collect_nodes_by_depth(
                child,
                target_depth,
                current_depth + 1,
                next_path,
                node_id=idx,
            )
        )
    return results

def render_node(
    node:dict,
    depth:int,
    anim_seq:int=0,
    wbs_key:str="wbs",
    debug:bool=False,
    path:list[str]|None=None,
    node_id:int|None=None,
    max_depth:int|None=None,
    truncate_labels: bool = True,
    level_offset: int = 0,
):
    path = path or []
    label=node.get("label",""); level=int(node.get("level", depth)); metrics=node.get("metrics") or {}
    if level_offset:
        level = max(1, level - level_offset + 1)
    display_label = _truncate_label(label) if truncate_labels else label
    children = node.get("children") or []
    if max_depth is not None and depth >= max_depth:
        children = []
    has_children=bool(children)
    base=_node_base(label, depth, wbs_key, path, node_id=node_id); ver_key=f"{base}__ver"
    chart_hide_key = f"{base}__chart_hidden"
    view_version = (anim_seq + st.session_state.get(ver_key, 0)) % 2
    if base not in st.session_state:
        st.session_state[base] = True if depth == 1 else False
    if chart_hide_key not in st.session_state:
        st.session_state[chart_hide_key] = False
    if ver_key not in st.session_state: st.session_state[ver_key]=0
    bar_variant = (anim_seq + depth) % 2
    if depth == 1:
        st.markdown(_h1(label, metrics, bar_variant, display_label=display_label), unsafe_allow_html=True)
    else:
        leaf_html = ""
        if not has_children and st.session_state.get("show_leaf_badges"):
            leaf_html = '<span class="leaf-badge" title="No children">🍃</span>'
        with st.container(key=f"{base}__rowwrap"):
            st.markdown(_h2(label,level,metrics, bar_variant, leaf_html=leaf_html, display_label=display_label), unsafe_allow_html=True)
            if has_children:
                if st.button(" ", key=f"{base}__rowbtn", width="stretch"):
                    st.session_state[base]=not st.session_state[base]; st.session_state[ver_key]+=1
    if debug:
        st.caption(f"[dbg] base={base} open={st.session_state.get(base)} ver={st.session_state.get(ver_key)} view={view_version} anim_seq={anim_seq}")
    open_self = True if depth == 1 else bool(st.session_state.get(base, False))
    label_key = f"{label}__{node_id}" if node_id is not None else label
    next_path = path + [label_key]
    if has_children and open_self:
        for idx, child in enumerate(children):
            render_node(
                child,
                depth + 1,
                anim_seq,
                wbs_key,
                debug=debug,
                path=next_path,
                node_id=idx,
                max_depth=max_depth,
                truncate_labels=truncate_labels,
                level_offset=level_offset,
            )
        child_open = any(
            st.session_state.get(_node_base(ch.get("label",""), depth + 1, wbs_key, next_path, node_id=idx), False)
            for idx, ch in enumerate(children)
        )
        show_summary_chart = len(children) > 1 and not child_open
        if show_summary_chart and depth >= 1:
            with st.container(key=f"{base}__chartbar"):
                col_a, col_b = st.columns([0.85, 0.15])
                with col_b:
                    hidden_now = st.session_state[chart_hide_key]
                    if st.button("Show / Hide", key=f"{base}__hide_chart"):
                        st.session_state[chart_hide_key] = not hidden_now
                        if hidden_now:
                            st.session_state[ver_key] += 1
            if not st.session_state[chart_hide_key]:
                with st.container(key=f"{base}__chartwrap_v{view_version}"):
                    render_barchart(node, chart_key=f"{base}__chart", truncate_labels=truncate_labels)


def render_all(
    root:dict,
    anim_seq:int=0,
    wbs_key:str="wbs",
    debug:bool=False,
    max_depth:int|None=None,
    truncate_labels: bool = True,
    start_depth: int = 0,
):
    with st.container(key=f"hero_wrap__{anim_seq%2}"):
        start_depth = max(0, int(start_depth or 0))
        target_depth = start_depth + 1
        level_offset = start_depth
        if start_depth <= 0:
            render_node(
                root,
                1,
                anim_seq,
                wbs_key,
                debug=debug,
                max_depth=max_depth,
                truncate_labels=truncate_labels,
                level_offset=level_offset,
            )
        else:
            nodes = _collect_nodes_by_depth(root, target_depth)
            if not nodes:
                st.info("No nodes available at the selected start depth.")
            for node, path, node_id in nodes:
                render_node(
                    node,
                    target_depth,
                    anim_seq,
                    wbs_key,
                    debug=debug,
                    path=path,
                    node_id=node_id,
                    max_depth=max_depth,
                    truncate_labels=truncate_labels,
                    level_offset=level_offset,
                )
    st.divider()

# ===== Sidebar: importer (unchanged) =====
st.sidebar.markdown('<div class="sidebar-nav-title">Navigation</div>', unsafe_allow_html=True)
st.sidebar.page_link("app.py", label="Project Progress")
st.sidebar.page_link("pages/3_S_Curve.py", label="S-Curve")
st.sidebar.page_link("pages/2_WBS.py", label="WBS")
st.sidebar.markdown("<hr>", unsafe_allow_html=True)

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

with st.sidebar:
    if PREVIEW_ENABLED:
        use_test = st.toggle(
            "Use test Excel (artifacts/W_example.xlsx)",
            value=True,
            key="use_test_excel",
        )
    else:
        use_test = False
    debug_remount = False
    packs = []
    source_path = shared_path
    test_path = Path("artifacts/W_example.xlsx")
    if not source_path and use_test:
        if test_path.exists():
            source_path = str(test_path)
        else:
            st.info("Test file not found at artifacts/W_example.xlsx.")

    if source_path:
        try:
            schedule_lookup, schedule_info = build_schedule_lookup(
                source_path,
                column_mapping=st.session_state.get("column_mapping"),
            )
            st.session_state["_schedule_lookup"] = schedule_lookup
            st.session_state["_schedule_info"] = schedule_info
            packs = extract_all_wbs(
                source_path,
                schedule_lookup=schedule_lookup,
                schedule_info=schedule_info,
                column_mapping=st.session_state.get("column_mapping"),
            )
            st.session_state["_packs"] = packs
            st.session_state["_detected_tables"] = []
            if not packs:
                st.session_state["_detected_tables"] = detect_expected_tables(source_path)
            st.session_state["_table_mismatch"] = None
            st.session_state["_preview_rows"] = build_preview_rows(
                source_path,
                table_type="activity_summary",
                prefer_first_table=True,
                column_mapping=st.session_state.get("column_mapping"),
            )
        except Exception as e:
            st.error(f"Extraction error: {e}")

    if packs:
        preview_rows = st.session_state.get("_preview_rows", [])
        if preview_rows:
            build_activity_filter_sidebar(
                preview_rows,
                sidebar=st.sidebar,
                fallback_max_depth_key="wbs_max_depth",
            )

packs = st.session_state.get("_packs", [])
detected_tables = st.session_state.get("_detected_tables", [])
mismatch = st.session_state.get("_table_mismatch")
schedule_info = st.session_state.get("_schedule_info", {})
preview_rows = st.session_state.get("_preview_rows", [])
label_by_id, label_by_name, name_by_id = _build_display_label_maps(preview_rows)
if label_by_id or label_by_name or name_by_id:
    for pack in packs:
        _apply_display_labels(pack.get("wbs", {}), label_by_id, label_by_name, name_by_id)
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
if schedule_info and schedule_info.get("status") not in (None, "ok"):
    st.warning(
        "Schedule % may be unavailable. "
        + " ".join(schedule_info.get("errors", []))
    )
st.sidebar.toggle(
    "Show leaf badges",
    value=False,
    key="show_leaf_badges",
    help="Show a badge for nodes with no children.",
)
if PREVIEW_ENABLED:
    preview_mode = st.sidebar.toggle("Preview mode (dev)", value=True, key="preview_mode")
else:
    preview_mode = False
st.sidebar.checkbox(
    "Do not truncate names",
    value=False,
    key="wbs_no_truncate",
)
truncate_labels = not st.session_state.get("wbs_no_truncate", False)
if preview_mode:
    st.markdown("### Preview (mapping checks)")
    st.markdown("Source for hierarchy: Activity summary table (Activity ID indentation).")
    st.info("Resource assignments table is used only for Schedule % mapping for now.")
    st.markdown("Mapped now:")
    st.markdown("- planned (BL Project Finish)")
    st.markdown("- forecast (Finish)")
    st.markdown("- schedule (from resource assignments weekly table)")
    st.markdown("- earned (from Units % Complete)")
    st.markdown("- variance (earned - schedule)")
    st.markdown("- impact (Budgeted Units ratio * variance)")
    st.markdown("- slip (Variance - BL Project Finish Date)")
    st.markdown("Random placeholder fields (to be mapped later):")
    st.markdown("- planned_finish")
    st.markdown("- forecast_finish")
    st.markdown("- earned")
    st.markdown("- variance")
    st.markdown("- impact")
    st.markdown("- slip")
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

    # Mapping diagnostics (missing IDs / values)
    schedule_lookup = st.session_state.get("_schedule_lookup", {})
    activity_ids = [
        str(r.get("activity_id") or "").strip()
        for r in preview_rows
        if str(r.get("activity_id") or "").strip()
    ]
    schedule_missing = [
        r.get("display_label") or r.get("label") or r.get("activity_id")
        for r in preview_rows
        if str(r.get("activity_id") or "").strip()
        and (
            str(r.get("activity_id") or "").strip() not in schedule_lookup
            or schedule_lookup[str(r.get("activity_id") or "").strip()].get("value") is None
        )
    ]
    earned_missing = [
        r.get("display_label") or r.get("label") or r.get("activity_id")
        for r in preview_rows
        if r.get("units_complete") in (None, "", " ")
    ]
    root_budget = None
    if activity_ids:
        root_entry = schedule_lookup.get(activity_ids[0])
        root_budget = root_entry.get("budgeted_units") if root_entry else None
    budget_missing = [
        r.get("display_label") or r.get("label") or r.get("activity_id")
        for r in preview_rows
        if str(r.get("activity_id") or "").strip()
        and (
            str(r.get("activity_id") or "").strip() not in schedule_lookup
            or schedule_lookup[str(r.get("activity_id") or "").strip()].get("budgeted_units") in (None, 0)
        )
    ]
    if schedule_info and schedule_info.get("status") not in (None, "ok"):
        st.warning("Schedule issues: " + " ".join(schedule_info.get("errors", [])))
    if schedule_missing or earned_missing or budget_missing:
        st.warning("Mapping issues detected (showing samples):")
        if schedule_missing:
            st.markdown(f"- Missing Schedule % (week column or value): {', '.join(schedule_missing[:8])}")
        if earned_missing:
            st.markdown(f"- Missing Earned % (Units % Complete): {', '.join(earned_missing[:8])}")
        if root_budget in (None, 0):
            st.markdown("- Root Budgeted Units missing or 0 (Impact will be '?').")
        elif budget_missing:
            st.markdown(f"- Missing Budgeted Units: {', '.join(budget_missing[:8])}")

    import hashlib
    import random
    from datetime import date, timedelta

    def _rng(key: str) -> random.Random:
        seed = int.from_bytes(hashlib.md5(key.encode("utf-8")).digest()[:4], "little")
        return random.Random(seed)

    def _rand_date(r: random.Random) -> str:
        base = date(2025, 1, 1)
        return (base + timedelta(days=r.randint(0, 330))).strftime("%d-%b-%y")

    schedule_lookup = st.session_state.get("_schedule_lookup", {})
    root_budget = None
    if preview_rows:
        root_entry = schedule_lookup.get(str(preview_rows[0].get("activity_id") or "").strip())
        if root_entry:
            root_budget = root_entry.get("budgeted_units")

    def _preview_metrics(row: dict) -> dict:
        activity_id = str(row.get("activity_id") or "").strip()
        label = row.get("display_label") or row.get("label") or activity_id
        rng = _rng(label)
        schedule_entry = schedule_lookup.get(activity_id) if activity_id else None
        if schedule_entry:
            schedule = schedule_entry.get("value")
            schedule_display = schedule_entry.get("display", "?")
            schedule_tip = schedule_entry.get("tip")
            activity_budget = schedule_entry.get("budgeted_units")
        else:
            schedule = None
            schedule_display = "?"
            schedule_tip = "Schedule unavailable: Activity ID not found in resource assignments."
            activity_budget = None
        earned_raw = row.get("units_complete")
        if earned_raw is None or str(earned_raw).strip() == "":
            earned = None
            earned_display = "?"
            earned_tip = "Earned unavailable: Units % Complete missing."
        else:
            earned = parse_percent_float(earned_raw)
            earned_display = f"{earned:.2f}%"
            earned_tip = "Earned % = Units % Complete"

        if isinstance(earned, (int, float)) and isinstance(schedule, (int, float)):
            ecart = round(earned - schedule, 2)
            ecart_display = f"{ecart:+.2f}%"
            ecart_tip = "Variance = Earned % - Schedule %"
        else:
            ecart = None
            ecart_display = "?"
            if earned is None:
                ecart_tip = "Variance unavailable: Earned % missing."
            elif schedule is None:
                ecart_tip = "Variance unavailable: Schedule % missing."
            else:
                ecart_tip = "Variance unavailable: missing values."

        impact = None
        if isinstance(ecart, (int, float)):
            if root_budget in (None, 0):
                impact_display = "?"
                impact_tip = "Impact unavailable: root Budgeted Units missing or 0."
            elif activity_budget in (None, 0):
                impact_display = "?"
                impact_tip = "Impact unavailable: Budgeted Units missing or 0."
            else:
                impact = (activity_budget / root_budget) * ecart
                impact_display = f"{impact:+.2f}%"
                impact_tip = "Impact = (Budgeted Units / Root Budgeted Units) * Variance"
        else:
            impact_display = "?"
            if ecart is None:
                impact_tip = "Impact unavailable: Variance missing."
            else:
                impact_tip = "Impact unavailable: missing values."
        planned_raw = row.get("bl_project_finish")
        planned_text = as_text(planned_raw)
        if planned_text:
            planned_display = planned_text
            planned_tip = "Planned = BL Project Finish"
        else:
            planned_display = "?"
            planned_tip = "Planned unavailable: BL Project Finish missing."

        forecast_raw = row.get("finish")
        forecast_text = as_text(forecast_raw)
        if forecast_text:
            forecast_display = forecast_text
            forecast_tip = "Forecast = Finish"
        else:
            forecast_display = "?"
            forecast_tip = "Forecast unavailable: Finish missing."

        gliss_raw = row.get("variance_days")
        gliss_val = None
        if gliss_raw is not None and str(gliss_raw).strip() != "":
            try:
                gliss_val = float(gliss_raw)
            except Exception:
                gliss_val = None
        if gliss_val is None:
            gliss_display = "?"
            gliss_tip = "Slip unavailable: Variance - BL Project Finish Date missing."
        else:
            gliss_display = f"{int(gliss_val)}j"
            gliss_tip = "Slip = Variance - BL Project Finish Date (days)"
        return {
            "planned_finish": planned_text,
            "planned_display": planned_display,
            "planned_tip": planned_tip,
            "forecast_finish": forecast_text,
            "forecast_display": forecast_display,
            "forecast_tip": forecast_tip,
            "schedule": schedule,
            "schedule_display": schedule_display,
            "schedule_tip": schedule_tip,
            "earned": earned,
            "earned_display": earned_display,
            "earned_tip": earned_tip,
            "ecart": ecart,
            "ecart_display": ecart_display,
            "ecart_tip": ecart_tip,
            "impact": impact,
            "impact_display": impact_display,
            "impact_tip": impact_tip,
            "glissement": gliss_val,
            "glissement_display": gliss_display,
            "glissement_tip": gliss_tip,
        }

    def _build_preview_tree(rows: list[dict]) -> dict:
        min_level = min(r.get("level", 0) for r in rows)
        root = None
        stack = []
        for r in rows:
            lvl = (r.get("level", 0) - min_level) + 1
            node = {
                "label": r.get("display_label") or r["label"],
                "level": lvl,
                "activity_id": r.get("activity_id") or r["label"],
                "metrics": _preview_metrics(r),
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
    root_choice = st.session_state.get("activity_root_id", ROOT_ACTIVITY_ALL)
    if root_choice != ROOT_ACTIVITY_ALL:
        found = _find_node_by_activity_id(root, root_choice)
        if found:
            root_level = int(found.get("level", 1))
            root = _rebase_tree_levels(found, max(0, root_level - 1))
    st.caption("Preview uses placeholder metrics until we map real values.")
    st.session_state.setdefault("_preview_anim_seq", 0)
    start_depth_level = st.session_state.get("activity_start_depth", "0")
    if isinstance(start_depth_level, str) and start_depth_level.isdigit():
        start_depth_level = int(start_depth_level)
    else:
        start_depth_level = 0
    render_all(
        root,
        st.session_state["_preview_anim_seq"],
        wbs_key="preview",
        debug=False,
        truncate_labels=truncate_labels,
        start_depth=start_depth_level,
    )
    st.info("Disable preview in the sidebar to render the WBS.")
    st.stop()

if not packs:
    if detected_tables:
        st.info("Tables detected, but the format is incomplete for WBS generation.")
        for t in detected_tables:
            missing = ", ".join(t.get("missing", [])) or "none"
            st.markdown(f"- {t['type']} | sheet {t['sheet']} | {t['range']} | missing: {missing}")
    else:
        st.info("Upload the Excel file in the sidebar or from the Project Progress page to view the WBS.")
    st.stop()

# Permet de forcer le remount des blocs animes lorsque l'on change de WBS
st.session_state.setdefault("_anim_seq", 0)
st.session_state.setdefault("_active_ctx", "")
st.session_state.setdefault("_idx_prev", -1)

depth_choice = st.session_state.get(
    "activity_depth_filter",
    st.session_state.get("wbs_max_depth", "All levels"),
)
max_depth = int(depth_choice) if isinstance(depth_choice, str) and depth_choice.isdigit() else None
start_depth_level = st.session_state.get("activity_start_depth", "0")
if isinstance(start_depth_level, str) and start_depth_level.isdigit():
    start_depth_level = int(start_depth_level)
else:
    start_depth_level = 0
if max_depth is not None and max_depth <= start_depth_level:
    max_depth = start_depth_level + 1

idx = 0
wbs_idx = idx
sel = packs[wbs_idx]
root = sel["wbs"]
root_choice = st.session_state.get("activity_root_id", ROOT_ACTIVITY_ALL)
if root_choice != ROOT_ACTIVITY_ALL:
    found = _find_node_by_activity_id(root, root_choice)
    if found:
        root_level = int(found.get("level", 1))
        root = _rebase_tree_levels(found, max(0, root_level - 1))
wbs_key = _slug(sel.get("sheet","sheet")) + "__" + _slug(sel.get("range","range")) + "__" + _slug(root.get("label","wbs")) + f"__{wbs_idx}"
if st.session_state["_active_ctx"] != wbs_key or st.session_state["_idx_prev"] != wbs_idx:
    st.session_state["_anim_seq"] += 1
    st.session_state["_active_ctx"] = wbs_key
st.session_state["_idx_prev"] = wbs_idx

if debug_remount:
    st.sidebar.caption(f"[dbg] anim_seq={st.session_state['_anim_seq']} active_ctx={st.session_state['_active_ctx']} idx_prev={st.session_state['_idx_prev']}")
with st.container(key="glass_wrap"):
    with st.container(key=f"anim_wrap__{st.session_state['_anim_seq']%2}"):
        render_all(
            root,
            st.session_state["_anim_seq"],
            wbs_key,
            debug=debug_remount,
            max_depth=max_depth,
            truncate_labels=truncate_labels,
            start_depth=start_depth_level,
        )
