"""Phase-grouping columns (FR-6.3): vertical phase header bands over swimlane columns.

Phases group flow columns under a header band that spans the width of their member
nodes, drawn above the lanes with a separator dropping through them. They reuse the
lane-grid layouter; lanes shift down to make room. Geometry-only, deterministic.
"""
from __future__ import annotations

import copy

from defusedxml.ElementTree import fromstring

from tarseem.layout.lanegrid import LaneGridLayout
from tarseem.measure import measure_graph
from tarseem.model import PositionedDiagram, compile_spec
from tarseem.render import render_svg

PHASED = {
    "specVersion": "0.1",
    "diagramType": "swimlane",
    "direction": "LR",
    "meta": {"title": "Order Flow"},
    "phases": [
        {"id": "intake", "label": {"text": "Intake"}},
        {"id": "fulfil", "label": {"text": "Fulfilment"}},
    ],
    "lanes": [
        {"id": "cust", "label": {"text": "Customer"}},
        {"id": "ops", "label": {"text": "Operations"}},
    ],
    "nodes": [
        {"id": "order", "lane": "cust", "phase": "intake", "shape": "stadium", "badge": False,
         "label": {"text": "Place order"}},
        {"id": "check", "lane": "ops", "phase": "intake", "shape": "roundrect",
         "label": {"text": "Validate"}},
        {"id": "pick", "lane": "ops", "phase": "fulfil", "shape": "roundrect",
         "label": {"text": "Pick"}},
        {"id": "ship", "lane": "ops", "phase": "fulfil", "shape": "roundrect",
         "label": {"text": "Ship"}},
        {"id": "recv", "lane": "cust", "phase": "fulfil", "shape": "stadium", "badge": False,
         "label": {"text": "Receive"}},
    ],
    "edges": [
        {"id": "e1", "source": "order", "target": "check"},
        {"id": "e2", "source": "check", "target": "pick"},
        {"id": "e3", "source": "pick", "target": "ship"},
        {"id": "e4", "source": "ship", "target": "recv"},
    ],
}


def _layout(spec: dict) -> PositionedDiagram:
    return LaneGridLayout().layout(measure_graph(compile_spec(spec)))


def test_compile_carries_phases_and_node_phase():
    g = compile_spec(PHASED)
    assert [p.id for p in g.phases] == ["intake", "fulfil"]
    assert {n.id: n.phase for n in g.nodes}["pick"] == "fulfil"


def test_compile_is_pure():
    before = copy.deepcopy(PHASED)
    compile_spec(PHASED)
    assert PHASED == before


def test_layout_emits_one_band_per_phase_above_the_lanes():
    d = _layout(PHASED)
    assert len(d.phases) == 2
    lanes_top = min(b.y for b in d.lanes)
    for ph in d.phases:
        assert ph.y < lanes_top  # header band sits above the lane bands
        assert ph.height > 0 and ph.width > 0


def test_phase_bands_follow_column_order():
    d = _layout(PHASED)
    by_id = {p.id: p for p in d.phases}
    assert by_id["intake"].x < by_id["fulfil"].x  # intake columns are left of fulfilment


def test_phase_band_spans_its_member_columns():
    d = _layout(PHASED)
    nodes = {n.id: n for n in d.nodes}
    intake = next(p for p in d.phases if p.id == "intake")
    for nid in ("order", "check"):
        n = nodes[nid]
        assert intake.x <= n.x and n.x + n.width <= intake.x + intake.width


def test_no_phases_means_no_bands_and_no_extra_height():
    plain = {**PHASED}
    plain.pop("phases")
    plain = copy.deepcopy(plain)
    for n in plain["nodes"]:
        n.pop("phase", None)
    d = _layout(plain)
    assert d.phases == ()
    # lanes start higher without the phase header reserving vertical space
    assert min(b.y for b in d.lanes) < min(b.y for b in _layout(PHASED).lanes)


def test_render_includes_phase_labels_and_is_wellformed():
    svg = render_svg(_layout(PHASED))
    assert "Intake" in svg and "Fulfilment" in svg
    fromstring(svg)


def test_layout_is_deterministic():
    d1, d2 = _layout(PHASED), _layout(PHASED)
    assert [(p.id, p.x, p.y, p.width) for p in d1.phases] == \
           [(p.id, p.x, p.y, p.width) for p in d2.phases]
    assert render_svg(d1) == render_svg(d2)
