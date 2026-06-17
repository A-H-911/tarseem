"""Phase 7 / F11 — the agent surface: generate() + JSON error contract + schema bundle."""
from __future__ import annotations

import json
import shutil

import pytest

from tarseem import generate, schema_bundle
from tarseem.cli import main

requires_node = pytest.mark.skipif(
    shutil.which("node") is None, reason="Node.js runtime not on PATH"
)

SWIMLANE = {  # lane-grid layouter -> no Node, no Chromium
    "specVersion": "0.1",
    "diagramType": "swimlane",
    "direction": "LR",
    "meta": {"title": "Tiny"},
    "lanes": [{"id": "a", "label": {"text": "A"}}],
    "nodes": [{"id": "n1", "lane": "a", "label": {"text": "One"}}],
    "edges": [],
}
FLOWCHART = {
    "specVersion": "0.1",
    "diagramType": "flowchart",
    "meta": {"title": "F"},
    "nodes": [{"id": "a", "label": {"text": "A"}}, {"id": "b", "label": {"text": "B"}}],
    "edges": [{"id": "e", "source": "a", "target": "b"}],
}
INVALID = {"diagramType": "flowchart"}  # missing required specVersion


# ---- generate(): success shape -----------------------------------------------
def test_generate_returns_inline_svg_by_default():
    out = generate(SWIMLANE)
    assert out["ok"] is True
    assert out["svg"].lstrip().startswith("<svg")
    assert out["diagramType"] == "swimlane"
    assert out["artifacts"] == {}  # nothing written without out_dir
    assert set(out) >= {"svg", "report", "capabilities", "warnings", "provenance", "versions"}


def test_generate_payload_is_json_serializable():
    json.dumps(generate(SWIMLANE))  # must not raise — it is the agent's wire format


def test_generate_report_carries_geometry_metrics():
    report = generate(SWIMLANE)["report"]
    assert {"node_count", "edge_count", "crossings", "overlaps", "width", "height"} <= set(report)


# ---- generate(): JSON error contract (never raises) --------------------------
def test_generate_returns_coded_errors_not_exceptions():
    out = generate(INVALID)
    assert out["ok"] is False
    err = out["errors"][0]
    assert set(err) >= {"code", "path", "message", "hint"}  # the 05 §5 contract
    assert err["code"] == "E_SCHEMA"
    assert err["path"].startswith("/")


def test_generate_file_format_without_out_dir_is_a_coded_error():
    out = generate(SWIMLANE, formats=["drawio"])
    assert out["ok"] is False
    assert out["errors"][0]["code"] == "E_OUTPUT"
    assert "out_dir" in out["errors"][0]["hint"]


def test_generate_writes_non_raster_files_in_process(tmp_path):
    out = generate(SWIMLANE, formats=["svg", "drawio"], out_dir=tmp_path, name="deck")
    assert out["ok"] is True
    assert (tmp_path / "deck.svg").exists()
    assert (tmp_path / "deck.drawio").exists()
    assert "drawio" in out["capabilities"]  # CapabilityReport surfaced (invariant 6)


# ---- generate(): raster runs in a subprocess (Chromium pool safety) ----------
@requires_node
def test_generate_raster_runs_via_subprocess(tmp_path):
    out = generate(FLOWCHART, formats=["svg", "png"], out_dir=tmp_path, name="f")
    assert out["ok"] is True
    assert (tmp_path / "f.png").exists()
    assert out["svg"].lstrip().startswith("<svg")  # inline SVG returned alongside the raster


# ---- schema bundle (LLM tool-use / IDE autocomplete) -------------------------
def test_schema_bundle_is_2020_12_with_registered_type_enum():
    bundle = schema_bundle()
    assert bundle["$schema"].endswith("2020-12/schema")
    enum = bundle["properties"]["diagramType"]["enum"]
    assert {"flowchart", "swimlane", "sequence"} <= set(enum)
    assert "specVersion" in bundle["required"]


# ---- CLI faces of the agent surface ------------------------------------------
def test_cli_schema_emits_valid_json(capsys):
    assert main(["schema"]) == 0
    json.loads(capsys.readouterr().out)  # parseable


def test_cli_generate_ok(tmp_path, capsys):
    spec = tmp_path / "s.json"
    spec.write_text(json.dumps(SWIMLANE), encoding="utf-8")
    assert main(["generate", str(spec)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True


def test_cli_generate_invalid_exits_nonzero(tmp_path, capsys):
    spec = tmp_path / "bad.json"
    spec.write_text(json.dumps(INVALID), encoding="utf-8")
    assert main(["generate", str(spec)]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["errors"][0]["code"] == "E_SCHEMA"
