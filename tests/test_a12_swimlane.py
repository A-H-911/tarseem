"""A12 — swimlane (LTR): reproduce Reference-1 (Bug Triage) + Reference-3 (Pipeline).

Swimlanes use the deterministic lane-grid layouter, NOT ELK (Phase-0 decision: ELK
partitioning groups along the flow axis, not lanes). One step per column = topological
number; lanes are fixed rows. Visual contract: docs/plan/references/analysis.md.

No Node runtime needed — the lane-grid layouter is pure Python.
"""
from __future__ import annotations

import copy

from tarseem.layout.lanegrid import LaneGridLayout
from tarseem.measure import measure_graph
from tarseem.model import PositionedDiagram, compile_spec
from tarseem.render import render_svg

# Reference-1: Bug Triage (LTR, 4 lanes; back-edge + long cross-lane edges + labels)
BUG_TRIAGE = {
    "specVersion": "0.1",
    "diagramType": "swimlane",
    "direction": "LR",
    "meta": {"title": "Bug Triage"},
    "lanes": [
        {"id": "rep", "label": {"text": "Reporter"}},
        {"id": "tri", "label": {"text": "Triage Engineer"}},
        {"id": "dev", "label": {"text": "Developer"}},
        {"id": "qa", "label": {"text": "QA"}},
    ],
    "nodes": [
        {"id": "report", "lane": "rep", "shape": "stadium", "badge": False,
         "label": {"text": "Bug report"}},
        {"id": "classify", "lane": "tri", "shape": "roundrect", "label": {"text": "Classify"}},
        {"id": "realbug", "lane": "tri", "shape": "diamond", "label": {"text": "Real bug?"}},
        {"id": "fix", "lane": "dev", "shape": "roundrect", "label": {"text": "Fix"}},
        {"id": "verify", "lane": "qa", "shape": "diamond", "label": {"text": "Verify"}},
        {"id": "close", "lane": "tri", "shape": "stadium", "badge": False,
         "label": {"text": "Close"}},
    ],
    "edges": [
        {"id": "e1", "source": "report", "target": "classify"},
        {"id": "e2", "source": "classify", "target": "realbug"},
        {"id": "e3", "source": "realbug", "target": "close", "label": {"text": "no"}},
        {"id": "e4", "source": "realbug", "target": "fix", "label": {"text": "yes"}},
        {"id": "e5", "source": "fix", "target": "verify"},
        {"id": "e6", "source": "verify", "target": "fix", "label": {"text": "fails"}},
        {"id": "e7", "source": "verify", "target": "close", "label": {"text": "passes"}},
    ],
}

# Reference-3: Pipeline (LTR, 3 lanes; full shape set + UML markers + dashed + back-edge)
PIPELINE = {
    "specVersion": "0.1",
    "diagramType": "swimlane",
    "direction": "LR",
    "meta": {"title": "Pipeline"},
    "layout": {"markers": True},
    "lanes": [
        {"id": "user", "label": {"text": "User"}},
        {"id": "sys", "label": {"text": "System"}},
        {"id": "stor", "label": {"text": "Storage"}},
    ],
    "nodes": [
        {"id": "upload", "lane": "user", "shape": "parallelogram", "label": {"text": "Upload"}},
        {"id": "validate", "lane": "sys", "shape": "diamond", "label": {"text": "Validate?"}},
        {"id": "process", "lane": "sys", "shape": "roundrect", "label": {"text": "Process"}},
        {"id": "save", "lane": "stor", "shape": "cylinder", "label": {"text": "Save"}},
        {"id": "receipt", "lane": "user", "shape": "document", "label": {"text": "Receipt"}},
    ],
    "edges": [
        {"id": "e1", "source": "upload", "target": "validate"},
        {"id": "e2", "source": "validate", "target": "process", "label": {"text": "ok"}},
        {"id": "e3", "source": "validate", "target": "upload", "label": {"text": "bad"}},
        {"id": "e4", "source": "process", "target": "save", "label": {"text": "async"},
         "dashed": True},
        {"id": "e5", "source": "save", "target": "receipt"},
    ],
}


# ---- compile ----------------------------------------------------------------
def test_compile_carries_lanes_and_title():
    g = compile_spec(BUG_TRIAGE)
    assert g.diagram_type == "swimlane"
    assert g.title == "Bug Triage"
    assert [lane.label.text for lane in g.lanes] == [
        "Reporter", "Triage Engineer", "Developer", "QA"
    ]


def test_compile_reads_markers_hint():
    assert compile_spec(PIPELINE).markers is True
    assert compile_spec(BUG_TRIAGE).markers is False


def test_compile_is_pure():
    before = copy.deepcopy(BUG_TRIAGE)
    compile_spec(BUG_TRIAGE)
    assert BUG_TRIAGE == before


# ---- lane-grid layout -------------------------------------------------------
def test_layout_places_nodes_in_their_lane_rows():
    g = measure_graph(compile_spec(BUG_TRIAGE))
    d = LaneGridLayout().layout(g)
    assert isinstance(d, PositionedDiagram)
    assert d.title == "Bug Triage"
    assert len(d.lanes) == 4

    band_by_id = {b.id: b for b in d.lanes}
    node_by_id = {n.id: n for n in d.nodes}
    lane_of = {n["id"]: n["lane"] for n in BUG_TRIAGE["nodes"]}
    # every node sits vertically inside the band of its lane
    for nid, node in node_by_id.items():
        band = band_by_id[lane_of[nid]]
        assert band.y <= node.y and node.y + node.height <= band.y + band.height


def test_layout_columns_follow_topological_order():
    g = measure_graph(compile_spec(BUG_TRIAGE))
    d = LaneGridLayout().layout(g)
    x = {n.id: n.x for n in d.nodes}
    # report -> classify -> realbug -> {fix, close}; columns strictly increase along flow
    assert x["report"] < x["classify"] < x["realbug"] < x["fix"]


def test_layout_numbers_badges_and_exempts_terminals():
    g = measure_graph(compile_spec(BUG_TRIAGE))
    d = LaneGridLayout().layout(g)
    badge = {n.id: n.badge for n in d.nodes}
    assert badge["report"] is None  # stadium start: badge-exempt
    assert badge["close"] is None  # stadium terminal: badge-exempt
    assert badge["classify"] == "2."  # numbered by column (report is col 1)


def test_layout_no_node_overlap():
    g = measure_graph(compile_spec(PIPELINE))
    d = LaneGridLayout().layout(g)
    boxes = [(n.x, n.y, n.x + n.width, n.y + n.height) for n in d.nodes]
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            ax0, ay0, ax1, ay1 = boxes[i]
            bx0, by0, bx1, by1 = boxes[j]
            assert not (ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1)


def test_pipeline_emits_uml_markers():
    g = measure_graph(compile_spec(PIPELINE))
    d = LaneGridLayout().layout(g)
    kinds = {m.kind for m in d.markers}
    assert kinds == {"start", "end"}


def test_bug_triage_has_no_markers():
    g = measure_graph(compile_spec(BUG_TRIAGE))
    d = LaneGridLayout().layout(g)
    assert d.markers == ()


# ---- swimlane render --------------------------------------------------------
def test_render_swimlane_svg_includes_chrome_and_labels():
    g = measure_graph(compile_spec(BUG_TRIAGE))
    svg = render_svg(LaneGridLayout().layout(g))
    assert svg.lstrip().startswith("<svg")
    assert svg.rstrip().endswith("</svg>")
    assert "Bug Triage" in svg  # title bar
    for lane in BUG_TRIAGE["lanes"]:
        assert lane["label"]["text"] in svg  # header pills
    for node in BUG_TRIAGE["nodes"]:
        assert node["label"]["text"] in svg
    for edge in BUG_TRIAGE["edges"]:
        if "label" in edge:
            assert edge["label"]["text"] in svg


def test_render_is_deterministic():
    g = measure_graph(compile_spec(PIPELINE))
    d = LaneGridLayout().layout(g)
    assert render_svg(d) == render_svg(d)


def test_dashed_edge_renders_dashed():
    g = measure_graph(compile_spec(PIPELINE))
    svg = render_svg(LaneGridLayout().layout(g))
    assert "stroke-dasharray" in svg


def test_badge_renders_as_corner_circle():
    # Badge is now a circle centred on the node's top corner (note #5): right for the default
    # LTR side, left when forced — with the number (dot stripped) inside.
    from tarseem.model.ir import Label, PositionedNode
    from tarseem.render.swimlane import _badge_circle

    n = PositionedNode(
        id="x", x=100.0, y=50.0, width=80.0, height=40.0,
        label=Label(text="Step"), shape="roundrect", badge="2.",
    )
    right = "".join(_badge_circle(n, "right", "#333333"))
    assert "<circle" in right and 'cx="180"' in right and 'cy="50"' in right  # top-right
    assert ">2<" in right  # number, dot stripped
    left = "".join(_badge_circle(n, "left", "#333333"))
    assert 'cx="100"' in left  # top-left corner


def test_rendered_svg_is_wellformed_xml():
    """Strict SVG viewers reject duplicate attributes; the output must parse as XML."""
    from defusedxml.ElementTree import fromstring  # safe parser (project invariant)

    for spec in (BUG_TRIAGE, PIPELINE):
        svg = render_svg(LaneGridLayout().layout(measure_graph(compile_spec(spec))))
        fromstring(svg)  # raises ParseError on malformed XML (e.g. duplicate attrs)


def test_edges_attach_to_parallelogram_slanted_edge():
    """Connections must touch the parallelogram body, not its bounding box (no gap)."""
    d = LaneGridLayout().layout(measure_graph(compile_spec(PIPELINE)))
    upload = next(n for n in d.nodes if n.id == "upload")  # parallelogram
    inset = 10.0  # s/2 at vertical center (shape slant s = 20)

    start = next(e for e in d.edges if e.id == "__marker_start__")
    assert abs(start.points[-1][0] - (upload.x + inset)) < 0.6  # left-center attach

    bad = next(e for e in d.edges if e.id == "e3")  # validate -> upload (enters right)
    assert abs(bad.points[-1][0] - (upload.x + upload.width - inset)) < 0.6
