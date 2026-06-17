"""Sequence family: deterministic Python time-order layouter + dedicated renderer (A10).

The drawio/PPTX writers draw lifelines + activation bars for this family, declared via
``export_chrome="sequence"``.
"""
from __future__ import annotations

from tarseem.families.base import DiagramTypePlugin
from tarseem.layout.sequence import SequenceLayout
from tarseem.render.sequence import render_sequence_svg

PLUGIN = DiagramTypePlugin(
    type_id="sequence",
    default_shape="rect",
    layouter_factory=SequenceLayout,
    svg_renderer=render_sequence_svg,
    export_chrome="sequence",
    layout_engine_name="sequence",
)
