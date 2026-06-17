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
    # Profile (v1.0, 05 §1 anti-generic guard): a sequence is not lane/phase-based. maxItems:0
    # (rather than a boolean `false`) makes the error point precisely at /lanes or /phases.
    schema_extension={"properties": {"lanes": {"maxItems": 0}, "phases": {"maxItems": 0}}},
)
