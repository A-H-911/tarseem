"""Regression: swimlane side padding was asymmetric and inter-shape spacing was narrow.

Reported bug (all swimlanes): the gap between the actor/label separator and the first
shape was much smaller than the gap between the last shape and the lane's right border,
and the value drifted per diagram. Also the horizontal gap between shapes was a touch
narrow.

Root cause was the layout layer (lanegrid): the left content margin used a small
``_LABEL_GAP`` while the right used a large ``_TRAIL`` (+ marker reservation), so the two
sides differed by a fixed ~52px on every diagram. Fixed by collapsing both to one
symmetric ``_SIDE_PAD`` and widening ``_COL_GAP``. (Not an upstream limitation — the
lane-grid layouter is pure Python.)

These assertions lock symmetry, a fixed side value across diagrams, and the wider step gap.
"""
from __future__ import annotations

import json
from pathlib import Path

from tarseem.layout.lanegrid import _COL_GAP, _LABEL_W, _M, _SIDE_PAD, LaneGridLayout
from tarseem.measure import measure_graph
from tarseem.model import compile_spec

ROOT = Path(__file__).resolve().parent.parent.parent
HERE = Path(__file__).parent

# no-marker swimlanes: side padding must be exactly _SIDE_PAD on both sides
NO_MARKER = [
    HERE / "swimlane_side_padding.json",
    ROOT / "examples" / "swimlane-bug-triage.json",
    ROOT / "examples" / "swimlane-phases.json",
]
# marker swimlane: still symmetric, just larger (padding + marker lane)
WITH_MARKER = ROOT / "examples" / "swimlane-pipeline.json"


def _layout(path: Path):
    spec = json.loads(path.read_text(encoding="utf-8"))
    return LaneGridLayout().layout(measure_graph(compile_spec(spec)))


def _side_gaps(d):
    actor_sep = _M + _LABEL_W  # left reference: actor/label separator
    right_border = d.width - _M  # right reference: lane band border
    nodes = sorted(d.nodes, key=lambda n: n.x)
    left = nodes[0].x - actor_sep
    right = right_border - (nodes[-1].x + nodes[-1].width)
    return left, right


def _inter_shape_gaps(d):
    by_x: dict[float, object] = {}
    for n in d.nodes:
        by_x.setdefault(n.x, n)
    xs = sorted(by_x)
    return [round(xs[i + 1] - (by_x[xs[i]].x + by_x[xs[i]].width), 1) for i in range(len(xs) - 1)]


def test_side_padding_is_symmetric_on_every_swimlane():
    for path in [*NO_MARKER, WITH_MARKER]:
        left, right = _side_gaps(_layout(path))
        assert abs(left - right) < 0.5, f"{path.name}: left={left:.1f} != right={right:.1f}"


def test_side_padding_is_a_fixed_small_value_across_diagrams():
    for path in NO_MARKER:
        left, right = _side_gaps(_layout(path))
        assert left == _SIDE_PAD and right == _SIDE_PAD, f"{path.name}: {left}/{right}"


def test_inter_shape_gap_is_widened():
    gaps = _inter_shape_gaps(_layout(HERE / "swimlane_side_padding.json"))
    assert set(gaps) == {_COL_GAP}
    assert _COL_GAP > 40  # wider than the previous narrow default
