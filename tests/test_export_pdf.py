"""PDF export — single-page, vector, font-embedded, deterministic (Phase 6, 08 §export).

PDF is a thin Chromium render of the canonical SVG (like PNG), so it drops nothing and carries
no CapabilityReport. The render needs a Playwright Chromium; those tests skip cleanly when it is
absent (CI installs it) and otherwise run ``svg_to_pdf`` for real so a writer bug fails — it is
not swallowed. The date-normalization unit test is browser-free and always runs.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from tarseem import Engine
from tarseem.export import svg_to_pdf
from tarseem.export.pdf import _normalize_pdf_dates


def _chromium_ok() -> bool:
    """Probe once: True iff a Playwright Chromium can launch (covers playwright-not-installed)."""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            browser.close()
        return True
    except Exception:  # noqa: BLE001 - any failure means the render layer can't run here
        return False


requires_chromium = pytest.mark.skipif(not _chromium_ok(), reason="Chromium unavailable")


def _svg(name: str) -> str:
    """Canonical SVG for an example (swimlane/sequence families need no Node runtime)."""
    spec = json.loads(Path(f"examples/{name}.json").read_text(encoding="utf-8"))
    return Engine().render(spec).to_svg(provenance=True)


# --- pure: determinism normalization (no browser) --------------------------------------------

def test_normalize_pdf_dates_is_same_length_and_constant():
    raw = (
        b"2 0 obj\n<</CreationDate (D:20260614174850+00'00')\n"
        b"/ModDate (D:20991231235959-05'00')>>\nendobj"
    )
    out = _normalize_pdf_dates(raw)
    # same length => byte offsets (and the xref table) are preserved
    assert len(out) == len(raw)
    # both Info dates pinned to the constant; no live wall-clock digits survive
    assert out.count(b"D:19700101000000") == 2
    assert b"20260614174850" not in out and b"20991231235959" not in out
    # the timezone suffix and surrounding structure are untouched
    assert b"-05'00'" in out and b"endobj" in out


def test_normalize_pdf_dates_ignores_unrelated_digit_runs():
    """Anchored on the field name: a stray 14-digit number must not be rewritten."""
    raw = b"/Length 12345678901234\n/CreationDate (D:20260101000000Z)"
    out = _normalize_pdf_dates(raw)
    assert b"/Length 12345678901234" in out
    assert b"D:19700101000000" in out


# --- render: structure, sizing, determinism (need Chromium) ----------------------------------

@pytest.fixture(scope="module")
def swimlane_pdf(tmp_path_factory) -> bytes:
    out = tmp_path_factory.mktemp("pdf") / "swimlane.pdf"
    return svg_to_pdf(_svg("swimlane-pipeline"), out).read_bytes()


@requires_chromium
def test_pdf_is_valid_and_self_contained(swimlane_pdf: bytes):
    assert swimlane_pdf[:5] == b"%PDF-"
    assert b"%%EOF" in swimlane_pdf
    # Glyph outlines travel in the file (Skia carries web-font glyphs as Type3 procedures, or an
    # embedded subset), so it renders with zero fonts installed — verified visually vs the PNG.
    assert b"/Type3" in swimlane_pdf or b"/FontFile" in swimlane_pdf


@requires_chromium
@pytest.mark.parametrize("name", ["sequence-login", "swimlane-vertical-release"])
def test_pdf_is_a_single_page(name: str, tmp_path):
    """The part of png.py that does NOT transfer: page.pdf paginates. A tall and a wide diagram
    must each fit one page (no clip, no hairline spill)."""
    pdf = svg_to_pdf(_svg(name), tmp_path / f"{name}.pdf").read_bytes()
    assert re.search(rb"/Count\s+1\b", pdf), "Pages tree must report exactly one page"
    assert len(re.findall(rb"/Type\s*/Page[^s]", pdf)) == 1


@requires_chromium
def test_pdf_bytes_identical_across_runs(tmp_path):
    """Determinism (invariant 7) — load-bearing: catches a Chromium that changes the date format,
    adds an /ID, or moves dates into a compressed stream."""
    svg = _svg("swimlane-pipeline")
    a = svg_to_pdf(svg, tmp_path / "a.pdf").read_bytes()
    b = svg_to_pdf(svg, tmp_path / "b.pdf").read_bytes()
    assert hashlib.sha256(a).hexdigest() == hashlib.sha256(b).hexdigest()
    assert b"D:19700101000000" in a  # the wall-clock stamp was pinned, not left live


@requires_chromium
def test_export_writes_pdf_via_engine(tmp_path):
    """The engine.export() dispatch + package wiring produce a real .pdf."""
    spec = json.loads(Path("examples/swimlane-pipeline.json").read_text(encoding="utf-8"))
    written = Engine().render(spec).export(["pdf"], tmp_path, name="d")
    assert written["pdf"].name == "d.pdf"
    assert written["pdf"].read_bytes()[:5] == b"%PDF-"
