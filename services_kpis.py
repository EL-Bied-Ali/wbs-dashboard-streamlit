from __future__ import annotations
import pandas as pd
from services_dates import business_days_diff

__all__ = ["extract_dates_labels", "compute_kpis"]

def extract_dates_labels(df: pd.DataFrame | None, colmap: dict | None):
    def fmt(d): return d.strftime("%d %b %y") if d is not None and pd.notna(d) else "—"
    if df is None or colmap is None:
        return ("—","—","—"), None, None

    planned_start_dt = planned_finish_dt = forecast_finish_dt = None

    bl_start = colmap.get("bl_start")
    bl_finish = colmap.get("bl_finish")

    if bl_start in df.columns:
        s = pd.to_datetime(df[bl_start], errors="coerce").dropna()
        planned_start_dt = s.min() if not s.empty else None
    if bl_finish in df.columns:
        s = pd.to_datetime(df[bl_finish], errors="coerce").dropna()
        planned_finish_dt = s.min() if not s.empty else None
    if "Finish" in df.columns:
        s = pd.to_datetime(df["Finish"], errors="coerce").dropna()
        forecast_finish_dt = s.min() if not s.empty else None

    labels = (fmt(planned_start_dt), fmt(planned_finish_dt), fmt(forecast_finish_dt))
    return labels, planned_finish_dt, forecast_finish_dt

def compute_kpis(df: pd.DataFrame | None, colmap: dict | None,
                 planned_finish_dt=None, forecast_finish_dt=None,
                 country_code="BE"):
    if df is None or colmap is None:
        return 0, 0, "_", "_", "_"

    actual_pct = planned_pct = 0.0
    if "Actual Labor Units" in df.columns and "Budgeted Labor Units" in df.columns:
        act = pd.to_numeric(df["Actual Labor Units"], errors="coerce").fillna(0).sum()
        bud = pd.to_numeric(df["Budgeted Labor Units"], errors="coerce").fillna(0).sum()
        actual_pct = (act / bud * 100) if bud > 0 else 0.0

    planned_pct = min(100.0, actual_pct * 0.9)
    sv_pct = (actual_pct - planned_pct) if planned_pct > 0 else "_"
    spi = (actual_pct / planned_pct) if planned_pct > 0 else "_"

    delay_days = business_days_diff(planned_finish_dt, forecast_finish_dt)
    return planned_pct, actual_pct, sv_pct, spi, delay_days

