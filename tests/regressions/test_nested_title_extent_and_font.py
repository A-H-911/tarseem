"""Regression: nested-lane title bar must reach the swimlane end border, and the group
label must use the embedded font (bug report #2).

Two defects, both in the swimlane writer:
1. Font: ``_collect_chars`` omitted ``lane_groups`` labels, so the group label's glyphs were
   not in the embedded WOFF2 subset and fell back to a system serif.
2. Title extent: the writer derived the canvas margin from ``lanes[0].x``, which a group
   gutter shifts right — so the title was inset by the gutter on both sides and fell short of
   the lane's right border. The top margin is independent of the (gutter-shifted) left inset.
"""
from __future__ import annotations

from defusedxml.ElementTree import fromstring

from tarseem.layout.lanegrid import LaneGridLayout
from tarseem.measure import measure_graph
from tarseem.model import compile_spec
from tarseem.render import render_svg
from tarseem.render.swimlane import _collect_chars

NESTED = {
    "specVersion": "0.1", "diagramType": "swimlane", "direction": "LR",
    "meta": {"title": "Service Delivery"},
    "lanes": [
        {"id": "eng", "label": {"text": "Engineering"}},
        {"id": "fe", "label": {"text": "Frontend"}, "parent": "eng"},
        {"id": "be", "label": {"text": "Backend"}, "parent": "eng"},
        {"id": "qa", "label": {"text": "QA"}},
    ],
    "nodes": [
        {"id": "a", "lane": "fe", "label": {"text": "A"}},
        {"id": "b", "lane": "be", "label": {"text": "B"}},
        {"id": "c", "lane": "qa", "label": {"text": "C"}},
    ],
    "edges": [{"id": "e1", "source": "a", "target": "b"},
              {"id": "e2", "source": "b", "target": "c"}],
}


def _diagram():
    return LaneGridLayout().layout(measure_graph(compile_spec(NESTED)))


def test_group_label_chars_are_in_the_font_subset():
    chars = _collect_chars(_diagram())
    assert set("Engineering") <= chars  # else the glyphs fall back to a system serif


def _title_rect(svg: str):
    """The title bar rect: the diagram's theme title fill (default #269973)."""
    root = fromstring(svg)
    ns = "{http://www.w3.org/2000/svg}"
    for rect in root.iter(f"{ns}rect"):
        if rect.get("fill") == "#269973":
            return float(rect.get("x")), float(rect.get("width"))
    raise AssertionError("title rect not found")


def test_title_extends_to_the_swimlane_end_border():
    d = _diagram()
    svg = render_svg(d)
    tx, tw = _title_rect(svg)
    lane_right = max(b.x + b.width for b in d.lanes)
    left = min([b.x for b in d.lanes] + [g.x for g in d.lane_groups])
    assert tx == left  # title starts at the far-left chrome edge (covers the group gutter)
    assert tx + tw == lane_right  # ... and reaches the lane's right border (the "end border")


def test_title_sits_at_the_true_top_margin():
    d = _diagram()
    # the top margin equals the bottom margin (symmetric canvas), independent of the gutter
    top_margin = d.height - (d.lanes[-1].y + d.lanes[-1].height)
    assert d.lanes[0].x > top_margin  # gutter really did shift the left inset past the margin
    root = fromstring(render_svg(d))
    ns = "{http://www.w3.org/2000/svg}"
    title = next(r for r in root.iter(f"{ns}rect") if r.get("fill") == "#269973")
    assert float(title.get("y")) == top_margin  # not the (larger) gutter-shifted left inset
