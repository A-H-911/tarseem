"""Mind-map family: ELK ``mrtree`` (default) / ``radial`` tree, generic renderer (spike-6).

The mrtree-vs-radial algorithm choice is read from ``layout.mindmapStyle`` inside the ELK
adapter; the family itself is a plain rounded-box graph with no dedicated renderer.
"""
from __future__ import annotations

from tarseem.families.base import DiagramTypePlugin

PLUGIN = DiagramTypePlugin(type_id="mindmap", default_shape="roundrect")
