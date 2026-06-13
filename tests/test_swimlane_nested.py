"""Phase 5 sub-stage 4 — nested lanes (best-effort, AM-6).

A lane named as another lane's ``parent`` is a group, not a flow row. Child lanes are the
rows; the parent is drawn as an outer header gutter spanning its children. Implemented as a
single x-translate post-pass over the horizontal layout, so the inner geometry (and its
baselines) is unchanged when no parents are declared. One level only (documented limit).
"""
from __future__ import annotations

from defusedxml.ElementTree import fromstring  # safe parser (project invariant)

from tarseem.layout.lanegrid import _GROUP_W, _M, LaneGridLayout
from tarseem.measure import measure_graph
from tarseem.model import compile_spec
from tarseem.render import render_svg

NESTED = {
    "specVersion": "0.1",
    "diagramType": "swimlane",
    "direction": "LR",
    "meta": {"title": "Service Delivery"},
    "lanes": [
        {"id": "eng", "label": {"text": "Engineering"}},  # group (parent of fe + be)
        {"id": "fe", "label": {"text": "Frontend"}, "parent": "eng"},
        {"id": "be", "label": {"text": "Backend"}, "parent": "eng"},
        {"id": "qa", "label": {"text": "QA"}},  # standalone leaf
    ],
    "nodes": [
        {"id": "design", "lane": "fe", "shape": "roundrect", "label": {"text": "Design"}},
        {"id": "api", "lane": "be", "shape": "roundrect", "label": {"text": "API"}},
        {"id": "test", "lane": "qa", "shape": "diamond", "label": {"text": "Test"}},
    ],
    "edges": [
        {"id": "e1", "source": "design", "target": "api"},
        {"id": "e2", "source": "api", "target": "test"},
    ],
}


def _layout(spec: dict):
    return LaneGridLayout().layout(measure_graph(compile_spec(spec)))


# ---- compile ----------------------------------------------------------------
def test_compile_reads_parent():
    lanes = {lane.id: lane for lane in compile_spec(NESTED).lanes}
    assert lanes["be"].parent == "eng"
    assert lanes["qa"].parent is None


# ---- layout -----------------------------------------------------------------
def test_group_excluded_from_flow_rows():
    d = _layout(NESTED)
    assert {b.id for b in d.lanes} == {"fe", "be", "qa"}  # eng is a group, not a row


def test_group_band_spans_its_children():
    d = _layout(NESTED)
    assert len(d.lane_groups) == 1
    group = d.lane_groups[0]
    assert group.id == "eng"
    kids = [b for b in d.lanes if b.id in ("fe", "be")]
    assert group.y <= min(k.y for k in kids)
    assert group.y + group.height >= max(k.y + k.height for k in kids)
    assert group.x == _M  # outer gutter at the far left


def test_content_shifted_right_of_the_group_gutter():
    d = _layout(NESTED)
    assert all(b.x == _M + _GROUP_W for b in d.lanes)  # lane bands start past the gutter
    assert all(n.x >= _M + _GROUP_W for n in d.nodes)


# ---- render -----------------------------------------------------------------
def test_render_includes_group_and_child_labels():
    svg = render_svg(_layout(NESTED))
    fromstring(svg)  # well-formed XML (no duplicate attrs from the rotated label)
    assert "Engineering" in svg  # group gutter label
    for text in ("Frontend", "Backend", "QA", "Design", "API", "Test"):
        assert text in svg


def test_nested_render_is_deterministic():
    d = _layout(NESTED)
    assert render_svg(d) == render_svg(d)


# ---- regression: flat swimlane is untouched ---------------------------------
def test_flat_swimlane_has_no_groups_and_no_shift():
    flat = {**NESTED, "lanes": [{"id": "qa", "label": {"text": "QA"}}],
            "nodes": [{"id": "test", "lane": "qa", "label": {"text": "Test"}}],
            "edges": []}
    d = _layout(flat)
    assert d.lane_groups == ()
    assert d.lanes[0].x == _M  # no gutter shift
