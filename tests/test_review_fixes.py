"""Regression tests for review-round-2 fixes: edge corners, cube label, ER header, sequence."""
from __future__ import annotations

import json
from pathlib import Path

from defusedxml.ElementTree import fromstring

from tarseem import Engine
from tarseem.export.drawio import to_drawio_xml

EX = Path(__file__).resolve().parent.parent / "examples"


def _spec(name: str) -> dict:
    return json.loads((EX / f"{name}.json").read_text(encoding="utf-8"))


def _render(name: str):
    return Engine().render(_spec(name))


def _ids(xml: str) -> set:
    return {c.get("id") for c in fromstring(xml).findall(".//mxCell")}


def _cellmap(xml: str) -> dict:
    return {c.get("id"): c for c in fromstring(xml).findall(".//mxCell")}


# --- edge corners (issue 2): unified, default curved, flag to straighten ---------------

def test_edge_svg_line_curved_vs_straight():
    from tarseem.render.svg import edge_svg_line

    pts = [(0.0, 0.0), (50.0, 0.0), (50.0, 50.0)]
    curved = edge_svg_line(pts, "#000", 1.0, "", True)
    straight = edge_svg_line(pts, "#000", 1.0, "", False)
    assert "<path" in curved and "Q" in curved  # rounded corner
    assert "<polyline" in straight and "Q" not in straight


def test_swimlane_edges_respond_to_corner_flag():
    # Curved (default) turns bent edges into rounded <path>; straight keeps them as <polyline>,
    # so the straight render has strictly more polylines.
    curved = _render("swimlane-pipeline").svg
    spec = _spec("swimlane-pipeline")
    spec["theme"] = {"edgeCorners": "straight"}
    straight = Engine().render(spec).svg
    assert straight.count("<polyline") > curved.count("<polyline")


def test_drawio_edges_rounded_by_default():
    assert "edgeStyle=none;rounded=1" in to_drawio_xml(_render("swimlane-pipeline").diagram)


def test_drawio_edges_straight_with_flag():
    spec = _spec("swimlane-pipeline")
    spec["theme"] = {"edgeCorners": "straight"}
    assert "edgeStyle=none;rounded=0" in to_drawio_xml(Engine().render(spec).diagram)


# --- cube label centres on the front face (issue 1) ------------------------------------

def test_label_center_shifts_for_cube():
    from tarseem.model.ir import Label, PositionedNode
    from tarseem.render.svg import _label_center

    rect = PositionedNode(id="r", x=0.0, y=0.0, width=100.0, height=60.0,
                          label=Label(text="x"), shape="rect")
    cube = PositionedNode(id="c", x=0.0, y=0.0, width=100.0, height=60.0,
                          label=Label(text="x"), shape="cube")
    assert _label_center(rect) == (50.0, 30.0)
    cx, cy = _label_center(cube)
    assert cx < 50.0 and cy > 30.0  # toward the front (down-left) face


# --- ER header artifact fixed: square container (issue 3) ------------------------------

def test_drawio_er_default_is_rounded_no_artifact():
    # Default is rounded (matches the SVG); header shares the radius so it doesn't poke out.
    style = _cellmap(to_drawio_xml(_render("er-shop").diagram))["er_order"].get("style", "")
    assert "rounded=1;" in style


# --- sequence draw.io output now exists (issue 4) -------------------------------------

def test_drawio_sequence_has_lifelines_and_activations():
    ids = _ids(to_drawio_xml(_render("sequence-login").diagram))
    assert any((i or "").startswith("stem_") for i in ids)
    assert any((i or "").startswith("activation_") for i in ids)


# --- style OPTIONS apply to BOTH writers (entityCorners) -------------------------------

def test_entity_corners_option_applies_to_svg():
    assert 'rx="6"' in _render("er-shop").svg  # rounded by default
    spec = _spec("er-shop")
    spec["theme"] = {"entityCorners": "square"}
    assert 'rx="6"' not in Engine().render(spec).svg


def test_entity_corners_option_applies_to_drawio():
    rounded = _cellmap(to_drawio_xml(_render("er-shop").diagram))["er_order"].get("style", "")
    assert "rounded=1;" in rounded
    spec = _spec("er-shop")
    spec["theme"] = {"entityCorners": "square"}
    sq = _cellmap(to_drawio_xml(Engine().render(spec).diagram))["er_order"].get("style", "")
    assert "rounded=0;" in sq


# --- border / edge width honoured (same spec option drives both writers) ---------------

def test_drawio_node_honours_border_width_option():
    spec = _spec("flowchart")
    spec["nodes"][0].setdefault("style", {})["border"] = {"width": 4}
    nid = f"n_{spec['nodes'][0]['id']}"
    style = _cellmap(to_drawio_xml(Engine().render(spec).diagram))[nid].get("style", "")
    assert "strokeWidth=4" in style


def test_drawio_swimlane_edge_width_matches_svg_default():
    assert "strokeWidth=2" in to_drawio_xml(_render("swimlane-pipeline").diagram)  # SVG default 2


# --- text-centric fidelity fixes ------------------------------------------------------

def test_drawio_cube_label_is_separate_front_face_cell():
    ids = _ids(to_drawio_xml(_render("deployment-web-stack").diagram))
    assert any((i or "").startswith("cubelabel_") for i in ids)


def test_drawio_sequence_label_raised_above_line():
    assert "verticalAlign=bottom" in to_drawio_xml(_render("sequence-login").diagram)
