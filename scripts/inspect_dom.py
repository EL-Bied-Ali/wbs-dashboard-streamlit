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


def dom_summary_js() -> str:
    return r"""
() => {
  const toText = (el) => (el ? (el.innerText || "").trim().replace(/\s+/g, " ").slice(0, 160) : "");
  const withBox = (el) => {
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return { x: r.x, y: r.y, w: r.width, h: r.height };
  };
  const findKeyClass = (el) => {
    if (!el) return null;
    const cls = (el.className || "").toString().split(/\s+/).find((c) => c.includes("st-key-"));
    return cls || null;
  };
  const closestKey = (el) => {
    let cur = el;
    while (cur) {
      const cls = findKeyClass(cur);
      if (cls) return cls;
      cur = cur.parentElement;
    }
    return null;
  };

  const openDetails = Array.from(document.querySelectorAll("details[open]")).map((d) => {
    return {
      summary: toText(d.querySelector("summary")),
      keyClass: closestKey(d),
      box: withBox(d)
    };
  });

  const plotly = Array.from(document.querySelectorAll(".stPlotlyChart")).map((c) => {
    const container = c.closest('[data-testid="stElementContainer"]');
    return {
      keyClass: closestKey(c),
      containerHeight: container ? container.getAttribute("height") : null,
      containerClass: container ? container.className : null,
      box: withBox(c)
    };
  });

  const toggles = Array.from(document.querySelectorAll('div[class*="__rowbtn"], div[class*="__hero_toggle"]')).map((t) => {
    return {
      keyClass: closestKey(t),
      className: t.className || null,
      box: withBox(t)
    };
  });

  const n2Labels = Array.from(document.querySelectorAll(".n2g-label .title")).map((t) => ({
    text: toText(t),
    keyClass: closestKey(t),
    box: withBox(t)
  }));

  const expanderCount = document.querySelectorAll('[data-testid="stExpander"]').length;

  return {
    openDetailsCount: openDetails.length,
    openDetails,
    plotlyCount: plotly.length,
    plotly,
    toggleCount: toggles.length,
    toggles,
    n2LabelsCount: n2Labels.length,
    n2Labels,
    expanderCount
  };
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
    parser.add_argument("--summary", action="store_true", help="Write a DOM summary JSON.")
    parser.add_argument("--upload", help="Optional file to upload into the first file input.")
    parser.add_argument("--click", action="append", default=[], help="Text to click (can be repeated).")
    parser.add_argument("--click-selector", action="append", default=[], help="CSS selector to click (can be repeated).")
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

        if args.upload:
            try:
                page.locator('[data-testid="stFileUploaderDropzoneInput"]').first.set_input_files(args.upload)
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(1200)
            except Exception:
                pass

        for text in args.click:
            try:
                page.get_by_text(text, exact=True).click(timeout=2000)
                page.wait_for_load_state("networkidle")
            except Exception:
                try:
                    page.get_by_text(text).first.click(timeout=2000)
                    page.wait_for_load_state("networkidle")
                except Exception:
                    pass

        for selector in args.click_selector:
            try:
                page.locator(selector).first.click(timeout=2000)
                page.wait_for_load_state("networkidle")
            except Exception:
                pass

        page.wait_for_timeout(int(args.wait * 1000))

        dom = page.content()
        (out_dir / "dom.html").write_text(dom, encoding="utf-8")

        scrollables = page.evaluate(find_scrollables_js())
        (out_dir / "scrollables.json").write_text(
            json.dumps(scrollables, indent=2), encoding="utf-8"
        )

        if args.summary:
            summary = page.evaluate(dom_summary_js())
            (out_dir / "dom_summary.json").write_text(
                json.dumps(summary, indent=2), encoding="utf-8"
            )

        if not args.no_screenshot:
            page.screenshot(path=str(out_dir / "screen.png"), full_page=True)

        browser.close()


if __name__ == "__main__":
    main()
