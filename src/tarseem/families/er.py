"""Entity-relationship family: ELK-layered graph + dedicated attribute-table renderer.

Entity rows are keyed structurally off ``node.rows`` in the writers; the family default
shape is ``table``.
"""
from __future__ import annotations

from tarseem.families.base import DiagramTypePlugin
from tarseem.render.er import render_er_svg

PLUGIN = DiagramTypePlugin(
    type_id="er",
    default_shape="table",
    svg_renderer=render_er_svg,
)
