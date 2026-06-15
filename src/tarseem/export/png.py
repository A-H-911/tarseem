"""PNG export via Playwright-managed Chromium (ADR-003).

Rasterizes the canonical SVG by loading it in headless Chromium and screenshotting the
``<svg>`` element. Chromium is the ONLY raster path (never CairoSVG — no bidi support).
Determinism comes from the embedded font subset + fixed device scale; the same SVG
yields the same PNG on the same Chromium build (A3).

Two entry points, mirroring the SVG canonical/provenance split:
* ``svg_to_png`` — the byte-stable raster primitive (no provenance). Used by visual baselines,
  the determinism suite, and the gallery, which all want the bare picture.
* ``write_png`` — the export *writer*: rasters, embeds provenance as a ``tEXt`` chunk, and
  returns a ``WriteResult`` with a CapabilityReport (invariant 6). A PNG is a faithful raster
  of the canonical SVG, so every visual axis is ``full`` and glyphs are baked to pixels
  (self-contained); see ``report.faithful_svg_render_report``.
"""
from __future__ import annotations

import struct
import zlib
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tarseem.export.result import WriteResult

__all__ = ["svg_to_png", "write_png"]


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


def _png_with_text(raw: bytes, keyword: bytes, text: bytes) -> bytes:
    """Insert a single ``tEXt`` provenance chunk before ``IEND`` without re-encoding the image.

    ``tEXt`` is an ancillary chunk, so the pixel stream (IDAT) is byte-for-byte untouched — the
    raster, and thus every committed visual baseline, is unaffected (the baselines compare pixels;
    see ``visualtest.compare_png``). Deterministic: the chunk is a pure function of its content."""
    data = keyword + b"\x00" + text
    crc = zlib.crc32(b"tEXt" + data) & 0xFFFFFFFF
    chunk = struct.pack(">I", len(data)) + b"tEXt" + data + struct.pack(">I", crc)
    iend = raw.rindex(b"IEND") - 4  # back up over IEND's 4-byte length field
    return raw[:iend] + chunk + raw[iend:]


def write_png(
    svg: str, out_path: str | Path, *, scale: int = 2, meta: dict[str, str] | None = None
) -> WriteResult:
    """Raster ``svg`` to ``out_path`` and return the path + a CapabilityReport (invariant 6).

    A PNG faithfully reproduces the canonical SVG within a raster, so every visual axis is ``full``;
    glyphs are baked to pixels (``fonts_embedded=full`` — renders with zero fonts installed). When
    ``meta`` is given, provenance travels in a ``tEXt`` chunk (``metadata=full``)."""
    from tarseem.export.metadata import as_text
    from tarseem.export.result import WriteResult
    from tarseem.report import faithful_svg_render_report

    out = svg_to_png(svg, out_path, scale)
    if meta:
        body = as_text(meta).encode("latin-1", "replace")  # tEXt is Latin-1; provenance is ASCII
        out.write_bytes(_png_with_text(out.read_bytes(), b"tarseem", body))
    report = faithful_svg_render_report(
        "png", svg=svg, fonts_embedded="full", metadata="full" if meta else "none"
    )
    return WriteResult(path=out, report=report)
