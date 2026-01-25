# data.py - full version
import json
from pathlib import Path
from typing import Dict, Any, List

DEFAULT_WBS: Dict[str, Any] = {
    "wbs": {
        "label": "Transformer Station",
        "level": 1,
        "metrics": {"planned_finish": "", "forecast_finish": "", "schedule": 55.78, "earned": 57.74, "ecart": 1.96, "impact": 0, "glissement": "11"},
        "children": [
            {"label": "Structural Works", "level": 2, "metrics": {"planned_finish": "", "forecast_finish": "", "schedule": 87.5, "earned": 90.57, "ecart": 3.07, "impact": 0, "glissement": "0"}},
            {"label": "CEA", "level": 2, "metrics": {"planned_finish": "", "forecast_finish": "", "schedule": 0.0, "earned": 0.0, "ecart": 0.0, "impact": 0, "glissement": "0"}},
            {"label": "CET", "level": 2, "metrics": {"planned_finish": "", "forecast_finish": "", "schedule": 0.0, "earned": 0.0, "ecart": 0.0, "impact": 0, "glissement": "0"}},
        ],
    }
}

def load_all_wbs(path: str = "wbs.json") -> List[Dict[str, Any]]:
    """
    Load the full list from wbs.json (array of {sheet, range, wbs} objects).
    If the file does not exist or is invalid, return [DEFAULT_WBS].
    """
    p = Path(path)
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, list) and all(isinstance(x, dict) and "wbs" in x for x in data):
                return data
        except Exception:
            pass
    return [DEFAULT_WBS]
