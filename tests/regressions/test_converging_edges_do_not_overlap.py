"""Regression: cross-lane edges converging on one node side must not share a corridor
(bug report #5).

Every edge entering a node from the same side rode that node's centre row, so two of them
overlapped on the shared horizontal segment. Converging edges are now spread to distinct
entry heights around the node centre.
"""
from __future__ import annotations

from tarseem.layout.lanegrid import LaneGridLayout
from tarseem.measure import measure_graph
from tarseem.model import compile_spec

# s1 and s2 are both in the lower lane and both point UP at t in the top lane; they sit at
# earlier columns than t, so both enter t from its LEFT side -> a convergence group of two.
SPEC = {
    "specVersion": "1.0", "diagramType": "swimlane", "direction": "LR",
    "meta": {"title": "Converge"},
    "lanes": [{"id": "top", "label": {"text": "Top"}}, {"id": "bot", "label": {"text": "Bot"}}],
    "nodes": [
        {"id": "s1", "lane": "bot", "label": {"text": "S1"}},
        {"id": "s2", "lane": "bot", "label": {"text": "S2"}},
        {"id": "t", "lane": "top", "label": {"text": "T"}},
    ],
    "edges": [
        {"id": "e0", "source": "s1", "target": "s2"},   # order the columns
        {"id": "c1", "source": "s1", "target": "t"},    # converge on t (left)
        {"id": "c2", "source": "s2", "target": "t"},    # converge on t (left)
    ],
}


def _layout():
    return LaneGridLayout().layout(measure_graph(compile_spec(SPEC)))


def test_converging_edges_enter_at_distinct_heights():
    d = _layout()
    c1 = next(e for e in d.edges if e.id == "c1")
    c2 = next(e for e in d.edges if e.id == "c2")
    # the entry point (last polyline point) into t must differ in y -> no shared corridor
    assert c1.points[-1][1] != c2.points[-1][1]
    # and both still land on t's left side (same x), i.e. they only differ vertically
    assert c1.points[-1][0] == c2.points[-1][0]


def test_entries_straddle_the_node_centre():
    d = _layout()
    t = next(n for n in d.nodes if n.id == "t")
    cy = t.y + t.height / 2
    ys = sorted(e.points[-1][1] for e in d.edges if e.id in ("c1", "c2"))
    assert ys[0] < cy < ys[1]  # one above centre, one below
    assert all(t.y <= y <= t.y + t.height for y in ys)  # both on the node's side
