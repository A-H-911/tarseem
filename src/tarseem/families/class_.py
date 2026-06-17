"""UML class family: ELK-layered graph + dedicated compartment renderer.

``member_compartments=True`` tells the compiler to read ``attributes``/``methods`` as UML
name/attribute/method compartments instead of ER attribute rows.
"""
from __future__ import annotations

from tarseem.families.base import DiagramTypePlugin
from tarseem.render.class_ import render_class_svg

PLUGIN = DiagramTypePlugin(
    type_id="class",
    default_shape="class",
    member_compartments=True,
    svg_renderer=render_class_svg,
)
