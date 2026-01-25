from __future__ import annotations

import json
import os
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

APP_URL = os.environ.get("APP_URL", "http://localhost:8501")
COOKIE_NAME = os.environ.get("AUTH_COOKIE_NAME", "nabil_auth")
USER_DATA_DIR = Path(__file__).resolve().parent / ".pw_auth_profile"
WAIT_TIMEOUT = int(os.environ.get("PW_WAIT_TIMEOUT", "180"))
POLL_INTERVAL = float(os.environ.get("PW_POLL_INTERVAL", "2"))


def _summarize_cookie(cookie: dict) -> str:
    expires = cookie.get("expires")
    return json.dumps(
        {
            "name": cookie.get("name"),
            "value_len": len(cookie.get("value", "")),
            "domain": cookie.get("domain"),
            "path": cookie.get("path"),
            "expires": expires,
            "httpOnly": cookie.get("httpOnly"),
            "secure": cookie.get("secure"),
            "sameSite": cookie.get("sameSite"),
        },
        indent=2,
    )


def _find_cookie(cookies: list[dict], name: str) -> dict | None:
    for cookie in cookies:
        if cookie.get("name") == name:
            return cookie
    return None


def _wait_for_cookie(context, name: str, timeout_sec: int) -> dict | None:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        target = _find_cookie(context.cookies(), name)
        if target:
            return target
        time.sleep(POLL_INTERVAL)
    return None


def main() -> None:
    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        try:
            context = p.chromium.launch_persistent_context(
                str(USER_DATA_DIR),
                channel="msedge",
                headless=False,
            )
        except Exception:
            context = p.chromium.launch_persistent_context(
                str(USER_DATA_DIR),
                headless=False,
            )
        page = context.new_page()
        page.goto(APP_URL, wait_until="domcontentloaded")
        print(f"Log in via the opened browser. Waiting up to {WAIT_TIMEOUT}s for cookie...")
        target = _wait_for_cookie(context, COOKIE_NAME, WAIT_TIMEOUT)
        if target:
            print("Cookie after login:")
            print(_summarize_cookie(target))
        else:
            print("Cookie not found after login.")
            print("Cookies present:", [c.get("name") for c in context.cookies()])

        print("Reloading page to test persistence...")
        page.reload(wait_until="domcontentloaded")
        time.sleep(1.0)
        cookies_after = context.cookies()
        target_after = _find_cookie(cookies_after, COOKIE_NAME)
        if target_after:
            print("Cookie after reload:")
            print(_summarize_cookie(target_after))
        else:
            print("Cookie not found after reload.")
            print("Cookies present:", [c.get("name") for c in cookies_after])

        print("Done. Close the browser window when finished.")
        context.close()


if __name__ == "__main__":
    main()
