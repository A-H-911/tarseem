"""Regression: arrowheads did not follow the line direction on angled (non-orthogonal) edges.

`_arrowhead` snapped every head to one of FOUR orthogonal directions (it chose horizontal vs
vertical by `abs(dx) >= abs(dy)`). That is exact for orthogonally-routed edges (every ELK graph
family sets `elk.edgeRouting=ORTHOGONAL`), but mindmap mrtree/radial edges are diagonal, so a
−59° terminal segment was drawn as a straight-up (−90°) arrow — the reported defect on
mindmap-roadmap / mindmap-arabic / mindmap-skills-radial.

Fix: the head points along the true `p1->p2` angle. For an axis-aligned segment it is the same
triangle as before (pixel-identical → zero orthogonal-family baseline churn, verified).
"""
from __future__ import annotations

import math
import re
import shutil

import pytest

from tarseem.render.svg import _arrowhead

requires_node = pytest.mark.skipif(shutil.which("node") is None, reason="ELK layout needs Node")


def _tip_angle(p1, p2) -> float:
    """Direction (degrees) the rendered arrowhead actually points: base-midpoint -> tip."""
    poly = _arrowhead(p1, p2, "#000")
    nums = [float(n) for n in re.findall(r"-?\d+\.?\d*", poly.split('points="')[1].split('"')[0])]
    (tx, ty), (ax, ay), (bx, by) = (nums[0], nums[1]), (nums[2], nums[3]), (nums[4], nums[5])
    return math.degrees(math.atan2(ty - (ay + by) / 2, tx - (ax + bx) / 2))


def _near_axis(angle: float) -> bool:
    m = abs(angle) % 90
    return min(m, 90 - m) < 5.0


@pytest.mark.parametrize(
    "p1,p2,expected",
    [
        ((0, 0), (10, 0), 0.0),       # horizontal — unchanged (axis-aligned)
        ((0, 0), (0, 10), 90.0),      # vertical — unchanged
        ((0, 0), (10, 10), 45.0),     # diagonal
        ((0, 0), (10, 8), 38.66),     # the bug: abs(dx)>abs(dy) was snapped to 0°
        ((0, 0), (-10, -6), -149.0),  # back-left (an RTL mindmap leaf)
    ],
)
def test_arrowhead_points_along_the_segment(p1, p2, expected):
    assert abs(_tip_angle(p1, p2) - expected) < 1.5


def test_degenerate_segment_emits_no_arrowhead():
    assert _arrowhead((5.0, 5.0), (5.0, 5.0), "#000") == ""


@requires_node
def test_mindmap_renders_diagonal_arrowheads():
    # the family that exposed the bug: at least one edge must render a genuinely diagonal head.
    import json
    from pathlib import Path

    from tarseem import Engine

    root = Path(__file__).resolve().parent.parent.parent
    spec = json.loads((root / "examples" / "mindmap-roadmap.json").read_text(encoding="utf-8"))
    d = Engine().render(spec).diagram
    angles = [_tip_angle(e.points[-2], e.points[-1]) for e in d.edges if len(e.points) >= 2]
    assert any(not _near_axis(a) for a in angles), "mindmap must render diagonal arrowheads"
