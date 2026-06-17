"""Deployment / infrastructure family: ELK-layered graph, generic renderer, 3D cube nodes."""
from __future__ import annotations

from tarseem.families.base import DiagramTypePlugin

PLUGIN = DiagramTypePlugin(type_id="deployment", default_shape="cube")
