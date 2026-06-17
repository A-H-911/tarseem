"""Swimlane layout spec options: sidePadding, columnGap, phaseSeparator.

These expose the previously-hardcoded swimlane geometry as per-diagram `layout` hints so
callers can tune spacing and the phase-separator look without a code change. Defaults equal
the built-in constants, so specs that omit them are unchanged (deterministic).
"""
from __future__ import annotations

import re

from tarseem.layout.lanegrid import _LABEL_W, _M, _SIDE_PAD, LaneGridLayout
from tarseem.measure import measure_graph
from tarseem.model import compile_spec
from tarseem.render import render_svg
from tarseem.validation import validate

BASE = {
    "specVersion": "1.0",
    "diagramType": "swimlane",
    "direction": "LR",
    "meta": {"title": "Opts"},
    "phases": [
        {"id": "p1", "label": {"text": "One"}},
        {"id": "p2", "label": {"text": "Two"}},
    ],
    "lanes": [{"id": "a", "label": {"text": "A"}}],
    "nodes": [
        {"id": "n1", "lane": "a", "phase": "p1", "label": {"text": "N1"}},
        {"id": "n2", "lane": "a", "phase": "p2", "label": {"text": "N2"}},
    ],
    "edges": [{"id": "e1", "source": "n1", "target": "n2"}],
}


def _spec(**layout):
    return {**BASE, "layout": layout} if layout else BASE


def _layout(spec):
    return LaneGridLayout().layout(measure_graph(compile_spec(spec)))


def _side_gaps(d):
    left = d.nodes[0].x - (_M + _LABEL_W)
    right = (d.width - _M) - (sorted(d.nodes, key=lambda n: n.x)[-1].x
                             + sorted(d.nodes, key=lambda n: n.x)[-1].width)
    return left, right


# ---- defaults unchanged -----------------------------------------------------
def test_defaults_match_builtin_constants():
    d = _layout(_spec())
    left, right = _side_gaps(d)
    assert left == _SIDE_PAD and right == _SIDE_PAD


# ---- sidePadding ------------------------------------------------------------
def test_side_padding_option_changes_both_margins_symmetrically():
    d = _layout(_spec(sidePadding=60))
    left, right = _side_gaps(d)
    assert left == 60 and right == 60


# ---- columnGap --------------------------------------------------------------
def test_column_gap_option_widens_inter_shape_spacing():
    d = _layout(_spec(columnGap=120))
    xs = sorted({n.x for n in d.nodes})
    by_x = {}
    for n in d.nodes:
        by_x.setdefault(n.x, n)
    gap = xs[1] - (by_x[xs[0]].x + by_x[xs[0]].width)
    assert gap == 120


# ---- phaseSeparator ---------------------------------------------------------
def test_phase_separator_defaults_to_dashed():
    svg = render_svg(_layout(_spec()))
    assert 'stroke-dasharray="3 4"' in svg


def test_phase_separator_style_solid_drops_the_dashes():
    svg = render_svg(_layout(_spec(phaseSeparator={"style": "solid"})))
    # the phase separators must not be dashed; lane separator is solid regardless
    assert "Two" in svg  # phases rendered
    seps = re.findall(r'<line[^>]*stroke-dasharray="3 4"[^>]*/>', svg)
    assert seps == []


def test_phase_separator_color_and_width_apply():
    svg = render_svg(_layout(_spec(phaseSeparator={"color": "#FF0000", "width": 3})))
    assert re.search(r'<line[^>]*stroke="#FF0000"[^>]*stroke-width="3"', svg) or \
           re.search(r'<line[^>]*stroke-width="3"[^>]*stroke="#FF0000"', svg)


# ---- validation -------------------------------------------------------------
def test_layout_options_validate():
    assert validate(_spec(sidePadding=30, columnGap=70)).ok
    assert validate(_spec(phaseSeparator={"style": "solid", "color": "#333", "width": 2})).ok


def test_bad_layout_option_is_rejected_with_a_coded_error():
    result = validate(_spec(phaseSeparator={"style": "wavy"}))  # not an allowed enum
    assert not result.ok
    assert any(e.code == "E_SCHEMA" for e in result.errors)
