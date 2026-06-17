"""Regression: a back-edge detour must use the nearest clear corridor, not always dive to
the global bottom of the diagram (bug report #6).

The lane-grid router only tried the global bottom/top channels, so a back-edge between two
mid-lane nodes plunged below an unrelated bottom-lane node even though the channel just below
its own endpoints was clear. It now tries the near channels first.
"""
from __future__ import annotations

from tarseem.layout.lanegrid import LaneGridLayout
from tarseem.measure import measure_graph
from tarseem.model import compile_spec

# a(L0) -> b(L1) -> c(L1) -> d(L2) -> e(L3). Back-edge d->b must detour around the
# intervening c (same lane as b). e sits in the bottom lane, far to the right, so the GLOBAL
# bottom corridor is well below d -- the detour must not dive down to it.
SPEC = {
    "specVersion": "1.0", "diagramType": "swimlane", "direction": "LR",
    "meta": {"title": "Detour"},
    "lanes": [{"id": "l0", "label": {"text": "L0"}}, {"id": "l1", "label": {"text": "L1"}},
              {"id": "l2", "label": {"text": "L2"}}, {"id": "l3", "label": {"text": "L3"}}],
    "nodes": [
        {"id": "a", "lane": "l0", "label": {"text": "A"}},
        {"id": "b", "lane": "l1", "label": {"text": "B"}},
        {"id": "c", "lane": "l1", "label": {"text": "C"}},
        {"id": "d", "lane": "l2", "label": {"text": "D"}},
        {"id": "e", "lane": "l3", "label": {"text": "E"}},
    ],
    "edges": [
        {"id": "e1", "source": "a", "target": "b"},
        {"id": "e2", "source": "b", "target": "c"},
        {"id": "e3", "source": "c", "target": "d"},
        {"id": "e4", "source": "d", "target": "e"},
        {"id": "back", "source": "d", "target": "b"},  # the back-edge under test
    ],
}


def test_backedge_corridor_stays_above_the_bottom_lane_node():
    d = LaneGridLayout().layout(measure_graph(compile_spec(SPEC)))
    nodes = {n.id: n for n in d.nodes}
    back = next(e for e in d.edges if e.id == "back")
    # the detour's horizontal corridor is the y shared by its interior bend points
    ys = [p[1] for p in back.points]
    corridor_y = max(ys)  # the lowest point of the route
    e_top = nodes["e"].y
    # the back-edge must not dip into / below the bottom-lane node 'e'
    assert corridor_y < e_top, f"back-edge dived to y={corridor_y}, below e at {e_top}"
    # and it should sit just under the lower endpoint (d), not far away
    assert corridor_y <= nodes["d"].y + nodes["d"].height + 30


def test_forward_edges_are_unaffected():
    d = LaneGridLayout().layout(measure_graph(compile_spec(SPEC)))
    # a straightforward adjacent forward edge still routes directly (no detour bends)
    e1 = next(e for e in d.edges if e.id == "e1")
    assert len(e1.points) <= 3  # L-shaped at most, no corridor detour
