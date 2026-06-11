"""PNG export via Playwright-managed Chromium (ADR-003).

Rasterizes the canonical SVG by loading it in headless Chromium and screenshotting the
``<svg>`` element. Chromium is the ONLY raster path (never CairoSVG — no bidi support).
Determinism comes from the embedded font subset + fixed device scale; the same SVG
yields the same PNG on the same Chromium build (A3).
"""
from __future__ import annotations

from pathlib import Path

__all__ = ["svg_to_png"]


def svg_to_png(svg: str, out_path: str | Path, scale: int = 2) -> Path:
    """Render ``svg`` to a PNG at ``out_path``. Returns the written path.

    Imports Playwright lazily so importing the package never requires a browser.
    """
    from playwright.sync_api import sync_playwright

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    html = f"<!doctype html><meta charset='utf-8'><body style='margin:0'>{svg}</body>"

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(device_scale_factor=scale)
            page.set_content(html, wait_until="load")
            page.evaluate("document.fonts.ready")
            page.wait_for_timeout(200)
            element = page.query_selector("svg")
            if element is None:
                raise RuntimeError("no <svg> element found to rasterize")
            element.screenshot(path=str(out))
        finally:
            browser.close()
    return out
