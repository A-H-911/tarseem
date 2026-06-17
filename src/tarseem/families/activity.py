"""UML activity family: ELK-layered control flow, generic renderer.

An activity diagram is control flow over actions. It reuses the shared shape vocabulary like the
state family: actions are rounded boxes (the default), `initial`/`final` pseudostates mark
start/stop, and `diamond` nodes are decision/merge points. Fork/join can be modelled as
dark-filled `rect` bars via node style. No dedicated layouter or renderer is needed (ELK +
the generic graph renderer), so the family is a plain plugin.
"""
from __future__ import annotations

from tarseem.families.base import DiagramTypePlugin

PLUGIN = DiagramTypePlugin(type_id="activity", default_shape="roundrect")
