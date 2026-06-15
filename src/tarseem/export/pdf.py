"""PDF export via Playwright-managed Chromium (ADR-003, 08 §export-strategy).

Prints the canonical SVG to a single-page, vector PDF by loading it in headless Chromium and
driving ``Page.printToPDF`` (Playwright ``page.pdf``). Chromium is the ONLY render path (never
CairoSVG — no bidi support); it renders the Cairo glyph outlines into the file (self-contained —
no font install needed) and shapes Arabic/RTL, so the PDF is a faithful, portable render of the
source-of-truth SVG. Like ``png.py`` it has two entry points: ``svg_to_pdf`` is the byte-stable
print primitive (no provenance — used by the determinism suite); ``write_pdf`` is the export
*writer* that embeds provenance and returns a ``WriteResult`` with a CapabilityReport. Because a
faithful render reproduces the SVG, every *visual* axis is ``full`` — see
``report.faithful_svg_render_report``; the only non-full axes are the medium ones (text layer,
metadata) handled below.

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
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tarseem.export.result import WriteResult

__all__ = ["svg_to_pdf", "write_pdf"]

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


def _render_pdf(svg: str) -> bytes:
    """Chromium-print ``svg`` to deterministic, single-page, vector PDF bytes (dates pinned).

    Imports Playwright lazily so importing the package never requires a browser (mirrors png.py).
    Shared by ``svg_to_pdf`` (bare primitive) and ``write_pdf`` (which then appends provenance)."""
    from playwright.sync_api import sync_playwright

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
    return _normalize_pdf_dates(raw)


def svg_to_pdf(svg: str, out_path: str | Path) -> Path:
    """Render ``svg`` to a single-page, deterministic, vector PDF at ``out_path``. Returns the
    written path. The byte-stable primitive (no provenance) — ``write_pdf`` adds metadata."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(_render_pdf(svg))
    return out


# --- provenance via an append-only incremental update (08 §6, invariant 6) -------------------
# Chromium emits a PDF 1.4-style classic xref TABLE + ``trailer`` (confirmed: no xref streams, no
# object streams). So provenance is embedded by appending an incremental update — a fresh Info
# dictionary object + a new xref subsection + trailer — WITHOUT rewriting a single existing byte.
# That keeps the date-pinning, page count, and Type3 glyphs exactly as ``_render_pdf`` produced
# them. Safe failure mode: if Chromium ever switches to xref streams the trailer regex misses and
# ``_append_provenance`` returns None, so write_pdf keeps the base PDF and honestly reports
# ``metadata=none`` (never a corrupt file, never a dishonest report).
_TRAILER_RE = re.compile(
    rb"trailer\s*<<(?P<dict>.*?)>>\s*startxref\s+(?P<startxref>\d+)\s+%%EOF\s*\Z", re.DOTALL
)


def _pdf_literal(value: str) -> bytes:
    """A PDF literal string body: escape the three bytes that would break ``( ... )``."""
    escaped = value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return escaped.encode("latin-1", "replace")


def _append_provenance(raw: bytes, meta: dict[str, str]) -> bytes | None:
    """Append an incremental-update Info dictionary carrying ``meta``. Returns the new bytes, or
    ``None`` if ``raw`` is not the expected classic-trailer shape (caller then embeds nothing)."""
    m = _TRAILER_RE.search(raw)
    if m is None:  # pragma: no cover - Chromium emits a classic trailer; guard for future drift
        return None
    tdict = m.group("dict")
    size_m = re.search(rb"/Size\s+(\d+)", tdict)
    root_m = re.search(rb"/Root\s+(\d+)\s+(\d+)\s+R", tdict)
    if not (size_m and root_m):  # pragma: no cover - a /Size and /Root are mandatory in a trailer
        return None
    prev = int(m.group("startxref"))
    new_num = int(size_m.group(1))  # next free object number
    root_obj, root_gen = int(root_m.group(1)), int(root_m.group(2))

    body = b"".join(b"/%b (%b)" % (_pdf_name(k), _pdf_literal(v)) for k, v in meta.items())
    prefix = b"" if raw.endswith(b"\n") else b"\n"
    obj_offset = len(raw) + len(prefix)
    obj = b"%d 0 obj\n<<%b>>\nendobj\n" % (new_num, body)
    xref_offset = obj_offset + len(obj)
    # Classic xref entry: exactly 20 bytes — ``%010d 00000 n \n`` (offset, gen, in-use, EOL).
    xref = (
        b"xref\n%d 1\n%010d 00000 n \n" % (new_num, obj_offset)
        + b"trailer\n<</Size %d /Root %d %d R /Info %d 0 R /Prev %d>>\nstartxref\n%d\n%%%%EOF\n"
        % (new_num + 1, root_obj, root_gen, new_num, prev, xref_offset)
    )
    return raw + prefix + obj + xref


def _pdf_name(key: str) -> bytes:
    """A provenance dict key as a PDF name (e.g. ``specHash`` -> ``SpecHash``)."""
    capitalized = key[:1].upper() + key[1:]
    return capitalized.encode("latin-1", "replace")


def write_pdf(
    svg: str, out_path: str | Path, meta: dict[str, str] | None = None
) -> WriteResult:
    """Print ``svg`` to ``out_path`` and return the path + a CapabilityReport (invariant 6).

    A PDF faithfully reproduces the canonical SVG, so every visual axis is ``full`` and glyphs are
    self-contained (``fonts_embedded=full``). ``meta`` is embedded as an Info dictionary via an
    append-only incremental update; ``metadata`` is reported ``full`` only if that actually
    succeeds. Arabic is painted correctly but its extractable text layer is not searchable, so a
    text-layer warning is attached for RTL diagrams (``searchable_rtl_text=False``)."""
    from tarseem.export.result import WriteResult
    from tarseem.report import faithful_svg_render_report

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    data = _render_pdf(svg)
    embedded = False
    if meta:
        with_info = _append_provenance(data, meta)
        if with_info is not None:
            data, embedded = with_info, True
    out.write_bytes(data)
    report = faithful_svg_render_report(
        "pdf",
        svg=svg,
        fonts_embedded="full",
        metadata="full" if embedded else "none",
        searchable_rtl_text=False,
    )
    return WriteResult(path=out, report=report)
