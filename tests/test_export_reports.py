"""Uniform per-format CapabilityReports for the faithful-render writers (png, pdf) and the
provenance byte-surgery they rely on (invariant 6 + sub-stage 5).

The risky logic — the PNG ``tEXt`` inserter and the PDF incremental-update Info dictionary — is
unit-tested on synthetic bytes so it runs without a browser and pins structure/determinism exactly.
The end-to-end writer + engine.export integration is Chromium-gated (skips cleanly when absent).
"""
from __future__ import annotations

import hashlib
import io
import json
import re
from pathlib import Path

import pytest
from PIL import Image

from tarseem import Engine
from tarseem.export.metadata import as_text
from tarseem.export.pdf import _append_provenance
from tarseem.export.png import _png_with_text

# Availability via the shared pool: driver-only probe, no browser cold-launch at collection.
from tarseem.render.browser import chromium_executable
from tarseem.report import FEATURES, faithful_svg_render_report

requires_chromium = pytest.mark.skipif(
    chromium_executable() is None, reason="Chromium unavailable"
)


def _spec(name: str) -> dict:
    return json.loads(Path(f"examples/{name}.json").read_text(encoding="utf-8"))


# --- the shared faithful-render report --------------------------------------------------------


def test_faithful_report_marks_every_visual_axis_full():
    """A faithful render reproduces the SVG picture, so every axis except the two medium ones is
    full — this is the honest core of 'uniform reports', not all-full ceremony."""
    r = faithful_svg_render_report("png", svg="<svg></svg>", fonts_embedded="full", metadata="full")
    medium = {"fonts_embedded", "metadata"}
    assert all(r.supports[f] == "full" for f in FEATURES if f not in medium)
    assert not r.lossy  # all full + no warnings


def test_faithful_report_carries_the_medium_axes_through():
    r = faithful_svg_render_report("png", svg="<svg></svg>", fonts_embedded="full", metadata="none")
    assert r.supports["metadata"] == "none"
    assert r.lossy  # metadata != full


def test_pdf_text_layer_warning_only_fires_on_rtl():
    """rtl_shaping stays full (the picture is shaped correctly); the searchable-text loss is a
    warning, and only when the diagram actually has RTL — never noise on a Latin diagram."""
    ltr = faithful_svg_render_report(
        "pdf", svg="<svg><text>hi</text></svg>", fonts_embedded="full",
        metadata="full", searchable_rtl_text=False,
    )
    assert ltr.supports["rtl_shaping"] == "full"
    assert not ltr.lossy and ltr.warnings == ()

    rtl = faithful_svg_render_report(
        "pdf", svg='<svg><text direction="rtl">مرحبا</text></svg>', fonts_embedded="full",
        metadata="full", searchable_rtl_text=False,
    )
    assert rtl.supports["rtl_shaping"] == "full"  # shaping is fine; only extraction is lossy
    assert [w.code for w in rtl.warnings] == ["text-layer-lossy"]
    assert rtl.warnings[0].feature == "rtl_shaping"


# --- PNG tEXt inserter (pixel-safe, deterministic) -------------------------------------------


def _tiny_png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (3, 2), (10, 20, 30)).save(buf, format="PNG")
    return buf.getvalue()


def test_png_text_chunk_is_inserted_before_iend_with_valid_crc():
    raw = _tiny_png()
    out = _png_with_text(raw, b"tarseem", b"specHash=abc")
    assert b"tEXttarseem\x00specHash=abc" in out
    # IEND remains the final chunk
    assert out.rindex(b"IEND") > out.rindex(b"tEXt")
    # the new image still decodes (CRC + structure valid) and pixels are unchanged
    assert Image.open(io.BytesIO(out)).convert("RGB").tobytes() == \
        Image.open(io.BytesIO(raw)).convert("RGB").tobytes()


def test_png_text_insertion_is_deterministic():
    raw = _tiny_png()
    assert _png_with_text(raw, b"tarseem", b"x=1") == _png_with_text(raw, b"tarseem", b"x=1")


# --- PDF incremental-update Info dictionary ---------------------------------------------------


_CLASSIC_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<</Producer (Skia/PDF)>>\nendobj\n"
    b"9 0 obj\n<</Type /Catalog>>\nendobj\n"
    b"xref\n0 10\n0000000000 65535 f \n"
    b"trailer\n<</Size 10 /Root 9 0 R /Info 1 0 R>>\nstartxref\n9\n%%EOF\n"
)


def test_pdf_provenance_appends_a_valid_incremental_update():
    out = _append_provenance(_CLASSIC_PDF, {"specHash": "abc", "diagramType": "flowchart"})
    assert out is not None
    assert out.startswith(_CLASSIC_PDF)  # append-only: not one base byte rewritten
    assert out.rstrip().endswith(b"%%EOF")
    # the appended trailer supersedes /Info to the next free object (10), chains /Prev to the base
    tail = out[out.rindex(b"startxref"):]
    assert b"/Info 10 0 R" in out and b"/Prev 9" in out and b"/Size 11" in out
    # the recorded xref offset lands exactly on '10 0 obj' (catches any arithmetic slip)
    startxref = int(re.search(rb"startxref\s+(\d+)", tail).group(1))
    assert out[startxref:startxref + 4] == b"xref"
    obj_off = int(re.search(rb"\n(\d{10}) 00000 n", out[startxref:]).group(1))
    assert out[obj_off:obj_off + len(b"10 0 obj")] == b"10 0 obj"
    assert b"/SpecHash (abc)" in out and b"/DiagramType (flowchart)" in out


def test_pdf_provenance_escapes_literal_string_metacharacters():
    out = _append_provenance(_CLASSIC_PDF, {"theme": "a(b)c\\d"})
    assert out is not None
    assert rb"/Theme (a\(b\)c\\d)" in out


def test_pdf_provenance_is_deterministic():
    meta = {"specHash": "deadbeef"}
    assert _append_provenance(_CLASSIC_PDF, meta) == _append_provenance(_CLASSIC_PDF, meta)


def test_pdf_provenance_returns_none_on_non_classic_trailer():
    """Safe failure: an xref-stream PDF (no classic trailer) embeds nothing rather than risk a
    corrupt file — write_pdf then honestly reports metadata=none."""
    xref_stream = b"%PDF-1.5\n5 0 obj\n<</Type /XRef /Size 6>>\nstream\n...\nendstream\nendobj\n"
    assert _append_provenance(xref_stream, {"specHash": "x"}) is None


def test_as_text_is_a_compact_kv_line():
    assert as_text({"a": "1", "b": "2"}) == "a=1 b=2"


# --- drawio stale-report regression -----------------------------------------------------------


def test_drawio_reports_embedded_font_as_full_not_stale_none():
    """Round 7 embeds the Cairo subset into the .drawio, so fonts_embedded must report 'full'.
    Guards against the report drifting back to the pre-embed 'none' (a dishonest pivot)."""
    from tarseem.export import write_drawio

    diagram = Engine().render(_spec("swimlane-pipeline")).diagram
    report = write_drawio(diagram, Path("out/_reports_drawio.drawio")).report
    assert report.supports["fonts_embedded"] == "full"


# --- engine.export uniform recording (drawio path needs no browser) ---------------------------


def test_export_records_a_report_per_format_and_svg_carries_none(tmp_path):
    """Every writer-backed format records a CapabilityReport; the canonical SVG is the reference
    the others report against and carries none (it cannot be lossy w.r.t. itself)."""
    result = Engine().render(_spec("swimlane-pipeline"))
    result.export(["svg", "drawio"], tmp_path, name="d")
    assert "svg" not in result.reports
    assert result.reports["drawio"].writer == "drawio"


def test_lossy_export_writes_a_sidecar_clean_export_does_not(tmp_path):
    """A lossy export (Arabic drawio) sidecars its report; nothing else does."""
    result = Engine().render(_spec("arabic-flowchart"))
    result.export(["drawio"], tmp_path, name="d")
    assert result.reports["drawio"].lossy
    assert (tmp_path / "d.drawio.report.json").exists()


# --- Chromium-gated end-to-end: the real png/pdf writers + engine wiring -----------------------


@requires_chromium
def test_write_png_embeds_provenance_and_reports_full(tmp_path):
    from tarseem.export import write_png
    from tarseem.export.metadata import provenance

    r = Engine().render(_spec("flowchart"))
    res = write_png(r.to_svg(provenance=True), tmp_path / "d.png", meta=provenance(r))
    assert b"tEXt" in res.path.read_bytes()
    assert res.report.writer == "png"
    assert res.report.supports["metadata"] == "full"
    assert not res.report.lossy  # a Latin raster is fully faithful → no sidecar


@requires_chromium
def test_write_pdf_embeds_provenance_and_is_deterministic(tmp_path):
    from tarseem.export import write_pdf
    from tarseem.export.metadata import provenance

    r = Engine().render(_spec("flowchart"))
    svg, meta = r.to_svg(provenance=True), provenance(r)
    res = write_pdf(svg, tmp_path / "d.pdf", meta)
    raw = res.path.read_bytes()
    assert res.report.supports["metadata"] == "full"
    assert b"/SpecHash" in raw and raw[:5] == b"%PDF-" and b"/Count 1" in raw
    b = write_pdf(svg, tmp_path / "d2.pdf", meta).path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == hashlib.sha256(b).hexdigest()


@requires_chromium
def test_arabic_pdf_reports_text_layer_ceiling(tmp_path):
    from tarseem.export import write_pdf
    from tarseem.export.metadata import provenance

    r = Engine().render(_spec("arabic-flowchart"))
    res = write_pdf(r.to_svg(provenance=True), tmp_path / "ar.pdf", provenance(r))
    assert res.report.lossy
    assert [w.code for w in res.report.warnings] == ["text-layer-lossy"]


@requires_chromium
def test_engine_export_png_pdf_record_reports(tmp_path):
    result = Engine().render(_spec("flowchart"))
    result.export(["png", "pdf"], tmp_path, name="d")
    assert result.reports["png"].writer == "png"
    assert result.reports["pdf"].writer == "pdf"
    # clean Latin exports embed metadata → not lossy → no sidecars
    assert not (tmp_path / "d.png.report.json").exists()
    assert not (tmp_path / "d.pdf.report.json").exists()
