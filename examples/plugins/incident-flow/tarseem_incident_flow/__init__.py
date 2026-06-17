"""incident-flow: an example third-party Tarseem diagram type.

A clone of the built-in ``flowchart`` family for incident-response runbooks. It reuses ELK
layered layout and the generic graph renderer (the defaults), and only customises the default
node shape so incident states read as stadium "terminators". Built entirely by following
``docs/extending/clone-a-type.md`` — nothing under ``src/tarseem`` is touched (F9).

Register it by exposing ``PLUGIN`` on the ``tarseem.types`` entry-point group (see pyproject):

    [project.entry-points."tarseem.types"]
    incident-flow = "tarseem_incident_flow:PLUGIN"
"""
from __future__ import annotations

from tarseem.plugins import DiagramTypePlugin

PLUGIN = DiagramTypePlugin(
    type_id="incident-flow",
    # The one customisation: incident states default to stadium terminators instead of the
    # flowchart's rounded rectangles. Layout (ELK) and rendering (generic) are inherited.
    default_shape="stadium",
)
