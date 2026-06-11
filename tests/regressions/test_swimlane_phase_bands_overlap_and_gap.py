"""Regression: swimlane phase bands overlapped the title and left gaps between phases.

Reported bug (swimlane-phases): the phase header bands (a) had a gap between adjacent
phases instead of tiling, (b) had no separator at the start of the first phase, and
(c) overlapped the swimlane title because the renderer inferred the title-bar height as
"first lane top - margin", which wrongly included the phase-header band.

Root cause was in two owned layers (not upstream ELK — swimlanes are pure-Python):
- layout `lanegrid._phase_bands` sized bands to member nodes ±pad → gaps;
- render `swimlane.render_swimlane_svg` mis-inferred the title height.

These assertions lock the fix: contiguous bands, a leading separator, an unchanged title
bar height when phases are added, and a horizontal (un-rotated) title.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

from tarseem.layout.lanegrid import LaneGridLayout
from tarseem.measure import measure_graph
from tarseem.model import compile_spec
from tarseem.render import render_svg

SPEC = json.loads(
    (Path(__file__).parent / "swimlane_phases_overlap.json").read_text(encoding="utf-8")
)


def _layout(spec: dict):
    return LaneGridLayout().layout(measure_graph(compile_spec(spec)))


def test_phase_bands_tile_contiguously_with_no_gap():
    d = _layout(SPEC)
    bands = sorted(d.phases, key=lambda p: p.x)
    assert len(bands) == 2
    for prev, nxt in zip(bands, bands[1:], strict=False):
        gap = nxt.x - (prev.x + prev.width)
        assert abs(gap) < 0.5, f"phases must touch, found {gap:.2f}px gap"


def test_phase_band_does_not_overlap_the_title():
    d = _layout(SPEC)
    m = d.lanes[0].x
    title_bottom = d.phases[0].y  # renderer stops the title bar here
    # title bar height must equal what it is WITHOUT phases (phases add a band below the
    # title, they must not be swallowed into the title bar)
    plain = copy.deepcopy(SPEC)
    plain.pop("phases")
    for n in plain["nodes"]:
        n.pop("phase", None)
    plain_title_h = _layout(plain).lanes[0].y - m
    assert (title_bottom - m) == plain_title_h
    # and every phase band sits at/below the title bar bottom
    assert all(p.y >= title_bottom - 0.5 for p in d.phases)


def test_leading_separator_is_drawn_at_the_first_phase_start():
    d = _layout(SPEC)
    first = min(d.phases, key=lambda p: p.x)
    svg = render_svg(d)
    # a dashed vertical separator must start at the left edge of the first phase
    needle = f'x1="{first.x:.0f}"' if first.x == int(first.x) else f'x1="{first.x:g}"'
    assert "stroke-dasharray" in svg
    assert needle in svg, f"no separator at first-phase left edge x={first.x}"


def test_title_text_stays_horizontal():
    d = _layout(SPEC)
    svg = render_svg(d)
    title_line = next(ln for ln in svg.splitlines() if "Phase Layout Regression" in ln)
    assert "rotate" not in title_line and "transform" not in title_line
    assert 'text-anchor="middle"' in title_line
