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


# --- review round 5 (owner-reported) --------------------------------------------------

def test_drawio_cube_flips_to_match_engine_facing():
    # draw.io's cube extrudes depth top-LEFT (mirror of the engine); flipH=1 mirrors it so the
    # front face is bottom-left like the SVG (and the separate label cell then sits on it).
    style = _cellmap(to_drawio_xml(_render("deployment-web-stack").diagram))["n_browser"].get(
        "style", ""
    )
    assert "shape=cube" in style and "flipH=1" in style


def test_drawio_cylinder_cap_matches_engine_ry():
    # size=9 == render/svg.py cylinder ry → shallow cap (engine's tall-can look), not the deep
    # default cap that reads as a shorter cylinder.
    cells = _cellmap(to_drawio_xml(_render("deployment-web-stack").diagram))
    assert "shape=cylinder3;size=9" in cells["n_db"].get("style", "")


def test_drawio_node_label_defaults_to_engine_text_color():
    # a node with no spec text colour gets the engine default #14281D, not mxGraph black.
    style = _cellmap(to_drawio_xml(_render("deployment-web-stack").diagram))["n_browser"].get(
        "style", ""
    )
    assert "fontColor=#14281D" in style


def test_drawio_sequence_emits_centered_title():
    cell = _cellmap(to_drawio_xml(_render("sequence-login").diagram)).get("title")
    assert cell is not None and cell.get("value") == "Login"
    assert "align=center" in cell.get("style", "")


def test_drawio_names_cairo_with_sans_fallback():
    # references the SVG's font; sans-serif fallback keeps text sans (never browser serif) where
    # Cairo isn't installed — fonts-embedded ceiling.
    assert "fontFamily=Cairo,sans-serif" in to_drawio_xml(_render("swimlane-pipeline").diagram)


def test_drawio_er_key_pill_radius_matches_svg():
    assert "absoluteArcSize=1;arcSize=3" in to_drawio_xml(_render("er-shop").diagram)


def test_sequence_label_gap_unified_across_writers():
    # the message-label lift is one shared constant so SVG and draw.io keep the same gap.
    from tarseem.export.drawio import _SEQ_LABEL_GAP
    from tarseem.render.sequence import _LABEL_LIFT

    assert _LABEL_LIFT == _SEQ_LABEL_GAP
    assert "spacingBottom=4" in to_drawio_xml(_render("sequence-login").diagram)


# --- review round 6 (owner-reported) --------------------------------------------------

def test_drawio_fill_only_chrome_has_no_black_border():
    # SVG lane chips + title bar are fill-only; without strokeColor=none mxGraph draws a default
    # black border ("actor/user shapes have black borders").
    cells = _cellmap(to_drawio_xml(_render("swimlane-pipeline").diagram))
    assert "strokeColor=none" in cells["title"].get("style", "")
    chip = next(c for cid, c in cells.items() if (cid or "").startswith("lanechip_"))
    assert "strokeColor=none" in chip.get("style", "")


def test_drawio_er_title_has_no_black_border():
    cells = _cellmap(to_drawio_xml(_render("er-shop").diagram))
    assert "strokeColor=none" in cells["ertitle_order"].get("style", "")


def test_drawio_embeds_cairo_font_subset():
    # one registering cell carries fontSource (a data: URI) so the file renders in Cairo with no
    # install — zero-dependency parity, raising the fonts ceiling.
    xml = to_drawio_xml(_render("swimlane-pipeline").diagram)
    assert "fontSource=" in xml and "data%3Afont%2Fwoff2" in xml


def test_drawio_embedded_font_is_deterministic():
    # same spec -> byte-identical XML (subset is timestamp-free + codepoint-sorted) (A3).
    a = to_drawio_xml(_render("swimlane-pipeline").diagram)
    b = to_drawio_xml(_render("swimlane-pipeline").diagram)
    assert a == b


# --- review round 8 (owner-reported) --------------------------------------------------

def test_drawio_state_pseudostates_render_as_ellipses():
    # initial/final have no _SHAPE_STYLE entry -> were plain white boxes; now ellipses like the SVG.
    cells = _cellmap(to_drawio_xml(_render("state-order-lifecycle").diagram))
    assert "ellipse" in cells["state_start"].get("style", "")
    assert "ellipse" in cells["state_done"].get("style", "")
    assert "statedot_done" in cells  # final bullseye inner dot


def test_chrome_radius_unified_and_crisp():
    from tarseem.export.drawio import _CHROME_RADIUS as D_R
    from tarseem.render.swimlane import _CHROME_RADIUS as S_R

    assert S_R == D_R == 3.0
    assert "absoluteArcSize=1;arcSize=3" in to_drawio_xml(_render("swimlane-phases").diagram)
    assert "absoluteArcSize=1;arcSize=3" in to_drawio_xml(
        _render("swimlane-nested-delivery").diagram
    )
    assert 'rx="3"' in _render("swimlane-phases").svg  # SVG phase band uses the same crisp radius


def test_svg_edge_labels_have_no_white_slab():
    # owner: white box behind link text -> transparent. The old halo rect is gone in all writers.
    for name in ("state-order-lifecycle", "swimlane-pipeline", "er-shop"):
        assert 'fill="#FFFFFF" opacity="0.85"' not in _render(name).svg


def test_svg_3d_shapes_get_a_drop_shadow():
    svg = _render("deployment-web-stack").svg  # cube + cylinder
    assert "tarseem-shadow" in svg and "feDropShadow" in svg
