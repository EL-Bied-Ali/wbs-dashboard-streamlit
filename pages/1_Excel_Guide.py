from pathlib import Path

import streamlit as st

from auth_google import require_login, render_auth_sidebar, render_contact_sidebar
from demo_template import demo_template_bytes, get_demo_template_debug
from ui import inject_theme


_icon_path = Path(__file__).resolve().parents[1] / "Chronoplan_ico.png"
st.set_page_config(
    page_title="ChronoPlan",
    page_icon=str(_icon_path) if _icon_path.exists() else "🧭",
    layout="wide",
)
st.markdown(
    "<style>[data-testid='stSidebarNav']{display:none !important;}</style>",
    unsafe_allow_html=True,
)

user = require_login()
render_auth_sidebar(user, show_logo=False, show_branding=False)
inject_theme()

st.sidebar.markdown('<div class="sidebar-nav-title">Navigation</div>', unsafe_allow_html=True)
st.sidebar.page_link("pages/10_Dashboard.py", label="Project Progress")
st.sidebar.page_link("pages/3_S_Curve.py", label="S-Curve")
st.sidebar.page_link("pages/2_WBS.py", label="WBS")
st.sidebar.markdown("<hr>", unsafe_allow_html=True)
render_contact_sidebar()


def _excel_template_bytes():
    demo_bytes = demo_template_bytes()
    if demo_bytes[0] is not None:
        return demo_bytes

    candidates = [
        Path("artifacts") / "W_example.xlsx",
        Path("artifacts") / "wbs_sample.xlsx",
        Path("Progress.xlsx"),
    ]
    for path in candidates:
        if path.exists():
            return path.read_bytes(), path.name
    return None, None


st.markdown("## Excel format guide")
st.markdown(
    "<div style='font-size:18px;font-weight:800;'>Download the template first — it shows the exact sheet names, columns, and weekly headers we expect.</div>",
    unsafe_allow_html=True,
)
data, name = _excel_template_bytes()
if data and name:
    week = str(get_demo_template_debug().get("target_week") or "unknown-week")
    download_name = f"Chronoplan_Template_{week}.xlsx"
    st.download_button(
        "Download recommended template",
        data=data,
        file_name=download_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    st.caption(
        "Regenerates weekly to keep weekly headers aligned to the current week (Budgeted/Actual together, Remaining one week later)."
    )
else:
    st.caption("Template file not found in artifacts/ or project root.")

st.markdown(
    "Use four sheets with the same names as the template: "
    "**Activity Summary**, **Ressource Assign. Budgeted**, **Ressource Assign. Actual**, "
    "**Ressource Assign. Remaining**."
)
st.markdown(
    "**Important**: Activity IDs must match across all sheets (same values and indentation/spacing as the template)."
)

st.markdown("### Activity Summary (required)")
st.markdown(
    "- Required columns: Activity ID, Activity Name, Activity Status, BL Project Finish, "
    "Finish, Units % Complete, Variance - BL Project Finish Date, Budgeted Labor Units"
)
st.markdown(
    "- **Hierarchy**: use leading spaces in Activity ID to define levels (2 spaces per level)."
)
st.markdown(
    "- **Leaf rule**: Activity Name is filled only for leaf activities "
    "(no children). When Activity Name is filled, Activity Status must also be filled."
)
st.markdown("Example (Activity ID indentation shown with leading spaces):")
st.markdown(
    """
| Activity ID | Activity Name    | Activity Status | BL Project Finish | Finish      | Units % Complete | Variance - BL Project Finish Date | Budgeted Labor Units |
|------------|------------------|-----------------|------------------|-------------|------------------|-----------------------------------|----------------------|
| A-100      |                  |                 | 2025-01-10       | 2025-01-12  | 100%             | 2                                 | 1000                 |
| &nbsp;&nbsp;A-110 |                  |                 | 2025-01-05       | 2025-01-07  | 100%             | 2                                 | 600                  |
| &nbsp;&nbsp;&nbsp;&nbsp;A-111 | Mobilize crew    | Completed       | 2025-01-06       | 2025-01-07  | 100%             | 1                                 | 300                  |
| &nbsp;&nbsp;&nbsp;&nbsp;A-112 | Temporary works  | In Progress     | 2025-01-08       | 2025-01-12  | 90%              | 4                                 | 300                  |
| &nbsp;&nbsp;A-120 | Foundations     | Not Started     | 2025-02-05       | 2025-02-11  | 72%              | 6                                 | 400                  |
""",
    unsafe_allow_html=False,
)

st.markdown("### Resource sheets (Budgeted, Actual, Remaining)")
st.markdown("- Columns: Activity ID, Budgeted Units, Spreadsheet Field (Start/Finish optional).")
st.markdown("- Activity IDs must match Activity Summary (same values and indentation).")
st.markdown("- Spreadsheet Field values: Cum Budgeted Units, Cum Actual Units, Cum Remaining Early Units.")
st.markdown("- Weekly date columns: one column per week (week start, Monday) used for curves.")
st.markdown("- Weekly alignment: Budgeted and Actual share the same weeks; Remaining starts exactly one week after the last Actual week (template enforces this).")
st.markdown(
    "- Planned data (Cum Budgeted Units) is treated as one week earlier in the app "
    "(last planned week ignored and an extra week added at the start)."
)
st.markdown("Example snippet (from the separate resource sheets):")
st.markdown(
    """
**Ressource Assign. Budgeted**

| Activity ID | Start      | Finish     | Budgeted Units | Spreadsheet Field     | 2025-01-06 | 2025-01-13 |
|-------------|------------|------------|----------------|-----------------------|------------|------------|
| A-100       |            |            | 310            | Cum Budgeted Units    | 10         | 25         |
| &nbsp;&nbsp;A-110 |            |            | 190            | Cum Budgeted Units    | 5          | 15         |
| &nbsp;&nbsp;&nbsp;&nbsp;A-111 | 2025-01-06 | 2025-01-07 | 120            | Cum Budgeted Units    | 10         | 25         |
| &nbsp;&nbsp;A-120 | 2025-01-08 | 2025-01-12 | 90             | Cum Budgeted Units    | 4          | 10         |
| A-200       | 2025-02-05 | 2025-02-11 | 72             | Cum Budgeted Units    | 3          | 9          |

**Ressource Assign. Actual**

| Activity ID | Start      | Finish     | Budgeted Units | Spreadsheet Field  | 2025-01-06 | 2025-01-13 |
|-------------|------------|------------|----------------|--------------------|------------|------------|
| &nbsp;&nbsp;&nbsp;&nbsp;A-111 | 2025-01-06 | 2025-01-07 | 120            | Cum Actual Units | 8          | 20         |

**Ressource Assign. Remaining**

| Activity ID | Start      | Finish     | Budgeted Units | Spreadsheet Field           | 2025-01-13 | 2025-01-20 |
|-------------|------------|------------|----------------|-----------------------------|------------|------------|
| &nbsp;&nbsp;&nbsp;&nbsp;A-111 | 2025-01-06 | 2025-01-07 | 120            | Cum Remaining Early Units | 0          | 5          |
""",
    unsafe_allow_html=False,
)

st.markdown("### Calculations (from Excel)")
st.markdown(
    """
Formulas apply when an Excel file is loaded and an Activity ID is selected.
If data is missing, the UI shows "?" and may fall back to demo values.

**Project Progress dashboard**
- Planned Progress (gauge): `Schedule % = (current week units / Budgeted Units) * 100`
  using Resource Assignments with Spreadsheet Field = "Cum Budgeted Units" (shifted one week earlier).
- Actual Progress (gauge): Activity Summary `Units % Complete`.
- Planned Finish: Activity Summary `BL Project Finish`.
- Forecast Finish: Activity Summary `Finish`.
- Delay/Ahead: Activity Summary `Variance - BL Project Finish Date` (days).
- SV %: `Units % Complete - Schedule %`.
- SPI: `Units % Complete / Schedule %` (displayed as a percent).
- Weekly Progress chart: 7-week window centered on current week (3 before, current, 3 after).
  Planned % per week = `(Cum Budgeted Units week value - previous week value) / Budgeted Units * 100`,
  using the planned values shifted one week earlier.
  Actual % per week uses `Cum Actual Units` for past weeks and
  `Cum Remaining Early Units` for current/future weeks.
- Weekly SV % chart: `Planned % - Actual %` (or `Planned % - Forecast %` when actual is missing).
- Activities Status donut: for the selected activity, find leaf activities (no children) under it,
  sum Activity Summary `Budgeted Labor Units` by `Activity Status`, then divide by the parent
  activity's `Budgeted Labor Units` to get percentages.

**S-Curve page**
- Planned curve: cumulative planned % = `Cum Budgeted Units / Budgeted Units * 100`,
  using the planned values shifted one week earlier.
- Actual curve: cumulative actual % = `Cum Actual Units / Budgeted Units * 100` (past weeks only).
- Forecast curve: cumulative forecast % = `Cum Remaining Early Units / Budgeted Units * 100`,
  stitched from the last actual point when forecast starts on the same or next week.
- Weekly bars: weekly actual % = difference between consecutive points in the actual curve.

**WBS page**
- Hierarchy uses Activity ID indentation from Activity Summary (2 spaces per level).
- Planned Finish: Activity Summary `BL Project Finish`.
- Forecast Finish: Activity Summary `Finish`.
- Earned %: Activity Summary `Units % Complete` (fallback to `Earned %` if present).
- Schedule %: same as dashboard Schedule % (current week / Budgeted Units from Resource Assignments).
- Variance: `Earned % - Schedule %`.
- Impact: `(Activity Budgeted Units / Root Budgeted Units) * Variance`.
- Slip: Activity Summary `Variance - BL Project Finish Date` (days).
""",
    unsafe_allow_html=False,
)

st.markdown("### Notes")
st.markdown(
    "- All curves are computed as percent of **Budgeted Units**.\n"
    "- Weekly date columns are treated as week start (Monday).\n"
    "- Keep a single header row at the top of each table.\n"
    "- Avoid merged header cells.\n"
    "- Dates can be Excel dates or ISO format (YYYY-MM-DD)."
)

# Template download is already placed at the top of the page.
