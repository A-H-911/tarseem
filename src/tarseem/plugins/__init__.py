"""Public plugin API for diagram-type authors (invariant 8, F9).

Third parties extend Tarseem with new diagram types without touching the core. Declare a
:class:`DiagramTypePlugin` and expose it via the ``tarseem.types`` entry-point group — the
identical mechanism the built-in families use (``tarseem.families``):

    # mypackage/incident_flow.py
    from tarseem.plugins import DiagramTypePlugin
    PLUGIN = DiagramTypePlugin(type_id="incident-flow", default_shape="roundrect")

    # pyproject.toml
    [project.entry-points."tarseem.types"]
    incident-flow = "mypackage.incident_flow:PLUGIN"

The registry (:func:`get_plugin`, :func:`all_plugins`) is shared with the core pipeline, so
a registered type flows through compile → layout → render → export with no core edits.
"""
from __future__ import annotations

from tarseem.families import (
    ENTRY_POINT_GROUP,
    DiagramTypePlugin,
    all_plugins,
    get_plugin,
)

__all__ = ["DiagramTypePlugin", "get_plugin", "all_plugins", "ENTRY_POINT_GROUP"]
