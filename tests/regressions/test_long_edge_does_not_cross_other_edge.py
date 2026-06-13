"""Regression: a long cross-lane edge must not run its vertical segment across another
edge's horizontal segment (bug report #3).

The lane-grid router routed each edge independently against the NODES, not against other
edges, so a long cross-lane edge's vertical column could cross an unrelated horizontal edge.
Such an edge now flips to the alternate L-orientation (along its own row, then down the target
column) when the default would cross another edge.
"""
from __future__ import annotations

from tarseem.layout.lanegrid import LaneGridLayout, _route_crosses_other
from tarseem.measure import measure_graph
from tarseem.model import compile_spec

# a->b is a same-lane (mid) horizontal edge spanning col1..col3. s sits in the bottom lane at
# col2 -- inside that span -- and points up to t in the top lane. The naive route runs s->t's
# vertical up s's column (col2), crossing a->b. The fix must avoid that.
SPEC = {
    "specVersion": "0.1", "diagramType": "swimlane", "direction": "LR",
    "meta": {"title": "Cross"},
    "lanes": [{"id": "top", "label": {"text": "T"}}, {"id": "mid", "label": {"text": "M"}},
              {"id": "bot", "label": {"text": "B"}}],
    "nodes": [
        {"id": "a", "lane": "mid", "label": {"text": "A"}},
        {"id": "s", "lane": "bot", "label": {"text": "S"}},
        {"id": "b", "lane": "mid", "label": {"text": "B"}},
        {"id": "t", "lane": "top", "label": {"text": "T"}},
    ],
    "edges": [
        {"id": "e1", "source": "a", "target": "s"},
        {"id": "e2", "source": "s", "target": "b"},
        {"id": "e3", "source": "b", "target": "t"},
        {"id": "ab", "source": "a", "target": "b"},   # mid-lane horizontal
        {"id": "st", "source": "s", "target": "t"},   # long cross-lane edge under test
    ],
}


def test_long_edge_does_not_cross_the_horizontal_edge():
    d = LaneGridLayout().layout(measure_graph(compile_spec(SPEC)))
    routes = {e.id: list(e.points) for e in d.edges}
    # st must not cross any other edge's horizontal segment
    assert not _route_crosses_other(routes["st"], "st", routes)


def test_other_edges_unchanged_remain_crossing_free():
    d = LaneGridLayout().layout(measure_graph(compile_spec(SPEC)))
    routes = {e.id: list(e.points) for e in d.edges}
    # the whole routed set is crossing-free (no edge's vertical crosses another's horizontal)
    for eid in routes:
        assert not _route_crosses_other(routes[eid], eid, routes)
