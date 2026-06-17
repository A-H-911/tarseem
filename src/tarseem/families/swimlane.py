"""Swimlane / process family: pure-Python lane-grid layout + dedicated band renderer (D3:B).

Band/header/phase chrome in the drawio and PPTX writers is keyed structurally off
``diagram.lanes`` (ADR-007), so ``export_chrome`` stays ``None`` here.
"""
from __future__ import annotations

from tarseem.families.base import DiagramTypePlugin
from tarseem.layout.lanegrid import LaneGridLayout
from tarseem.render.swimlane import render_swimlane_svg

PLUGIN = DiagramTypePlugin(
    type_id="swimlane",
    default_shape="roundrect",
    layouter_factory=LaneGridLayout,
    svg_renderer=render_swimlane_svg,
    layout_engine_name="lanegrid",
)
