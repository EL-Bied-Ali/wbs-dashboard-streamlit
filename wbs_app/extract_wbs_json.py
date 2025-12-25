# extract_wbs_json_v7.py
# Usage: python extract_wbs_json_v7.py Book1.xlsx --out wbs_all.json
from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any, Tuple
import argparse, json, re
import pandas as pd
from openpyxl import load_workbook
from datetime import datetime, date
from typing import Any

REQUIRED_COLS = [
    "Planned Finish", "Forecast Finish", "Schedule %", "Earned %",
    "ecart", "impact", "Glissement"
]

SUMMARY_HEADER_GROUPS = {
    "activity id": ["Activity ID", "ActivityID"],
    "bl project finish": [
        "BL Project Finish", "Baseline Project Finish",
        "BL Project Finish Date", "Baseline Project Finish Date"
    ],
    "finish": ["Finish", "Project Finish", "Finish Date"],
    "units % complete": ["Units % Complete", "Units Percent Complete", "% Complete", "Percent Complete"],
    "variance - bl project finish date": [
        "Variance - BL Project Finish Date", "Variance BL Project Finish Date",
        "Variance - BL Project Finish", "Variance BL Project Finish"
    ],
}

ASSIGN_HEADER_GROUPS = {
    "activity id": ["Activity ID", "ActivityID"],
    "activity name": ["Activity Name", "ActivityName"],
    "start": ["Start", "Start Date"],
    "finish": ["Finish", "Finish Date"],
    "rcv / phases": ["RCV / Phases", "RCV/Phases", "RCV Phases"],
    "budgeted units": ["Budgeted Units", "Budget Units"],
    "actual units": ["Actual Units", "Actuals Units"],
    "spreadsheet field": ["Spreadsheet Field", "SpreadsheetField"],
}

# ---------- Helpers (format identique à ton exemple) ----------
def as_text(v: Any) -> str:
    """Dates -> 'dd-Mon-yy', sinon str, None -> '' """
    if isinstance(v, (datetime, date)):
        return v.strftime("%d-%b-%y")
    return "" if v is None else str(v)



def parse_percent_float(v):
    """
    Lecture propre des pourcentages :
    - '75.51%' -> 75.51
    - 0.7551   -> 75.51
    - '0.7551' -> 75.51
    - '1.2%'   -> 1.2
    - 75.51    -> 75.51
    """
    import re
    if v is None or v == "":
        return 0.0
    if isinstance(v, str):
        s = re.sub(r"[^\d\-\.,%]", "", v).replace(",", ".").replace("%", "").strip()
        if s in ("", "-", "."):
            return 0.0
        try:
            val = float(s)
        except Exception:
            return 0.0
    else:
        try:
            val = float(v)
        except Exception:
            return 0.0

    # ✅ multiplie uniquement si la valeur est comprise entre -1 et 1
    if -1.0 <= val <= 1.0:
        val *= 100.0

    return val




def parse_percent_int(v: Any) -> int:
    """
    Pour ecart/impact: retourne un ENTIER en 0–100 (ex: '-4%' -> -4, 0.05 -> 5).
    """
    f = parse_percent_float(v)
    return int(round(f))  # force entier comme ton exemple

def tidy_num(x: float | int) -> float | int:
    """
    Pour schedule/earned: si 75.0 -> 75 (int), sinon 36.81 reste 36.81.
    """
    if isinstance(x, (int,)):
        return x
    if abs(x - round(x)) < 1e-9:
        return int(round(x))
    return x

def trim_empty_border(df: pd.DataFrame) -> pd.DataFrame:
    while df.shape[1] > 0 and df.iloc[:, 0].isna().all(): df = df.iloc[:, 1:]
    while df.shape[1] > 0 and df.iloc[:, -1].isna().all(): df = df.iloc[:, :-1]
    while df.shape[0] > 0 and df.iloc[0].isna().all(): df = df.iloc[1:, :]
    while df.shape[0] > 0 and df.iloc[-1].isna().all(): df = df.iloc[:-1, :]
    return df

def make_unique_columns(cols: List[str]) -> List[str]:
    seen: Dict[str,int] = {}; out: List[str] = []
    for c in cols:
        c = "" if c is None else str(c).strip()
        if c not in seen:
            seen[c] = 1; out.append(c)
        else:
            seen[c] += 1; out.append(f"{c}_{seen[c]}")
    return out

def leading_spaces(s: Any) -> int:
    if s is None: return 0
    s = str(s).replace("\t","    ")
    m = re.match(r"^\s*", s)
    return len(m.group(0)) if m else 0

def clean_label(s: Any) -> str:
    if s is None: return ""
    return str(s).strip()

def _norm(x: Any) -> str:
    return re.sub(r"\s+", " ", str(x or "")).strip().lower()

def _norm_header(x: Any) -> str:
    s = str(x or "").strip().lower()
    if not s:
        return ""
    s = s.replace("%", " percent ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def has_all_required(headers: List[Any]) -> bool:
    H = [_norm(h) for h in headers]
    R = [_norm(rc) for rc in REQUIRED_COLS]
    return all(rc in H for rc in R)

def _is_date_like(x: str) -> bool:
    x = x.strip()
    if not x: return False
    if re.match(r"\d{4}-\d{2}-\d{2}", x): return True
    if re.match(r"\d{1,2}-[A-Za-z]{3}-\d{2}", x): return True
    try:
        datetime.strptime(x, "%d-%b-%y"); return True
    except Exception:
        return False

def _is_week_header(v: Any) -> bool:
    if isinstance(v, (datetime, date)):
        return True
    s = str(v or "").strip()
    if not s:
        return False
    if re.match(r"\d{4}-\d{2}-\d{2}", s):
        return True
    if re.match(r"\d{1,2}-[A-Za-z]{3}-\d{2}", s):
        return True
    if re.match(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", s):
        return True
    return False

def _match_header_groups(headers: List[Any], groups: dict) -> Tuple[List[str], List[str]]:
    header_set = { _norm_header(h) for h in headers if _norm_header(h) }
    matched = []
    missing = []
    for key, opts in groups.items():
        norm_opts = [_norm_header(o) for o in opts]
        if any(opt in header_set for opt in norm_opts):
            matched.append(key)
        else:
            missing.append(key)
    return matched, missing

# ---------- Détection de tous les blocs (avec extension gauche pour colonne label) ----------
def detect_all_blocks_with_left_extension(ws, max_added_left: int = 5) -> List[Tuple[int,int,int,int]]:
    max_r, max_c = ws.max_row, ws.max_column
    blocks: List[Tuple[int,int,int,int]] = []
    r = 1
    while r <= max_r:
        headers = [ws.cell(r,c).value for c in range(1,max_c+1)]
        if not any(headers):
            r += 1; continue
        if not has_all_required(headers):
            r += 1; continue

        nz = [i+1 for i,v in enumerate(headers) if v not in (None,""," ")]
        c1, c2 = min(nz), max(nz)

        # descendre pour fin du bloc
        r2 = r + 1
        while r2 <= max_r:
            row_vals = [ws.cell(r2, c).value for c in range(c1, c2+1)]
            if all(v in (None, "", " ") for v in row_vals):
                break
            r2 += 1

        # extension gauche si colonne sans titre avec données
        added = 0
        while c1 > 1 and added < max_added_left:
            col_vals = [ws.cell(rr, c1-1).value for rr in range(r+1, r2)]
            if any(v not in (None,""," ") for v in col_vals):
                c1 -= 1
                added += 1
            else:
                break

        blocks.append((r, c1, r2-1, c2))
        # saute au-delà de ce bloc
        r = r2 + 1
    return blocks

# ---------- Detection: summary + assignments tables ----------
def detect_expected_tables(input_xlsx: str) -> List[Dict[str, Any]]:
    wb = load_workbook(input_xlsx, data_only=True)
    results: List[Dict[str, Any]] = []
    for ws in wb.worksheets:
        max_r, max_c = ws.max_row, ws.max_column
        r = 1
        while r <= max_r:
            headers = [ws.cell(r, c).value for c in range(1, max_c + 1)]
            if not any(headers):
                r += 1
                continue

            matched_summary, missing_summary = _match_header_groups(headers, SUMMARY_HEADER_GROUPS)
            matched_assign, missing_assign = _match_header_groups(headers, ASSIGN_HEADER_GROUPS)
            date_cols = sum(1 for h in headers if _is_week_header(h))

            summary_ok = (
                "activity id" in matched_summary and
                ("finish" in matched_summary or "bl project finish" in matched_summary) and
                len(matched_summary) >= 3
            )
            assign_ok = (
                {"activity id", "activity name", "start", "finish"}.issubset(set(matched_assign)) and
                len(matched_assign) >= 5 and
                date_cols >= 5
            )

            if not summary_ok and not assign_ok:
                r += 1
                continue

            nz = [i + 1 for i, v in enumerate(headers) if v not in (None, "", " ")]
            if not nz:
                r += 1
                continue
            c1, c2 = min(nz), max(nz)

            r2 = r + 1
            while r2 <= max_r:
                row_vals = [ws.cell(r2, c).value for c in range(c1, c2 + 1)]
                if all(v in (None, "", " ") for v in row_vals):
                    break
                r2 += 1

            results.append({
                "sheet": ws.title,
                "range": f"R{r}C{c1}:R{r2-1}C{c2}",
                "header_row": r,
                "type": "activity_summary" if summary_ok else "resource_assignments",
                "missing": missing_summary if summary_ok else missing_assign,
                "date_columns": date_cols,
            })
            r = r2 + 1
    return results

def _parse_range(range_str: str) -> Tuple[int, int, int, int]:
    m = re.match(r"R(\d+)C(\d+):R(\d+)C(\d+)", range_str)
    if not m:
        raise ValueError(f"Invalid range: {range_str}")
    return tuple(int(x) for x in m.groups())

def compare_activity_ids(input_xlsx: str) -> Dict[str, Any]:
    wb = load_workbook(input_xlsx, data_only=True)
    tables = detect_expected_tables(input_xlsx)
    summary_ids: List[str] = []
    assign_ids: List[str] = []

    for t in tables:
        ws = wb[t["sheet"]]
        r1, c1, r2, c2 = _parse_range(t["range"])
        header = [ws.cell(r1, c).value for c in range(c1, c2 + 1)]
        id_idx = None
        for idx, v in enumerate(header):
            if str(v).strip() == "Activity ID":
                id_idx = idx
                break
        if id_idx is None:
            continue
        for r in range(r1 + 1, r2 + 1):
            val = ws.cell(r, c1 + id_idx).value
            if val is None or str(val).strip() == "":
                continue
            if t["type"] == "activity_summary":
                summary_ids.append(str(val))
            elif t["type"] == "resource_assignments":
                assign_ids.append(str(val))

    summary_set = {s.strip() for s in summary_ids}
    assign_set = {s.strip() for s in assign_ids}
    return {
        "summary_unique": len(summary_set),
        "assign_unique": len(assign_set),
        "summary_only": sorted(summary_set - assign_set),
        "assign_only": sorted(assign_set - summary_set),
    }

def build_preview_rows(input_xlsx: str) -> List[Dict[str, Any]]:
    wb = load_workbook(input_xlsx, data_only=True)
    tables = detect_expected_tables(input_xlsx)
    rows: List[Dict[str, Any]] = []

    def _lead_spaces(s: str) -> int:
        return len(re.match(r"^\s*", s).group(0))

    for t in tables:
        if t["type"] != "resource_assignments":
            continue
        ws = wb[t["sheet"]]
        r1, c1, r2, c2 = _parse_range(t["range"])
        header = [ws.cell(r1, c).value for c in range(c1, c2 + 1)]
        id_idx = None
        for idx, v in enumerate(header):
            if str(v).strip() == "Activity ID":
                id_idx = idx
                break
        if id_idx is None:
            continue

        for r in range(r1 + 1, r2 + 1):
            val = ws.cell(r, c1 + id_idx).value
            if val is None or str(val).strip() == "":
                continue
            raw = str(val)
            rows.append({
                "sheet": t["sheet"],
                "range": t["range"],
                "raw": raw,
                "label": raw.strip(),
                "indent": _lead_spaces(raw),
            })

    if not rows:
        return []

    indents = sorted({r["indent"] for r in rows})
    indent_to_level = {sp: i for i, sp in enumerate(indents)}
    for r in rows:
        r["level"] = indent_to_level.get(r["indent"], 0)
    return rows

# ---------- Choix de la colonne Label ----------
def pick_label_col(df: pd.DataFrame) -> str:
    """
    Priorité :
      1) Colonne d'en-tête vide "" si surtout du texte non date-like
      2) Sinon meilleure colonne non-requise : textuelle, non date-like, variété d'indentation
      3) Sinon première colonne
    """
    req = {"Planned Finish","Forecast Finish","Schedule %","Earned %","ecart","impact","Glissement"}
    if "" in df.columns:
        col = df[""].astype(str)
        if (col.str.strip() != "").any():
            not_dates_ratio = (~col.str.strip().apply(_is_date_like)).mean()
            if not_dates_ratio > 0.6:
                return ""

    best, best_score = None, -1.0
    for c in df.columns:
        if c in req: 
            continue
        col = df[c].astype(str)
        texty = col.apply(lambda s: any(ch.isalpha() for ch in s)).mean()
        not_date = col.apply(lambda s: not _is_date_like(s)).mean()
        indents = col.apply(leading_spaces)
        indent_levels = indents.nunique()
        score = (texty*2.0) + (not_date*1.5) + (min(indent_levels, 4)*0.8)
        if score > best_score:
            best_score, best = score, c
    return best or df.columns[0]

# ---------- WBS builder ----------
def to_wbs_tree(df: pd.DataFrame, label_col: str) -> Dict:
    df = df.copy()
    df[label_col] = df[label_col].fillna("")
    df = df[df[label_col].astype(str).str.strip() != ""]
    df["_indent"] = df[label_col].apply(leading_spaces)

    uniq = sorted(df["_indent"].unique().tolist()) or [0]
    space2lvl = {sp: i+1 for i, sp in enumerate(uniq)}

    def row_metrics(r: pd.Series) -> dict:
        # NOTE: ecart/impact -> ENTIER, schedule/earned -> tidy (int si rond)
        schedule = tidy_num(parse_percent_float(r.get("Schedule %")))
        earned   = tidy_num(parse_percent_float(r.get("Earned %")))
        return {
            "planned_finish": as_text(r.get("Planned Finish")),
            "forecast_finish": as_text(r.get("Forecast Finish")),
            "schedule": schedule,
            "earned":   earned,
            "ecart":    parse_percent_float(r.get("ecart")),
            "impact":   parse_percent_float(r.get("impact")),
            "glissement": as_text(r.get("Glissement")),
        }

    root: Dict | None = None
    stack: List[Dict] = []

    for _, r in df.iterrows():
        label = clean_label(r[label_col])
        if not label:
            continue
        lvl = space2lvl.get(r["_indent"], len(space2lvl))  # fallback = plus profond
        node = {"label": label, "level": int(lvl), "metrics": row_metrics(r), "children": []}

        if not stack:
            root = node
            stack = [node]
            continue

        while stack and stack[-1]["level"] >= lvl:
            stack.pop()

        if not stack:
            # nouveau L1 → frère du root
            if root is None:
                root = node
                stack = [node]
            else:
                root.setdefault("children", []).append(node)
                stack = [root, node]
        else:
            stack[-1]["children"].append(node)
            stack.append(node)

    return root or {}

# ---------- Extraction (tous les tableaux) ----------
def extract_all_wbs(input_xlsx: str) -> List[Dict]:
    wb = load_workbook(input_xlsx, data_only=True)
    results: List[Dict] = []

    for ws in wb.worksheets:
        blocks = detect_all_blocks_with_left_extension(ws)
        for (r1, c1, r2, c2) in blocks:
            data = [[ws.cell(rr, cc).value for cc in range(c1, c2+1)] for rr in range(r1, r2+1)]
            if len(data) < 2:
                continue
            df = pd.DataFrame(data)
            df.columns = make_unique_columns([str(x).strip() if x is not None else "" for x in df.iloc[0].tolist()])
            df = df.iloc[1:, :].reset_index(drop=True)
            df = trim_empty_border(df)

            # Filtre: doit contenir toutes les colonnes requises
            if not all(col in df.columns for col in REQUIRED_COLS):
                continue

            label_col = pick_label_col(df)
            tree = to_wbs_tree(df, label_col)
            if tree:
                results.append({
                    "sheet": ws.title,
                    "range": f"R{r1}C{c1}:R{r2}C{c2}",
                    "wbs": tree
                })
    return results

# ---------- CLI ----------
if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Build an array of WBS JSONs from all valid tables in Excel.")
    p.add_argument("input_xlsx", help="Path to Excel file, e.g., Book1.xlsx")
    p.add_argument("--out", default="wbs_all.json", help="Output JSON path")
    args = p.parse_args()

    all_wbs = extract_all_wbs(args.input_xlsx)
    Path(args.out).write_text(json.dumps(all_wbs, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"Saved: {args.out}  |  Tables matched: {len(all_wbs)}")
