"""Regression: edges to/from a diamond left a visible gap.

Reported bug (arabic-flowchart.png): the links from the decision diamond to the two
left-hand nodes were not connected — a gap between the diamond and the edge ends.

Root cause was the render/adapter layer (ELK). ELK lays nodes out as rectangles and
attaches edges to the bounding box; the two outgoing edges fan out and meet the bbox side
at y-offsets above/below the diamond's left/right vertices, i.e. *outside* the inscribed
rhombus — so the edge started in empty space. Fixed by snapping the terminal edge points
onto the actual diamond (and parallelogram) outline in the adapter, mirroring the
``_side_x`` treatment the lane-grid router already applies. (Not an upstream ELK limitation
— ELK treats nodes as boxes by design; snapping to a non-rectangular outline is the
consumer's responsibility.)

This locks every diamond-attached endpoint onto the rhombus outline (|dx/hw|+|dy/hh| ≈ 1).
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from tarseem.engine import Engine

HERE = Path(__file__).resolve().parent

requires_node = pytest.mark.skipif(
    shutil.which("node") is None, reason="Node.js runtime not on PATH (ELK graph families)"
)


@requires_node
def test_diamond_attached_edge_endpoints_lie_on_the_rhombus():
    spec = json.loads((HERE / "diamond_edge_gap.json").read_text(encoding="utf-8"))
    d = Engine().render(spec).diagram
    ch = {n.id: n for n in d.nodes}["check"]
    cx, cy = ch.x + ch.width / 2, ch.y + ch.height / 2
    hw, hh = ch.width / 2, ch.height / 2

    def outline_metric(px: float, py: float) -> float:
        return abs((px - cx) / hw) + abs((py - cy) / hh)  # == 1 exactly on the rhombus

    touching = 0
    for e in d.edges:
        for p in (e.points[0], e.points[-1]):
            m = outline_metric(*p)
            if m < 1.2:  # this endpoint attaches to the diamond
                touching += 1
                assert abs(m - 1.0) < 1e-3, (
                    f"endpoint {tuple(round(c, 1) for c in p)} is off the diamond outline "
                    f"(metric={m:.3f}); the bbox-vs-rhombus gap regressed"
                )
    assert touching >= 3  # start->check + check->yes + check->no
