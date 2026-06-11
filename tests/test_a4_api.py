"""A4 — clean Python API `Engine().render(spec).export([...])` + CLI equivalents."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from tarseem import Engine
from tarseem.cli import main
from tarseem.errors import SpecValidationError

requires_node = pytest.mark.skipif(
    shutil.which("node") is None, reason="Node.js runtime not on PATH"
)

SWIMLANE = {
    "specVersion": "0.1",
    "diagramType": "swimlane",
    "direction": "LR",
    "meta": {"title": "Tiny"},
    "lanes": [{"id": "a", "label": {"text": "A"}}, {"id": "b", "label": {"text": "B"}}],
    "nodes": [
        {"id": "n1", "lane": "a", "shape": "stadium", "badge": False, "label": {"text": "One"}},
        {"id": "n2", "lane": "b", "shape": "roundrect", "label": {"text": "Two"}},
    ],
    "edges": [{"id": "e1", "source": "n1", "target": "n2"}],
}

INVALID = {"diagramType": "flowchart"}  # missing specVersion


# ---- Python API -------------------------------------------------------------
def test_render_returns_result_with_canonical_svg():
    result = Engine().render(SWIMLANE)
    assert result.svg.lstrip().startswith("<svg")
    assert "One" in result.svg and "Two" in result.svg


def test_render_rejects_invalid_spec_with_coded_errors():
    with pytest.raises(SpecValidationError) as exc:
        Engine().render(INVALID)
    codes = {e.code for e in exc.value.result.errors}
    assert "E_SCHEMA" in codes


def test_render_dispatches_swimlane_without_node():
    # swimlane uses the lane-grid layouter (no Node runtime needed)
    result = Engine().render(SWIMLANE)
    assert result.diagram.diagram_type == "swimlane"
    assert len(result.diagram.lanes) == 2


def test_export_writes_requested_formats(tmp_path):
    result = Engine().render(SWIMLANE)
    paths = result.export(["svg", "png"], tmp_path, name="tiny")
    assert paths["svg"].exists() and paths["svg"].suffix == ".svg"
    assert paths["png"].exists() and paths["png"].suffix == ".png"
    assert paths["svg"].read_text(encoding="utf-8").lstrip().startswith("<svg")


def test_exported_svg_embeds_provenance():
    result = Engine().render(SWIMLANE)
    svg = result.to_svg(provenance=True)
    assert result.spec_hash[:12] in svg
    assert "tarseem" in svg.lower()


def test_spec_hash_is_stable_and_content_addressed():
    h1 = Engine().render(SWIMLANE).spec_hash
    h2 = Engine().render(json.loads(json.dumps(SWIMLANE))).spec_hash
    assert h1 == h2 == hashlib.sha256(
        json.dumps(SWIMLANE, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


@requires_node
def test_render_graph_family_via_engine():
    spec = json.loads(Path("examples/flowchart.json").read_text(encoding="utf-8"))
    result = Engine().render(spec)
    assert result.diagram.diagram_type == "flowchart"
    assert "<svg" in result.svg


# ---- CLI --------------------------------------------------------------------
def test_cli_validate_ok(capsys):
    spec_path = "examples/swimlane-pipeline.json"
    assert main(["validate", spec_path]) == 0


def test_cli_validate_rejects_invalid(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(INVALID), encoding="utf-8")
    assert main(["validate", str(bad)]) == 1
    out = capsys.readouterr().out
    assert "E_SCHEMA" in out


def test_cli_render_writes_svg(tmp_path):
    spec = tmp_path / "s.json"
    spec.write_text(json.dumps(SWIMLANE), encoding="utf-8")
    out = tmp_path / "out.svg"
    assert main(["render", str(spec), "-o", str(out)]) == 0
    assert out.exists() and out.read_text(encoding="utf-8").lstrip().startswith("<svg")


def test_cli_export_writes_multiple_formats(tmp_path):
    spec = tmp_path / "s.json"
    spec.write_text(json.dumps(SWIMLANE), encoding="utf-8")
    assert main(["export", str(spec), "-f", "svg,png", "-o", str(tmp_path), "-n", "deck"]) == 0
    assert (tmp_path / "deck.svg").exists()
    assert (tmp_path / "deck.png").exists()
