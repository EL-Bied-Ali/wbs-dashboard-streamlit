# data.py
import json
from datetime import date, timedelta
from pathlib import Path
import pandas as pd

# data.py
MAPPINGS = {
    "sheet": None,                 # default -> first sheet
    "date":  None,                 # optional for charts (we'll do later)
    "weekly_actual":  None,
    "weekly_forecast": None,
    "cum_planned":   None,
    "cum_actual":    None,
    "cum_forecast":  None,

    # NEW: baseline start/finish column names from your file
    "bl_start":  "BL Project Start",
    "bl_finish": "BL Project Finish",
}

DEFAULT_WBS = {
    "label": "Substation Program",
    "level": 1,
    "metrics": {
        "planned_finish": "20 Nov 25",
        "forecast_finish": "28 Nov 25",
        "schedule": 72.5,
        "earned": 69.2,
        "ecart": -3.3,
        "impact": -2.1,
        "glissement": "-8",
    },
    "children": [
        {
            "label": "Civil Works",
            "level": 2,
            "metrics": {
                "planned_finish": "05 Oct 25",
                "forecast_finish": "12 Oct 25",
                "schedule": 78.0,
                "earned": 75.0,
                "ecart": -3.0,
                "impact": -2.5,
                "glissement": "-7",
            },
        },
        {
            "label": "Electrical Assembly",
            "level": 2,
            "metrics": {
                "planned_finish": "02 Nov 25",
                "forecast_finish": "05 Nov 25",
                "schedule": 68.5,
                "earned": 65.5,
                "ecart": -3.0,
                "impact": -1.0,
                "glissement": "-3",
            },
        },
        {
            "label": "Testing & Commissioning",
            "level": 2,
            "metrics": {
                "planned_finish": "18 Nov 25",
                "forecast_finish": "22 Nov 25",
                "schedule": 61.0,
                "earned": 57.0,
                "ecart": -4.0,
                "impact": -2.0,
                "glissement": "-4",
            },
        },
    ],
}

def load_wbs_data(path: Path | str | None = None):
    """
    Load WBS data from an optional JSON file.
    If the file does not exist or is invalid, return a default sample.
    """
    if path:
        path = Path(path)
        if path.exists():
            try:
                with path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return data
            except Exception:
                pass
    return DEFAULT_WBS

def sample_dashboard_data():
    """Returns static demo data to render the dashboard mock."""
    metrics = {
        "planned_progress": 44.62,
        "actual_progress": 29.62,
        "planned_start": date(2025, 3, 23),
        "planned_finish": date(2025, 11, 28),
        "forecast_finish": date(2026, 1, 11),
        "delay_days": -44,
        "sv_pct": -15.00,
        "spi": 0.66,
    }

    weekly_progress = [
        {"week": "W30", "planned": 3.12, "actual": 0.58},
        {"week": "W31", "planned": 4.94, "actual": 1.98},
        {"week": "W32", "planned": 3.33, "actual": 0.89},
        {"week": "W33", "planned": 5.80, "actual": 0.86},
        {"week": "W34", "planned": 3.95, "actual": 2.53},
        {"week": "W35", "planned": 6.42, "actual": 3.79},
        {"week": "W36", "planned": 4.97, "actual": 4.14},
    ]
    current_week = "W33"

    weekly_sv = [
        {"week": f"W{w}", "sv": v}
        for w, v in [
            (13, 0.00), (14, 0.80), (15, -0.23), (16, -0.06), (17, 0.10),
            (18, 1.79), (19, -1.23), (20, -1.46), (21, 0.38), (22, 0.86),
            (23, 0.96), (24, 1.79), (25, 2.96), (26, -2.96), (27, -4.94),
            (28, -2.96), (29, -4.94), (30, -2.96), (31, -4.94), (32, -2.96),
            (33, -4.94),
        ]
    ]

    activities_status = {
        "Completed": 26.73,
        "In Progress": 4.91,
        "Not Started": 68.36,
    }

    return {
        "metrics": metrics,
        "weekly_progress": weekly_progress,
        "current_week": current_week,
        "weekly_sv": weekly_sv,
        "activities_status": activities_status,
    }

def load_from_excel(uploaded_file, sheet: str | None = None):
    if uploaded_file is None:
        return None

    xl = pd.ExcelFile(uploaded_file)
    sheet_names = xl.sheet_names
    chosen = sheet or MAPPINGS["sheet"] or sheet_names[0]
    df = xl.parse(chosen)

    # Optional project dates: parse to datetime if present
    bls, blf = MAPPINGS["bl_start"], MAPPINGS["bl_finish"]
    if bls in df.columns:
        df[bls] = pd.to_datetime(df[bls], errors="coerce")
    if blf in df.columns:
        df[blf] = pd.to_datetime(df[blf], errors="coerce")

    # Optional "Date" for charts (later)
    has_date = False
    if MAPPINGS.get("date") and MAPPINGS["date"] in df.columns:
        df = df.rename(columns={MAPPINGS["date"]: "Date"})
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        has_date = True

    return {
        "df": df,
        "sheet_names": sheet_names,
        "chosen_sheet": chosen,
        "has_date": has_date,
        "weekly_actual": df.get(MAPPINGS["weekly_actual"]),
        "weekly_forecast": df.get(MAPPINGS["weekly_forecast"]),
        "cum_planned": df.get(MAPPINGS["cum_planned"]),
        "cum_actual": df.get(MAPPINGS["cum_actual"]),
        "cum_forecast": df.get(MAPPINGS["cum_forecast"]),
        "colmap": MAPPINGS,
    }



def demo_series():
    x = [date(2025,3,10)+timedelta(weeks=i) for i in range(44)]
    planned_curve  = [min(100, i*2.3) for i in range(len(x))]
    actual_curve   = [min(100, max(0, (i-6)*2.0)) for i in range(len(x))]
    forecast_curve = [min(100, max(actual_curve[i], planned_curve[i]-5)) for i in range(len(x))]
    weekly_planned = [max(0, planned_curve[i]-planned_curve[i-1]) if i>0 else planned_curve[0] for i in range(len(x))]
    weekly_actual  = [max(0, actual_curve[i]-actual_curve[i-1]) if i>0 else actual_curve[0] for i in range(len(x))]
    weekly_forecast = [None for _ in range(len(x))]
    return x, weekly_planned, weekly_actual, weekly_forecast, actual_curve, planned_curve, forecast_curve

def compute_kpis_from_series(cum_planned_last, cum_actual_last):
    planned = float(cum_planned_last or 0)
    actual = float(cum_actual_last or 0)
    sv_pct = actual - planned
    spi = (actual / planned) if planned > 0 else 0
    delay_days = int(round((100 - actual) * 0.44))
    return planned, actual, sv_pct, spi, delay_days
