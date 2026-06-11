"""RenderReport metrics (Phase 3): crossing/overlap/timing quality signals.

These are pure geometry over the positioned IR — they feed the gallery detail pages and
give the regression suite a numeric, deterministic quality signal per golden (09 §1
regression/perf row). Timing is injected by the engine; geometry is computed here.
"""
from __future__ import annotations

from tarseem.layout.sequence import SequenceLayout
from tarseem.measure import measure_graph
from tarseem.model import Label, PositionedDiagram, PositionedEdge, PositionedNode, compile_spec
from tarseem.report import RenderReport, analyze
from test_a10_sequence import LOGIN  # sibling test module (tests/ on sys.path)


def _node(nid: str, x: float, y: float, w: float = 40, h: float = 30) -> PositionedNode:
    return PositionedNode(id=nid, x=x, y=y, width=w, height=h, label=Label(text=nid), shape="rect")


def _edge(eid: str, pts) -> PositionedEdge:
    return PositionedEdge(id=eid, points=tuple(pts))


def test_clean_diagram_has_zero_crossings_and_overlaps():
    d = PositionedDiagram(
        width=200, height=100,
        nodes=(_node("a", 0, 0), _node("b", 100, 0)),
        edges=(_edge("e", [(40, 15), (100, 15)]),),
        diagram_type="flowchart",
    )
    r = analyze(d)
    assert isinstance(r, RenderReport)
    assert r.node_count == 2 and r.edge_count == 1
    assert r.crossings == 0 and r.overlaps == 0


def test_counts_a_crossing_pair():
    # two edges forming an X cross exactly once
    d = PositionedDiagram(
        width=100, height=100, nodes=(),
        edges=(_edge("e1", [(0, 0), (100, 100)]), _edge("e2", [(0, 100), (100, 0)])),
        diagram_type="flowchart",
    )
    assert analyze(d).crossings == 1


def test_edges_sharing_an_endpoint_do_not_count_as_a_crossing():
    # both leave the same point -> a fan-out at a node, not a crossing
    d = PositionedDiagram(
        width=100, height=100, nodes=(),
        edges=(_edge("e1", [(50, 50), (100, 0)]), _edge("e2", [(50, 50), (100, 100)])),
        diagram_type="flowchart",
    )
    assert analyze(d).crossings == 0


def test_counts_node_overlap():
    d = PositionedDiagram(
        width=100, height=100,
        nodes=(_node("a", 0, 0, 50, 50), _node("b", 25, 25, 50, 50)),
        edges=(), diagram_type="flowchart",
    )
    assert analyze(d).overlaps == 1


def test_adjacent_nodes_do_not_overlap():
    d = PositionedDiagram(
        width=100, height=100,
        nodes=(_node("a", 0, 0, 50, 50), _node("b", 50, 0, 50, 50)),  # touching, not overlapping
        edges=(), diagram_type="flowchart",
    )
    assert analyze(d).overlaps == 0


def test_timing_is_injected_not_computed():
    d = PositionedDiagram(width=10, height=10, nodes=(), edges=(), diagram_type="flowchart")
    assert analyze(d).render_ms is None
    assert analyze(d, render_ms=12.5).render_ms == 12.5


def test_report_is_deterministic():
    d = SequenceLayout().layout(measure_graph(compile_spec(LOGIN)))
    assert analyze(d) == analyze(d)


def test_report_to_dict_is_json_friendly():
    d = SequenceLayout().layout(measure_graph(compile_spec(LOGIN)))
    out = analyze(d, render_ms=3.0).to_dict()
    assert out["node_count"] == 4 and out["edge_count"] == 7
    assert set(out) >= {"node_count", "edge_count", "crossings", "overlaps", "width", "height",
                        "render_ms"}


def test_engine_render_attaches_timing():
    from tarseem.engine import Engine

    report = Engine().render(LOGIN).report
    assert report.edge_count == 7
    assert report.render_ms is not None and report.render_ms >= 0
