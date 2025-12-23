import sys
import runpy
from pathlib import Path

# Ensure the WBS app can run in-place without clobbering root modules.
ROOT = Path(__file__).resolve().parent.parent
WBS_DIR = ROOT / "wbs_app"

# Keep originals to restore after execution (avoids leaking wbs_app/data.py as "data").
_orig_sys_path = list(sys.path)

# Put root first, then wbs_app, then the rest (deduped).
sys.path = [str(ROOT), str(WBS_DIR)] + [p for p in sys.path if p not in (str(ROOT), str(WBS_DIR))]

try:
    # Execute the standalone WBS app script; it sets page config and renders its UI.
    runpy.run_path(WBS_DIR / "wbs_app.py", run_name="__main__")
finally:
    # Restore path and drop any accidental module shadowing.
    sys.path = _orig_sys_path
    mod = sys.modules.get("data")
    if mod and getattr(mod, "__file__", "").endswith("wbs_app\\data.py"):
        sys.modules.pop("data", None)
