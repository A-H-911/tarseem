"""Regression: sequence messages must touch an activation bar's border, not pierce it
(bug report #4).

Messages were routed between lifeline centres. When a participant is activated, its bar is
centred on the lifeline, so an arrow drawn to the centre lands *inside* the bar. Endpoints
now attach to the bar edge on the side facing the other participant.
"""
from __future__ import annotations

from tarseem.layout.sequence import _ACT_W, SequenceLayout
from tarseem.measure import measure_graph
from tarseem.model import compile_spec

# a -> b opens b's activation; b -> b is a self-call while active; b -> a returns (closes it).
SPEC = {
    "specVersion": "0.1", "diagramType": "sequence", "meta": {"title": "Act"},
    "nodes": [{"id": "a", "label": {"text": "A"}}, {"id": "b", "label": {"text": "B"}}],
    "edges": [
        {"id": "m1", "source": "a", "target": "b", "label": {"text": "call"}},
        {"id": "m2", "source": "b", "target": "b", "label": {"text": "work"}},
        {"id": "m3", "source": "b", "target": "a", "label": {"text": "ret"}, "dashed": True},
    ],
}


def _layout():
    return SequenceLayout().layout(measure_graph(compile_spec(SPEC)))


def test_call_arrow_stops_at_the_target_bar_border():
    d = _layout()
    bar = next(a for a in d.activations)  # b's activation bar
    m1 = next(e for e in d.edges if e.id == "m1")
    # a is left of b, so the call arrives at b's LEFT border (bar.x), not the lifeline centre
    assert m1.points[-1][0] == bar.x
    assert bar.x < bar.x + bar.width  # sanity: the centre (bar.x + w/2) would be inside


def test_return_arrow_leaves_from_the_source_bar_border():
    d = _layout()
    bar = next(a for a in d.activations)
    m3 = next(e for e in d.edges if e.id == "m3")
    # b -> a goes left, so it leaves b's LEFT border
    assert m3.points[0][0] == bar.x


def test_self_message_brackets_off_the_bar_edge():
    d = _layout()
    bar = next(a for a in d.activations)
    m2 = next(e for e in d.edges if e.id == "m2")
    # the self-bracket starts on b's RIGHT border (centre + half-width), not the centre
    assert m2.points[0][0] == bar.x + _ACT_W


def test_inactive_endpoints_still_attach_to_the_lifeline_centre():
    # a is never activated; the call's tail leaves a's lifeline centre unchanged
    d = _layout()
    m1 = next(e for e in d.edges if e.id == "m1")
    head_a = next(n for n in d.nodes if n.id == "a")
    assert m1.points[0][0] == head_a.x + head_a.width / 2
