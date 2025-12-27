import streamlit as st
from pathlib import Path

from auth_google import require_login, render_auth_sidebar
from ui import inject_theme


st.set_page_config(page_title="Excel Format Guide", layout="wide")
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
    "This app expects two tables in your Excel file: "
    "**Activity Summary** and **Resource Assignments**. "
    "The tables can be on the same sheet or different sheets."
)

st.markdown("### Activity Summary (required)")
st.markdown(
    "- Required columns: Activity ID, BL Project Finish, Finish, Units % Complete, "
    "Variance - BL Project Finish Date"
)
st.markdown("- Optional columns: Activity Name, Activity Status, Budgeted Labor Units")
st.markdown(
    "- **Hierarchy**: use leading spaces in Activity ID to define levels (2 spaces per level)."
)
st.markdown("Example (Activity ID indentation shown with leading spaces):")
st.markdown(
    """
| Activity ID | Activity Name    | BL Project Finish | Finish      | Units % Complete | Variance - BL Project Finish Date |
|------------|------------------|------------------|-------------|------------------|-----------------------------------|
| A-100      | Mobilization     | 2025-01-10       | 2025-01-12  | 100%             | 2                                 |
| &nbsp;&nbsp;A-110 | Site setup       | 2025-01-05       | 2025-01-07  | 100%             | 2                                 |
| &nbsp;&nbsp;&nbsp;&nbsp;A-111 | Mobilize crew    | 2025-01-06       | 2025-01-07  | 100%             | 1                                 |
| &nbsp;&nbsp;A-120 | Temporary works  | 2025-01-08       | 2025-01-12  | 90%              | 4                                 |
| A-200      | Foundation       | 2025-02-05       | 2025-02-11  | 72%              | 6                                 |
""",
    unsafe_allow_html=False,
)

st.markdown("### Resource Assignments (required)")
st.markdown(
    "- Required columns: Activity ID, Budgeted Units, Spreadsheet Field"
)
st.markdown(
    "- Optional columns: Activity Name (leaf rows only), Start, Finish"
)
st.markdown(
    "- Activity ID values should match the Activity Summary table (same IDs/indentation)"
)
st.markdown(
    "- Weekly date columns: one column per week (week start), used for curves"
)
st.markdown("Example:")
st.markdown(
    """
| Activity ID | Activity Name | Start      | Finish     | Budgeted Units | Spreadsheet Field         | 2025-01-06 | 2025-01-13 |
|------------|---------------|------------|------------|----------------|---------------------------|------------|------------|
| &nbsp;&nbsp;&nbsp;&nbsp;A-111 | Mobilize crew  | 2025-01-06 | 2025-01-07 | 120            | Cum Budgeted Units        | 10         | 25         |
| &nbsp;&nbsp;&nbsp;&nbsp;A-111 |               | 2025-01-06 | 2025-01-07 | 120            | Cum Actual Units          | 8          | 20         |
| &nbsp;&nbsp;&nbsp;&nbsp;A-111 |               | 2025-01-06 | 2025-01-07 | 120            | Cum Remaining Early Units | 0          | 5          |
| &nbsp;&nbsp;A-120 | Temporary works | 2025-01-08 | 2025-01-12 | 90             | Cum Budgeted Units        | 4          | 10         |
| A-200      | Foundation    | 2025-02-05 | 2025-02-11 | 72             | Cum Budgeted Units        | 3          | 9          |
""",
    unsafe_allow_html=False,
)

st.markdown("### Spreadsheet Field values")
st.markdown(
    "- Cum Budgeted Units: planned cumulative curve\n"
    "- Cum Actual Units: actual cumulative curve\n"
    "- Cum Remaining Early Units: forecast cumulative curve"
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
