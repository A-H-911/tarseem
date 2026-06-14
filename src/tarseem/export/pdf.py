"""PDF export via Playwright-managed Chromium (ADR-003, 08 §export-strategy).

Prints the canonical SVG to a single-page, vector PDF by loading it in headless Chromium and
driving ``Page.printToPDF`` (Playwright ``page.pdf``). Chromium is the ONLY render path (never
CairoSVG — no bidi support); it renders the Cairo glyph outlines into the file (self-contained —
no font install needed) and shapes Arabic/RTL, so the PDF is a faithful, portable render of the
source-of-truth SVG. Like ``png.py`` this is a thin renderer of the canonical SVG (not an IR
reconstruction), so it drops nothing relative to the SVG and needs no CapabilityReport.

Fidelity ceiling (visually verified against the canonical PNG): the print backend (Skia) carries
glyphs as Type3 vector procedures rather than an embedded TrueType subset — visually faithful and
self-contained, but the extractable *text layer* loses reliable Unicode for complex scripts, so
copy/search of Arabic from the PDF is garbled (the picture is correct). Some compositing (e.g.
semi-transparent lane fills) may flatten to a small raster — not visible at the rendered size.

Two things differ from ``png.py`` and are handled here — the parts of "mirror png.py" that do
NOT transfer, because a PDF is a *paginated document*, not a single bitmap:

* **Page sizing.** ``page.pdf`` paginates (unlike ``element.screenshot``, which auto-sizes to the
  element). The page is sized to the SVG's own box and the SVG is forced ``display:block``;
  otherwise an inline ``<svg>`` carries a line-box descender that spills a hairline second page.
  Dimensions are ``ceil``'d so a fractional SVG (e.g. 662.4px) never clips at the bottom edge.
* **Determinism (invariant 7 / A3).** Chromium stamps the PDF Info dict with wall-clock
  ``/CreationDate`` + ``/ModDate``. These are fixed-length plaintext strings, so the 14 timestamp
  digits are overwritten with a constant of equal length — byte offsets are preserved (the xref
  stays valid; no PDF dependency, no rewrite) — giving the same PDF for the same SVG on the same
  Chromium build.
"""
from __future__ import annotations

import math
import re
from pathlib import Path

__all__ = ["svg_to_pdf"]

# A PDF date is ``D:YYYYMMDDHHmmSS<tz>``. Chromium emits it for /CreationDate + /ModDate; the
# substitution is anchored on the field name (so it can never match a stray 14-digit run) and
# rewrites exactly the 14 timestamp digits with a constant of the SAME length, leaving the
# timezone suffix and every byte offset untouched.
_PDF_DATE_RE = re.compile(rb"(/(?:CreationDate|ModDate)\s*\(D:)\d{14}")
_FIXED_DATE = rb"\g<1>19700101000000"

# Our SVG root (render/svg.py) is ``<svg ... width="W" height="H" viewBox=...>`` with bare
# numeric W/H in source order — parse them to size the print page.
_SVG_DIMS_RE = re.compile(r'<svg\b[^>]*\bwidth="([\d.]+)"[^>]*\bheight="([\d.]+)"')


def _normalize_pdf_dates(raw: bytes) -> bytes:
    """Pin Chromium's wall-clock PDF dates to a constant so the same SVG ⇒ byte-identical PDF
    (invariant 7). Same-length substitution, so byte offsets — and thus the xref table — are
    untouched. A determinism test guards this: a future Chromium that changes the date format,
    adds an ``/ID``, or moves dates into a compressed object stream fails the test loudly rather
    than silently regressing."""
    return _PDF_DATE_RE.sub(_FIXED_DATE, raw)


def _page_size(svg: str) -> tuple[int, int]:
    """The print-page size in px: the SVG's own box, ``ceil``'d so a fractional extent never
    clips at the right/bottom edge."""
    m = _SVG_DIMS_RE.search(svg)
    if m is None:  # pragma: no cover - our SVG always carries width/height (render/svg.py)
        raise RuntimeError("could not read width/height from the SVG root to size the PDF page")
    return math.ceil(float(m.group(1))), math.ceil(float(m.group(2)))


def svg_to_pdf(svg: str, out_path: str | Path) -> Path:
    """Render ``svg`` to a single-page, deterministic, vector PDF at ``out_path``. Returns the
    written path.

    Imports Playwright lazily so importing the package never requires a browser (mirrors png.py).
    """
    from playwright.sync_api import sync_playwright

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    width, height = _page_size(svg)
    # display:block kills the inline-<svg> line-box descender that would otherwise spill a 2nd page.
    html = (
        "<!doctype html><meta charset='utf-8'>"
        "<style>html,body{margin:0;padding:0}svg{display:block}</style>"
        f"<body>{svg}</body>"
    )

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.set_content(html, wait_until="load")
            page.evaluate("document.fonts.ready")
            page.wait_for_timeout(200)
            raw = page.pdf(
                width=f"{width}px",
                height=f"{height}px",
                # margin=0 so the page is exactly the SVG box (no default print margins)
                margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
                print_background=True,
            )
        finally:
            browser.close()
    out.write_bytes(_normalize_pdf_dates(raw))
    return out
