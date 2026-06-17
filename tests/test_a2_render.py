"""A2 — render flowchart / architecture-C4 / dependency from spec via ELK.

Pipeline under test (one IR, many writers):
    spec -> compile_spec -> LogicalGraph
         -> measure_graph (uharfbuzz advances BEFORE layout)   [invariant: measure-first]
         -> ElkLayout.layout -> PositionedDiagram               [invariant: ELK JSON in-adapter]
         -> render_svg -> SVG string

ELK layout needs the Node runtime; those tests skip (never silently pass) when node
is absent, surfacing the dependency as a capability, not a false green.
"""
from __future__ import annotations

import shutil

import pytest

from tarseem.measure import measure_graph
from tarseem.model import PositionedDiagram, compile_spec
from tarseem.render import render_svg

requires_node = pytest.mark.skipif(
    shutil.which("node") is None,
    reason="Node.js runtime not on PATH (ELK layout requires it)",
)

FLOWCHART = {
    "specVersion": "1.0",
    "diagramType": "flowchart",
    "direction": "TB",
    "nodes": [
        {"id": "start", "shape": "stadium", "label": {"text": "Start"}},
        {"id": "work", "shape": "roundrect", "label": {"text": "Do work"}},
        {"id": "check", "shape": "diamond", "label": {"text": "Looks OK?"}},
        {"id": "done", "shape": "stadium", "label": {"text": "Done"}},
    ],
    "edges": [
        {"id": "e1", "source": "start", "target": "work"},
        {"id": "e2", "source": "work", "target": "check"},
        {"id": "e3", "source": "check", "target": "done", "label": {"text": "yes"}},
        {"id": "e4", "source": "check", "target": "work", "label": {"text": "no"}},
    ],
}

ARCHITECTURE = {
    "specVersion": "1.0",
    "diagramType": "architecture",
    "direction": "LR",
    "nodes": [
        {"id": "web", "shape": "rect", "label": {"text": "Web App"}},
        {"id": "api", "shape": "rect", "label": {"text": "API Gateway"}},
        {"id": "svc", "shape": "rect", "label": {"text": "Orders Service"}},
        {"id": "db", "shape": "cylinder", "label": {"text": "Orders DB"}},
    ],
    "edges": [
        {"id": "e1", "source": "web", "target": "api", "label": {"text": "HTTPS"}},
        {"id": "e2", "source": "api", "target": "svc"},
        {"id": "e3", "source": "svc", "target": "db", "label": {"text": "SQL"}},
    ],
}

DEPENDENCY = {
    "specVersion": "1.0",
    "diagramType": "dependency",
    "direction": "LR",
    "nodes": [
        {"id": "app", "label": {"text": "app"}},
        {"id": "core", "label": {"text": "core"}},
        {"id": "utils", "label": {"text": "utils"}},
        {"id": "http", "label": {"text": "http"}},
    ],
    "edges": [
        {"id": "e1", "source": "app", "target": "core"},
        {"id": "e2", "source": "app", "target": "http"},
        {"id": "e3", "source": "core", "target": "utils"},
        {"id": "e4", "source": "http", "target": "utils"},
    ],
}

ALL_FAMILIES = [
    pytest.param(FLOWCHART, id="flowchart"),
    pytest.param(ARCHITECTURE, id="architecture"),
    pytest.param(DEPENDENCY, id="dependency"),
]


# ---- compile (logical IR) ---------------------------------------------------
def test_compile_builds_logical_ir():
    g = compile_spec(FLOWCHART)
    assert g.diagram_type == "flowchart"
    assert g.direction == "TB"
    assert [n.id for n in g.nodes] == ["start", "work", "check", "done"]
    assert g.nodes[0].label.text == "Start"
    assert [e.source for e in g.edges] == ["start", "work", "check", "check"]


def test_compile_resolves_styles_onto_nodes():
    spec = {
        "specVersion": "1.0",
        "diagramType": "flowchart",
        "styles": {"hot": {"fill": "#FDECEC"}},
        "nodes": [{"id": "n", "styleRefs": ["hot"], "label": {"text": "x"}}],
    }
    g = compile_spec(spec)
    assert g.nodes[0].style["fill"] == "#FDECEC"


def test_compile_is_pure():
    import copy

    before = copy.deepcopy(FLOWCHART)
    compile_spec(FLOWCHART)
    assert FLOWCHART == before


# ---- measurement (before layout) --------------------------------------------
def test_measure_sets_positive_node_sizes():
    g = measure_graph(compile_spec(FLOWCHART))
    assert all(n.width and n.width > 0 for n in g.nodes)
    assert all(n.height and n.height > 0 for n in g.nodes)


def test_measure_widens_longer_labels():
    # A label long enough to exceed the minimum-width floor must measure wider than
    # a short one — proving box size tracks shaped advance, not a constant.
    spec = {
        "specVersion": "1.0",
        "diagramType": "flowchart",
        "nodes": [
            {"id": "short", "label": {"text": "Hi"}},
            {"id": "long", "label": {"text": "A considerably longer node label"}},
        ],
    }
    by_id = {n.id: n for n in measure_graph(compile_spec(spec)).nodes}
    assert by_id["long"].width > by_id["short"].width


def test_measure_returns_new_graph_not_mutating():
    g0 = compile_spec(FLOWCHART)
    g1 = measure_graph(g0)
    assert g0.nodes[0].width is None  # original untouched
    assert g1.nodes[0].width is not None


# ---- layout (ELK) + render --------------------------------------------------
@requires_node
@pytest.mark.parametrize("spec", ALL_FAMILIES)
def test_family_lays_out_and_renders(spec):
    from tarseem.layout.elk import ElkLayout

    g = measure_graph(compile_spec(spec))
    with ElkLayout() as elk:
        diagram = elk.layout(g)

    assert isinstance(diagram, PositionedDiagram)
    assert diagram.width > 0 and diagram.height > 0
    assert len(diagram.nodes) == len(spec["nodes"])
    # every node placed inside the canvas with the size we measured
    for n in diagram.nodes:
        assert n.width > 0 and n.height > 0
        assert 0 <= n.x <= diagram.width
        assert 0 <= n.y <= diagram.height
    # edges carry a routed polyline (>= 2 points)
    assert all(len(e.points) >= 2 for e in diagram.edges)

    svg = render_svg(diagram)
    assert svg.lstrip().startswith("<svg")
    assert svg.rstrip().endswith("</svg>")
    for node in spec["nodes"]:
        assert node["label"]["text"] in svg


@requires_node
def test_layout_separates_nodes_no_overlap():
    from tarseem.layout.elk import ElkLayout

    g = measure_graph(compile_spec(FLOWCHART))
    with ElkLayout() as elk:
        diagram = elk.layout(g)

    boxes = [(n.x, n.y, n.x + n.width, n.y + n.height) for n in diagram.nodes]
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            ax0, ay0, ax1, ay1 = boxes[i]
            bx0, by0, bx1, by1 = boxes[j]
            overlap = ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1
            assert not overlap, f"nodes {i} and {j} overlap"


@requires_node
def test_positioned_diagram_exposes_no_elk_json():
    """ELK's wire format must not leak past the layout adapter (invariant)."""
    from tarseem.layout.elk import ElkLayout

    g = measure_graph(compile_spec(FLOWCHART))
    with ElkLayout() as elk:
        diagram = elk.layout(g)
    # PositionedDiagram is a typed dataclass; ELK keys like 'children'/'sections'
    # never appear on it.
    assert not hasattr(diagram, "children")
    node = diagram.nodes[0]
    assert hasattr(node, "x") and hasattr(node, "shape")
    assert not hasattr(node, "layoutOptions")


@requires_node
def test_layout_capability_report_declares_support():
    from tarseem.layout.elk import ElkLayout

    with ElkLayout() as elk:
        caps = elk.capabilities()
    assert caps["engine"] == "elk"
    assert "layered" in caps["algorithms"]
    assert caps["elkjs_version"] == "0.11.1"
