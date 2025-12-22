# services_dates.py — version simplifiée (dimanche uniquement)
from __future__ import annotations
import numpy as np
from datetime import datetime

__all__ = ["business_days_diff", "to_np_day"]

def to_np_day(dts) -> np.datetime64 | None:
    if dts is None:
        return None
    if hasattr(dts, "date"):
        try:
            return np.datetime64(dts.date(), "D")
        except Exception:
            return None
    try:
        return np.datetime64(dts, "D")
    except Exception:
        return None

def business_days_diff(planned_dt, forecast_dt,
                       weekmask="Mon Tue Wed Thu Fri Sat"):
    """
    Calcule le nombre de jours ouvrés (lundi à samedi).
    Dimanche est exclu, aucun jour férié n’est pris en compte.
    """
    if planned_dt is None or forecast_dt is None:
        return "_"
    start = to_np_day(planned_dt); end = to_np_day(forecast_dt)
    if start is None or end is None:
        return "_"
    raw = np.busday_count(min(start, end), max(start, end),
                          weekmask=weekmask)  # pas de holidays=
    sign = 1 if forecast_dt < planned_dt else -1
    return int(sign * raw)
