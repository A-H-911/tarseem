"""Phase 5 sub-stage 4 — vertical swimlanes (FR-6.1: horizontal AND vertical lanes).

Vertical lanes = columns side by side, flow top->bottom. Implemented as a uniform
coordinate transpose of the (untouched, byte-identical) horizontal lane-grid layout:
the orientation-invariant logic — topological columns + obstacle-avoiding routing — is
reused; only pixel assignment flips. Node boxes rotate to portrait aspect (documented
limitation, AM-6). Phases are not rendered in the vertical variant (documented).
"""
from __future__ import annotations

from defusedxml.ElementTree import fromstring  # safe parser (project invariant)

from tarseem.layout.lanegrid import LaneGridLayout
from tarseem.measure import measure_graph
from tarseem.model import PositionedDiagram, compile_spec
from tarseem.render import render_svg

# 3 lanes (columns), 4 steps; flow commit -> build -> test -> deploy runs top->bottom.
RELEASE_FLOW = {
    "specVersion": "0.1",
    "diagramType": "swimlane",
    "direction": "TB",
    "meta": {"title": "Release Flow"},
    "layout": {"laneOrientation": "vertical"},
    "lanes": [
        {"id": "dev", "label": {"text": "Dev"}},
        {"id": "ci", "label": {"text": "CI"}},
        {"id": "ops", "label": {"text": "Ops"}},
    ],
    "nodes": [
        {"id": "commit", "lane": "dev", "shape": "stadium", "badge": False,
         "label": {"text": "Commit"}},
        {"id": "build", "lane": "ci", "shape": "roundrect", "label": {"text": "Build"}},
        {"id": "test", "lane": "ci", "shape": "diamond", "label": {"text": "Test"}},
        {"id": "deploy", "lane": "ops", "shape": "roundrect", "label": {"text": "Deploy"}},
    ],
    "edges": [
        {"id": "e1", "source": "commit", "target": "build"},
        {"id": "e2", "source": "build", "target": "test"},
        {"id": "e3", "source": "test", "target": "deploy"},
    ],
}


def _layout(spec: dict) -> PositionedDiagram:
    return LaneGridLayout().layout(measure_graph(compile_spec(spec)))


# ---- compile / IR -----------------------------------------------------------
def test_compile_reads_lane_orientation():
    assert compile_spec(RELEASE_FLOW).lane_orientation == "vertical"


def test_default_orientation_is_horizontal():
    g = compile_spec({**RELEASE_FLOW, "layout": {}})
    assert g.lane_orientation == "horizontal"


def test_layout_marks_diagram_orientation():
    assert _layout(RELEASE_FLOW).orientation == "vertical"


# ---- vertical geometry ------------------------------------------------------
def test_lanes_are_columns_not_rows():
    d = _layout(RELEASE_FLOW)
    bands = list(d.lanes)
    assert len(bands) == 3
    # columns: same top y, increasing x, all taller than wide
    assert len({round(b.y, 3) for b in bands}) == 1  # share a top edge
    xs = [b.x for b in bands]
    assert xs == sorted(xs) and len(set(xs)) == 3  # laid out left->right
    for b in bands:
        assert b.height > b.width  # a column, not a row


def test_nodes_sit_inside_their_lane_column():
    d = _layout(RELEASE_FLOW)
    band_by_id = {b.id: b for b in d.lanes}
    lane_of = {n["id"]: n["lane"] for n in RELEASE_FLOW["nodes"]}
    for n in d.nodes:
        band = band_by_id[lane_of[n.id]]
        assert band.x <= n.x and n.x + n.width <= band.x + band.width


def test_flow_runs_top_to_bottom():
    d = _layout(RELEASE_FLOW)
    y = {n.id: n.y for n in d.nodes}
    # commit -> build -> test -> deploy: topo order increases downward
    assert y["commit"] < y["build"] < y["test"] < y["deploy"]


def test_no_node_overlap_vertical():
    d = _layout(RELEASE_FLOW)
    boxes = [(n.x, n.y, n.x + n.width, n.y + n.height) for n in d.nodes]
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            ax0, ay0, ax1, ay1 = boxes[i]
            bx0, by0, bx1, by1 = boxes[j]
            assert not (ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1)


def test_edges_stay_within_canvas():
    d = _layout(RELEASE_FLOW)
    for e in d.edges:
        for px, py in e.points:
            assert 0 <= px <= d.width and 0 <= py <= d.height


# ---- render -----------------------------------------------------------------
def test_vertical_svg_is_wellformed_and_complete():
    svg = render_svg(_layout(RELEASE_FLOW))
    fromstring(svg)  # raises on malformed XML
    assert "Release Flow" in svg  # title bar (still on top)
    for lane in RELEASE_FLOW["lanes"]:
        assert lane["label"]["text"] in svg
    for node in RELEASE_FLOW["nodes"]:
        assert node["label"]["text"] in svg


def test_vertical_render_is_deterministic():
    d = _layout(RELEASE_FLOW)
    assert render_svg(d) == render_svg(d)


# ---- horizontal regression guard -------------------------------------------
def test_horizontal_orientation_unchanged():
    horiz = {**RELEASE_FLOW, "layout": {}}
    d = _layout(horiz)
    assert d.orientation == "horizontal"
    bands = list(d.lanes)
    assert len({round(b.x, 3) for b in bands}) == 1  # rows share a left edge
    for b in bands:
        assert b.width > b.height  # a row, not a column
