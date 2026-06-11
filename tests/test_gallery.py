"""Gallery builder (A6/A9): static HTML index + per-sample detail pages.

The gallery is the shared fixture for manual review, E2E, screenshot regression, and docs
(09 §2 — one corpus, four consumers). It is dependency-light: thumbnails are the inline
canonical SVG (no Chromium needed to build the index), PNG is a best-effort download. A
sample that fails to render is recorded, never silently dropped (invariant 6).
"""
from __future__ import annotations

import json
from pathlib import Path

from tarseem.gallery import build_gallery

# pure-Python families (no Node/ELK) keep the builder test fast and hermetic
PURE_SAMPLES = ["examples/sequence-login.json", "examples/swimlane-phases.json"]


def _build(tmp_path: Path, paths=PURE_SAMPLES, with_png=False):
    return build_gallery([Path(p) for p in paths], tmp_path, with_png=with_png)


def test_build_writes_index_and_detail_pages(tmp_path):
    _build(tmp_path)
    index = tmp_path / "index.html"
    assert index.exists()
    html = index.read_text(encoding="utf-8")
    assert "Login" in html and "Order Flow" in html  # titles from meta
    for name in ("sequence-login", "swimlane-phases"):
        detail = tmp_path / f"{name}.html"
        assert detail.exists()
        assert f'href="{name}.html"' in html  # index links to detail


def test_detail_page_has_inline_svg_spec_and_metrics(tmp_path):
    _build(tmp_path)
    detail = (tmp_path / "sequence-login.html").read_text(encoding="utf-8")
    assert "<svg" in detail  # canonical artifact inlined
    assert "diagramType" in detail  # spec JSON shown
    assert "crossings" in detail and "node_count" in detail  # RenderReport metrics
    assert 'href="samples/sequence-login.svg"' in detail  # download link


def test_sample_svg_artifact_is_written(tmp_path):
    _build(tmp_path)
    svg = tmp_path / "samples" / "sequence-login.svg"
    assert svg.exists()
    assert svg.read_text(encoding="utf-8").lstrip().startswith("<")


def test_result_reports_each_sample_ok(tmp_path):
    result = _build(tmp_path)
    assert {s.name for s in result.samples} == {"sequence-login", "swimlane-phases"}
    assert all(s.ok for s in result.samples)
    assert all(s.report is not None for s in result.samples)


def test_invalid_sample_is_recorded_not_fatal(tmp_path):
    bad = tmp_path / "broken.json"
    bad.write_text(json.dumps({"diagramType": "flowchart"}), encoding="utf-8")  # no specVersion
    result = build_gallery([bad, Path("examples/sequence-login.json")], tmp_path, with_png=False)
    by_name = {s.name: s for s in result.samples}
    assert by_name["broken"].ok is False and by_name["broken"].error
    assert by_name["sequence-login"].ok is True  # build continued past the failure
    # the index still builds and flags the failure
    assert "broken" in (tmp_path / "index.html").read_text(encoding="utf-8")


def test_index_is_deterministic(tmp_path):
    a = _build(tmp_path)
    b = build_gallery([Path(p) for p in PURE_SAMPLES], tmp_path / "again", with_png=False)
    assert (tmp_path / "index.html").read_text(encoding="utf-8") == \
           (tmp_path / "again" / "index.html").read_text(encoding="utf-8")
    assert [s.name for s in a.samples] == [s.name for s in b.samples]
