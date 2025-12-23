#!/usr/bin/env python
"""
Inspect a Streamlit page with Playwright.

Outputs:
- artifacts/dom.html
- artifacts/scrollables.json
- artifacts/screen.png (optional)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def find_scrollables_js() -> str:
    return r"""
() => {
  const results = [];
  const nodes = Array.from(document.querySelectorAll('*'));
  for (const el of nodes) {
    const style = window.getComputedStyle(el);
    const overflowY = style.overflowY;
    const overflowX = style.overflowX;
    const scrollY = el.scrollHeight - el.clientHeight;
    const scrollX = el.scrollWidth - el.clientWidth;
    const hasScrollY = scrollY > 1 && (overflowY === 'auto' || overflowY === 'scroll');
    const hasScrollX = scrollX > 1 && (overflowX === 'auto' || overflowX === 'scroll');
    if (hasScrollY || hasScrollX) {
      results.push({
        tag: el.tagName,
        id: el.id || null,
        className: el.className || null,
        testid: el.getAttribute('data-testid'),
        overflowX,
        overflowY,
        scrollX,
        scrollY,
        clientWidth: el.clientWidth,
        clientHeight: el.clientHeight,
        scrollWidth: el.scrollWidth,
        scrollHeight: el.scrollHeight
      });
    }
  }
  return results;
}
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8501", help="Base URL to open.")
    parser.add_argument("--page", default="", help="Optional page label to click in the sidebar.")
    parser.add_argument("--wait", type=float, default=2.0, help="Seconds to wait after load/click.")
    parser.add_argument("--no-screenshot", action="store_true", help="Disable screenshot output.")
    parser.add_argument("--out", default="artifacts", help="Output directory.")
    parser.add_argument("--show", action="store_true", help="Run with a visible browser.")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.show)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(args.url, wait_until="networkidle")

        if args.page:
            # Try to navigate by clicking a sidebar link/button with the given label.
            clicked = False
            for selector in [
                ("link", args.page),
                ("button", args.page),
            ]:
                role, name = selector
                try:
                    page.get_by_role(role, name=name, exact=True).click(timeout=1500)
                    clicked = True
                    break
                except Exception:
                    pass
            if not clicked:
                try:
                    page.get_by_text(args.page, exact=True).click(timeout=1500)
                    clicked = True
                except Exception:
                    pass
            if clicked:
                page.wait_for_load_state("networkidle")

        page.wait_for_timeout(int(args.wait * 1000))

        dom = page.content()
        (out_dir / "dom.html").write_text(dom, encoding="utf-8")

        scrollables = page.evaluate(find_scrollables_js())
        (out_dir / "scrollables.json").write_text(
            json.dumps(scrollables, indent=2), encoding="utf-8"
        )

        if not args.no_screenshot:
            page.screenshot(path=str(out_dir / "screen.png"), full_page=True)

        browser.close()


if __name__ == "__main__":
    main()
