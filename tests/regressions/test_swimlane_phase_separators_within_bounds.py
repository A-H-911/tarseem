"""Regression: phase dashed separators escaped the swimlane borders.

Reported bug (swimlane-phases): the vertical dashed phase separators (a) poked past the
swimlane sides — the leading one started left of the actor/label separator and the closing
one ran past the lane's right border — and (b) extended above the lanes' top border (they
ran from the phase-header band top, not the lane top), so they exceeded the top/bottom
swimlane borders.

Root cause was two owned layers (not upstream ELK):
- layout (lanegrid._phase_bands): outer band edges used ``col_x ± _COL_GAP/2`` which
  overshot the content area by ``_COL_GAP/2 - _SIDE_PAD`` (4px) on each side;
- render (swimlane): separators spanned ``[phase-band top, lanes_bottom]`` instead of the
  lane band ``[lanes_top, lanes_bottom]``.

These assertions lock both: every phase separator stays within the side borders and within
the lane top/bottom.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from tarseem.layout.lanegrid import _LABEL_W, _M, LaneGridLayout
from tarseem.measure import measure_graph
from tarseem.model import compile_spec
from tarseem.render import render_svg

SPEC = json.loads(
    (Path(__file__).parent / "swimlane_phases_overlap.json").read_text(encoding="utf-8")
)
_DASHED = re.compile(
    r'<line x1="([\d.]+)" y1="([\d.]+)" x2="[\d.]+" y2="([\d.]+)"[^>]*stroke-dasharray="3 4"'
)


def _layout():
    return LaneGridLayout().layout(measure_graph(compile_spec(SPEC)))


def _phase_separators(d):
    return [tuple(map(float, m.groups())) for m in _DASHED.finditer(render_svg(d))]


def test_phase_separators_stay_within_the_side_borders():
    d = _layout()
    left = _M + _LABEL_W  # actor/label separator
    right = d.width - _M  # lane band right border
    seps = _phase_separators(d)
    assert seps  # phases produce separators
    for x, _y1, _y2 in seps:
        assert left - 0.5 <= x <= right + 0.5, f"separator x={x} outside [{left}, {right}]"


def test_phase_separators_do_not_exceed_lane_top_or_bottom():
    d = _layout()
    lanes_top = d.lanes[0].y
    lanes_bottom = d.lanes[-1].y + d.lanes[-1].height
    for x, y1, y2 in _phase_separators(d):
        assert y1 >= lanes_top - 0.5, f"separator x={x} starts above lane top ({y1} < {lanes_top})"
        assert y2 <= lanes_bottom + 0.5, f"separator x={x} runs below lane bottom"


def test_leading_and_closing_separators_sit_on_the_borders():
    d = _layout()
    xs = sorted({round(x, 1) for x, _, _ in _phase_separators(d)})
    assert xs[0] == _M + _LABEL_W  # leading separator on the actor separator
    assert xs[-1] == d.width - _M  # closing separator on the right border
