from pathlib import Path

import streamlit as st

from auth_google import require_login, render_auth_sidebar
from ui import inject_theme


_icon_path = Path(__file__).resolve().parents[1] / "Wibis_logo.png"
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
render_auth_sidebar(user, show_logo=False, show_branding=False)
inject_theme()

st.sidebar.markdown('<div class="sidebar-nav-title">Navigation</div>', unsafe_allow_html=True)
st.sidebar.page_link("app.py", label="Project Progress")
st.sidebar.page_link("pages/3_S_Curve.py", label="S-Curve")
st.sidebar.page_link("pages/2_WBS.py", label="WBS")
st.sidebar.markdown("<hr>", unsafe_allow_html=True)


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


st.markdown("## Excel format guide")
st.markdown(
    "Your Excel must contain two tables: **Activity Summary** and "
    "**Resource Assignments**. They can be on the same sheet or different sheets."
)
st.markdown(
    "**Important**: Activity IDs must match across both tables (same values and indentation)."
)

st.markdown("### Activity Summary (required)")
st.markdown(
    "- Required columns: Activity ID, Activity Name, Activity Status, BL Project Finish, "
    "Finish, Units % Complete, Variance - BL Project Finish Date"
)
st.markdown("- Optional columns: Budgeted Labor Units")
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
| Activity ID | Activity Name    | Activity Status | BL Project Finish | Finish      | Units % Complete | Variance - BL Project Finish Date |
|------------|------------------|-----------------|------------------|-------------|------------------|-----------------------------------|
| A-100      |                  |                 | 2025-01-10       | 2025-01-12  | 100%             | 2                                 |
| &nbsp;&nbsp;A-110 |                  |                 | 2025-01-05       | 2025-01-07  | 100%             | 2                                 |
| &nbsp;&nbsp;&nbsp;&nbsp;A-111 | Mobilize crew    | Completed       | 2025-01-06       | 2025-01-07  | 100%             | 1                                 |
| &nbsp;&nbsp;&nbsp;&nbsp;A-112 | Temporary works  | In Progress     | 2025-01-08       | 2025-01-12  | 90%              | 4                                 |
| &nbsp;&nbsp;A-120 | Foundations     | Not Started     | 2025-02-05       | 2025-02-11  | 72%              | 6                                 |
""",
    unsafe_allow_html=False,
)

st.markdown("### Resource Assignments (required)")
st.markdown(
    "- Required columns: Activity ID, Budgeted Units, Spreadsheet Field"
)
st.markdown("- Optional columns: Start, Finish")
st.markdown(
    "- Activity IDs must match Activity Summary (same values and indentation)."
)
st.markdown(
    "- Weekly date columns: one column per week (week start), used for curves."
)
st.markdown(
    "- Spreadsheet Field values: Cum Budgeted Units, Cum Actual Units, Cum Remaining Early Units."
)
st.markdown("Example:")
st.markdown(
    """
| Activity ID | Start      | Finish     | Budgeted Units | Spreadsheet Field         | 2025-01-06 | 2025-01-13 |
|------------|------------|------------|----------------|---------------------------|------------|------------|
| A-100      |            |            | 310            | Cum Budgeted Units        | 10         | 25         |
| &nbsp;&nbsp;A-110 |            |            | 190            | Cum Budgeted Units        | 5          | 15         |
| &nbsp;&nbsp;&nbsp;&nbsp;A-111 | 2025-01-06 | 2025-01-07 | 120            | Cum Budgeted Units        | 10         | 25         |
| &nbsp;&nbsp;&nbsp;&nbsp;A-111 | 2025-01-06 | 2025-01-07 | 120            | Cum Actual Units          | 8          | 20         |
| &nbsp;&nbsp;&nbsp;&nbsp;A-111 | 2025-01-06 | 2025-01-07 | 120            | Cum Remaining Early Units | 0          | 5          |
| &nbsp;&nbsp;A-120 | 2025-01-08 | 2025-01-12 | 90             | Cum Budgeted Units        | 4          | 10         |
| A-200      | 2025-02-05 | 2025-02-11 | 72             | Cum Budgeted Units        | 3          | 9          |
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
  using Resource Assignments with Spreadsheet Field = "Cum Budgeted Units".
- Actual Progress (gauge): Activity Summary `Units % Complete`.
- Planned Finish: Activity Summary `BL Project Finish`.
- Forecast Finish: Activity Summary `Finish`.
- Delay/Ahead: Activity Summary `Variance - BL Project Finish Date` (days).
- SV %: `Units % Complete - Schedule %`.
- SPI: `Units % Complete / Schedule %` (displayed as a percent).
- Weekly Progress chart: 7-week window centered on current week (3 before, current, 3 after).
  Planned % per week = `(Cum Budgeted Units week value - previous week value) / Budgeted Units * 100`.
  Actual % per week uses `Cum Actual Units` for past weeks and
  `Cum Remaining Early Units` for current/future weeks.
- Weekly SV % chart: `Planned % - Actual %` (or `Planned % - Forecast %` when actual is missing).
- Activities Status donut: for the selected activity, find leaf activities (no children) under it,
  sum Activity Summary `Budgeted Labor Units` by `Activity Status`, then divide by the parent
  activity's `Budgeted Labor Units` to get percentages.

**S-Curve page**
- Planned curve: cumulative planned % = `Cum Budgeted Units / Budgeted Units * 100`.
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
    "- Keep a single header row at the top of each table.\n"
    "- Avoid merged header cells.\n"
    "- Dates can be Excel dates or ISO format (YYYY-MM-DD)."
)

st.markdown("### Template")
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
