"""draw.io writer tests (Phase 6, 08 §3, D2:C).

Structure/geometry/RTL/determinism are asserted in pure Python by parsing the emitted XML.
The headless draw.io CLI round-trip (08 §3) runs only when a ``drawio`` binary is available
(env ``TARSEEM_DRAWIO_CLI`` or on PATH) — it is validation-only, never in the render path.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from defusedxml.ElementTree import fromstring

from tarseem import Engine
from tarseem.export.drawio import to_drawio_xml, write_drawio

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def _render(spec_name: str):
    spec = json.loads((EXAMPLES / spec_name).read_text(encoding="utf-8"))
    return Engine().render(spec)


def _xml(spec_name: str) -> str:
    return to_drawio_xml(_render(spec_name).diagram)


def _cells(xml: str) -> list:
    root = fromstring(xml.split("\n", 1)[1] if xml.startswith("<!--") else xml)
    return root.findall(".//mxCell")


# --- structure -------------------------------------------------------------

def test_emits_uncompressed_parseable_mxgraph():
    xml = _xml("flowchart.json")
    # Plain XML, not the base64+deflate payload draw.io also accepts.
    assert "<mxGraphModel" in xml and "<root>" in xml
    cells = _cells(xml)
    ids = {c.get("id") for c in cells}
    assert {"0", "1"} <= ids  # the two structural root cells


def test_every_node_becomes_a_vertex_cell():
    result = _render("flowchart.json")
    xml = to_drawio_xml(result.diagram)
    vertices = [c for c in _cells(xml) if c.get("vertex") == "1"]
    node_cells = [c for c in vertices if (c.get("id") or "").startswith("n_")]
    assert len(node_cells) == len(result.diagram.nodes)


def test_swimlane_emits_lane_band_and_chip_cells_not_native():  # ADR-007
    result = _render("swimlane-pipeline.json")
    xml = to_drawio_xml(result.diagram)
    cells = _cells(xml)
    # ADR-007: explicit rects, NOT native draw.io swimlanes.
    assert all("swimlane;" not in c.get("style", "") for c in cells)
    bands = [c for c in cells if (c.get("id") or "").startswith("lane_")]
    chips = [c for c in cells if (c.get("id") or "").startswith("lanechip_")]
    assert len(bands) == len(result.diagram.lanes)
    assert len(chips) == len(result.diagram.lanes)


def test_nodes_parented_to_layer_with_absolute_geometry():  # ADR-007
    result = _render("swimlane-pipeline.json")
    xml = to_drawio_xml(result.diagram)
    by_id = {c.get("id"): c for c in _cells(xml)}
    node = result.diagram.nodes[0]
    cell = by_id[f"n_{node.id}"]
    assert cell.get("parent") == "1"  # lanes are no longer containers
    geo = cell.find("mxGeometry")
    assert abs(float(geo.get("x")) - node.x) < 0.01  # absolute, not lane-relative
    assert abs(float(geo.get("y")) - node.y) < 0.01


def test_edges_carry_exact_route_points():
    result = _render("flowchart.json")
    xml = to_drawio_xml(result.diagram)
    edge_cells = [c for c in _cells(xml) if c.get("edge") == "1"]
    assert len(edge_cells) == len(result.diagram.edges)
    multi = [e for e in result.diagram.edges if len(e.points) > 2]
    if multi:
        # an edge with interior bends emits an <Array as="points"> of mxPoints
        arrays = [c for c in edge_cells if c.find(".//Array[@as='points']") is not None]
        assert arrays


def test_node_geometry_matches_ir():
    result = _render("flowchart.json")
    xml = to_drawio_xml(result.diagram)
    by_id = {c.get("id"): c for c in _cells(xml)}
    node = result.diagram.nodes[0]
    cell = by_id[f"n_{node.id}"]
    geo = cell.find("mxGeometry")
    # non-laned node: geometry is absolute (parent layer "1")
    assert abs(float(geo.get("width")) - node.width) < 0.01
    assert abs(float(geo.get("height")) - node.height) < 0.01


# --- shape style keys (draw.io round-trip caught these) --------------------

def test_diamond_uses_shape_rhombus_not_boolean():
    # `rhombus=1` parses as a stray property and draw.io falls back to a rectangle; the shape
    # MUST be named via shape=rhombus. Regression for the round-trip-caught diamond bug.
    xml = _xml("arabic-flowchart.json")
    assert "shape=rhombus" in xml
    assert "rhombus=1" not in xml


def test_er_renders_as_table_not_folded_label():  # bug #2
    # ER entity = explicit table matching render/er.py (title bar + rows + PK/FK pills),
    # NOT folded label text. Regression for "drawio ER lacks UI details/theming".
    xml = _xml("er-shop.json")
    ids = {c.get("id") for c in _cells(xml)}
    assert "er_order" in ids  # container
    assert "ertitle_order" in ids  # dark title bar
    assert any((i or "").startswith("erattr_order_") for i in ids)  # attribute rows
    assert any((i or "").startswith("erkey_order_") for i in ids)  # PK/FK pills
    # no folded-into-label artifact remains
    assert "<br>" not in xml


def test_rtl_node_label_is_centered_not_right_aligned():  # bug #1/#3
    # RTL controls bidi direction only; block alignment stays centered (matches the SVG).
    xml = _xml("arabic-flowchart.json")
    assert "writingDirection=rtl" in xml
    assert "align=right" not in xml


def test_numbered_badge_is_a_corner_circle_not_folded():  # bug #3/#4
    result = _render("swimlane-pipeline.json")
    xml = to_drawio_xml(result.diagram)
    ids = {c.get("id") for c in _cells(xml)}
    badged = [n for n in result.diagram.nodes if n.badge]
    assert badged, "fixture should have numbered nodes"
    assert any((i or "").startswith("badge_") for i in ids)  # ellipse badge cell
    # badge no longer prefixes the node label
    by_id = {c.get("id"): c for c in _cells(xml)}
    n = badged[0]
    assert not (by_id[f"n_{n.id}"].get("value", "")).startswith(n.badge)


def _badge_center_x(xml: str, node) -> float:
    by_id = {c.get("id"): c for c in _cells(xml)}
    geo = by_id[f"badge_{node.id}"].find("mxGeometry")
    return float(geo.get("x")) + float(geo.get("width")) / 2


def test_ltr_badge_circle_on_right_corner():  # note #5 — default LTR -> right
    result = _render("swimlane-pipeline.json")
    xml = to_drawio_xml(result.diagram)
    n = next(n for n in result.diagram.nodes if n.badge)
    assert _badge_center_x(xml, n) > n.x + n.width / 2


def test_rtl_badge_circle_on_left_corner():  # note #5 — default RTL -> left
    result = _render("swimlane-document-rtl.json")
    xml = to_drawio_xml(result.diagram)
    n = next(n for n in result.diagram.nodes if n.badge)
    assert _badge_center_x(xml, n) < n.x + n.width / 2


def test_badge_corner_flag_overrides_direction():  # note #5 — opt-in theme.badgeCorner
    spec = json.loads((EXAMPLES / "swimlane-pipeline.json").read_text(encoding="utf-8"))
    spec["theme"] = {**spec.get("theme", {}), "badgeCorner": "left"}
    result = Engine().render(spec)
    xml = to_drawio_xml(result.diagram)
    n = next(n for n in result.diagram.nodes if n.badge)
    assert _badge_center_x(xml, n) < n.x + n.width / 2  # forced left despite LTR


def test_end_marker_is_a_bullseye_with_inner_dot():  # bug #4
    result = _render("swimlane-pipeline.json")
    xml = to_drawio_xml(result.diagram)
    ids = {c.get("id") for c in _cells(xml)}
    if any(m.kind == "end" for m in result.diagram.markers):
        assert any((i or "").startswith("markerdot_end") for i in ids)
    assert "fillColor=#000000" in xml  # markers use black, matching the SVG


def _chip_x(xml: str, lane_id: str) -> float:
    by_id = {c.get("id"): c for c in _cells(xml)}
    return float(by_id[f"lanechip_{lane_id}"].find("mxGeometry").get("x"))


def test_rtl_swimlane_flips_header_chip_to_the_right():  # ADR-007 — the core RTL fix
    result = _render("swimlane-document-rtl.json")
    xml = to_drawio_xml(result.diagram)
    band = result.diagram.lanes[0]
    chip_x = _chip_x(xml, band.id)
    # RTL: chip sits on the right half of its band (flow-start side), not the left.
    assert chip_x > band.x + band.width / 2


def test_ltr_swimlane_keeps_header_chip_on_the_left():
    result = _render("swimlane-pipeline.json")
    xml = to_drawio_xml(result.diagram)
    band = result.diagram.lanes[0]
    assert _chip_x(xml, band.id) < band.x + band.width / 2


# --- RTL -------------------------------------------------------------------

def test_rtl_labels_get_writing_direction():
    xml = _xml("arabic-flowchart.json")
    assert "writingDirection=rtl" in xml


# --- determinism (invariant 7 / A3) ---------------------------------------

def test_output_is_byte_identical_across_renders():
    a = to_drawio_xml(_render("swimlane-pipeline.json").diagram)
    b = to_drawio_xml(_render("swimlane-pipeline.json").diagram)
    assert a == b


def test_no_wallclock_in_provenance():
    from tarseem.export.metadata import provenance

    meta = provenance(_render("flowchart.json"))
    assert "timestamp" not in {k.lower() for k in meta}
    assert meta["specHash"]


# --- capability report (invariant 6) --------------------------------------

def test_capability_report_present_and_on_shared_vocabulary(tmp_path):
    from tarseem.report import FEATURES

    result = write_drawio(_render("swimlane-phases.json").diagram, tmp_path / "d.drawio")
    rep = result.report
    assert rep.writer == "drawio"
    assert set(rep.supports) <= set(FEATURES)
    # ADR-007: phase bands are now drawn (full), and lanes carry an editability-limited note.
    assert rep.supports["phases"] == "full"
    assert any(w.feature == "lanes" for w in rep.warnings)


def test_export_writes_sidecar_for_lossy_writer(tmp_path):
    result = _render("swimlane-phases.json")
    written = result.export(["drawio"], tmp_path, name="d")
    assert written["drawio"].exists()
    sidecar = written["drawio"].with_suffix(".drawio.report.json")
    assert sidecar.exists()
    payload = json.loads(sidecar.read_text(encoding="utf-8"))
    assert payload["writer"] == "drawio"
    assert payload["lossy"] is True


# --- headless round-trip (CI-only; 08 §3, R-18) ---------------------------

def _drawio_cli() -> str | None:
    return os.environ.get("TARSEEM_DRAWIO_CLI") or shutil.which("drawio")


@pytest.mark.skipif(_drawio_cli() is None, reason="draw.io CLI not available")
def test_drawio_cli_reexports_headless(tmp_path):
    src = tmp_path / "rt.drawio"
    write_drawio(_render("swimlane-pipeline.json").diagram, src)
    out = tmp_path / "rt.pdf"
    proc = subprocess.run(  # noqa: S603 - CLI path is operator-provided
        [_drawio_cli(), "-x", "-f", "pdf", "-o", str(out), str(src)],
        capture_output=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")
    assert out.exists() and out.stat().st_size > 0
