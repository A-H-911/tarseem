"""State-machine family: ELK-layered graph, generic renderer, rounded states.

Initial/final pseudostates are keyed structurally off ``node.shape`` (``initial``/``final``)
in the writers, so the family needs no special routing beyond the rounded default.
"""
from __future__ import annotations

from tarseem.families.base import DiagramTypePlugin

PLUGIN = DiagramTypePlugin(type_id="state", default_shape="roundrect")
