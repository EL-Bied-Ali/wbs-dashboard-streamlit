#!/usr/bin/env python
"""
Verify the activity filter selectboxes with Playwright.

Outputs:
- artifacts/activity_filter_check.json
- artifacts/activity_filter.png
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright


def _select_option(page, label: str, option: str) -> list[str]:
    combobox = page.get_by_role("combobox", name=re.compile(label, re.I)).first
    combobox.click()
    try:
        page.wait_for_selector('[role="listbox"]', timeout=1500)
    except Exception:
        try:
            combobox.locator('xpath=ancestor-or-self::*[@data-baseweb="select"]').first.click()
            combobox.press("ArrowDown")
            page.wait_for_selector('[role="listbox"]', timeout=1500)
        except Exception:
            try:
                combobox.click()
                combobox.type(option, delay=30)
                combobox.press("Enter")
            except Exception:
                return []
            return []
    option_nodes = page.locator('[role="option"]')
    option_texts = option_nodes.all_inner_texts()
    for idx, text in enumerate(option_texts):
        if option.lower() in text.lower():
            option_nodes.nth(idx).click()
            return option_texts
    return option_texts


def _selected_label(page, label: str) -> str | None:
    combobox = page.get_by_role("combobox", name=re.compile(label, re.I)).first
    return combobox.get_attribute("aria-label")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8501")
    parser.add_argument("--depth", default=None, help="Max depth option to select.")
    parser.add_argument(
        "--activity", default=None, help="Activity name to select in the list."
    )
    parser.add_argument("--page", default="", help="Optional page label to click.")
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
            page.get_by_text(args.page, exact=True).click(timeout=2000)
            page.wait_for_load_state("networkidle")

        before = {
            "max_depth": _selected_label(page, "Max depth"),
            "activity": _selected_label(page, "Select activity"),
        }

        depth_options = []
        activity_options = []
        if args.depth:
            depth_options = _select_option(page, "Max depth", str(args.depth))
            page.wait_for_load_state("networkidle")

        if args.activity:
            activity_options = _select_option(page, "Select activity", args.activity)
            page.wait_for_load_state("networkidle")

        after = {
            "max_depth": _selected_label(page, "Max depth"),
            "activity": _selected_label(page, "Select activity"),
        }

        result = {
            "before": before,
            "after": after,
            "depth_options": depth_options,
            "activity_options": activity_options,
        }
        (out_dir / "activity_filter_check.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )
        page.screenshot(path=str(out_dir / "activity_filter.png"), full_page=True)
        browser.close()


if __name__ == "__main__":
    main()
