from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path

from openpyxl import load_workbook

BASE_TEMPLATE_PATH = Path("artifacts") / "Chronoplan_Template.xlsx"
DEMO_TEMPLATE_DIR = Path(".streamlit") / "generated_demo"
GENERATED_TEMPLATE_PATH = DEMO_TEMPLATE_DIR / "Chronoplan_Template.xlsx"
META_PATH = DEMO_TEMPLATE_DIR / "Chronoplan_Template.meta.json"
PLANNED_WEEK_SHIFT_DAYS = 7
DEMO_TEMPLATE_VERSION = 3


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _to_date(value) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def _extract_week_header_cells(sheet) -> list[tuple[int, date]]:
    row = next(sheet.iter_rows(min_row=1, max_row=1), None)
    if not row:
        return []
    headers: list[tuple[int, date]] = []
    for cell in row:
        header_date = _to_date(cell.value)
        if header_date is not None:
            headers.append((cell.col_idx, header_date))
    return headers


def _extract_week_headers(sheet) -> list[date]:
    row = next(sheet.iter_rows(min_row=1, max_row=1, values_only=True), None)
    if not row:
        return []
    headers: list[date] = []
    for value in row:
        header_date = _to_date(value)
        if header_date is not None:
            headers.append(header_date)
    return headers


def _find_week_headers(workbook) -> list[date]:
    preferred = (
        "Ressource Assign. Budgeted",
        "Ressource Assign. Actual",
        "Ressource Assign. Remaining",
    )
    for name in preferred:
        if name in workbook.sheetnames:
            headers = _extract_week_headers(workbook[name])
            if headers:
                return headers

    for sheet in workbook.worksheets:
        headers = _extract_week_headers(sheet)
        if headers:
            return headers

    return []


def _calculate_delta(workbook, target_week: date) -> timedelta | None:
    week_headers = _find_week_headers(workbook)
    if not week_headers:
        return None

    pivot_idx = len(week_headers) // 2
    pivot_header = week_headers[pivot_idx]
    pivot_target_week = _week_start(
        pivot_header - timedelta(days=PLANNED_WEEK_SHIFT_DAYS)
    )
    return target_week - pivot_target_week


def _apply_delta(workbook, delta: timedelta) -> None:
    for sheet in workbook.worksheets:
        for row in sheet.iter_rows():
            for cell in row:
                value = cell.value
                if isinstance(value, datetime):
                    cell.value = value + delta
                elif isinstance(value, date):
                    cell.value = value + delta


def _align_remaining_headers(workbook, desired_start: date) -> None:
    remaining_name = "Ressource Assign. Remaining"
    if remaining_name not in workbook.sheetnames:
        return

    remaining_sheet = workbook[remaining_name]
    remaining_cells = _extract_week_header_cells(remaining_sheet)
    if not remaining_cells:
        return

    remaining_dates = [d for _, d in remaining_cells]

    if len(remaining_dates) > 1:
        step = remaining_dates[1] - remaining_dates[0]
        if step.days <= 0:
            step = timedelta(days=7)
    else:
        step = timedelta(days=7)

    for idx, (col_idx, _) in enumerate(remaining_cells):
        remaining_sheet.cell(row=1, column=col_idx).value = desired_start + (step * idx)


def _ensure_readme_note(workbook) -> None:
    if "README" not in workbook.sheetnames:
        return
    note = "Remaining weekly columns should start at the current week."
    old_note = (
        "Remaining weekly columns should start at the last or penultimate "
        "planned week."
    )
    sheet = workbook["README"]
    for row_idx, row in enumerate(sheet.iter_rows(values_only=True), start=1):
        if any(cell == note for cell in row):
            return
        if any(cell == old_note for cell in row):
            for col_idx, cell in enumerate(row, start=1):
                if cell == old_note:
                    sheet.cell(row=row_idx, column=col_idx).value = note
                    return
    last_row = 0
    for row_idx in range(sheet.max_row, 0, -1):
        row_values = [cell.value for cell in sheet[row_idx]]
        if any(value not in (None, "") for value in row_values):
            last_row = row_idx
            break
    target_row = last_row + 1 if last_row else 1
    if last_row:
        sheet.cell(row=target_row, column=1, value="")
        target_row += 1
    sheet.cell(row=target_row, column=1, value=note)


def _load_meta() -> dict | None:
    if not META_PATH.exists():
        return None
    try:
        return json.loads(META_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None


def _save_meta(data: dict) -> None:
    DEMO_TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    META_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _generate_live_template(target_week: date) -> Path:
    workbook = load_workbook(BASE_TEMPLATE_PATH)
    delta = _calculate_delta(workbook, target_week)
    if delta is None:
        raise ValueError("unable to locate weekly headers in the template")

    _apply_delta(workbook, delta)
    _align_remaining_headers(workbook, target_week)
    _ensure_readme_note(workbook)
    DEMO_TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    workbook.save(GENERATED_TEMPLATE_PATH)
    return GENERATED_TEMPLATE_PATH


def ensure_demo_template() -> Path | None:
    if not BASE_TEMPLATE_PATH.exists():
        return None

    target_week = _week_start(date.today())
    base_mtime = BASE_TEMPLATE_PATH.stat().st_mtime
    meta = _load_meta()
    if (
        meta
        and meta.get("version") == DEMO_TEMPLATE_VERSION
        and meta.get("target_week") == target_week.isoformat()
        and isinstance(meta.get("base_mtime"), (int, float))
        and meta["base_mtime"] == base_mtime
        and GENERATED_TEMPLATE_PATH.exists()
    ):
        return GENERATED_TEMPLATE_PATH

    try:
        path = _generate_live_template(target_week)
        _save_meta(
            {
                "version": DEMO_TEMPLATE_VERSION,
                "target_week": target_week.isoformat(),
                "base_mtime": base_mtime,
            }
        )
        return path
    except Exception:
        return None


def get_demo_template_path() -> Path | None:
    path = ensure_demo_template()
    if path and path.exists():
        return path
    if BASE_TEMPLATE_PATH.exists():
        return BASE_TEMPLATE_PATH
    return None


def demo_template_bytes() -> tuple[bytes, str] | tuple[None, None]:
    path = get_demo_template_path()
    if path and path.exists():
        return path.read_bytes(), path.name
    return None, None
