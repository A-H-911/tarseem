"""F1 — the UML activity family (the 11th built-in, closing the F1 family set).

Activity is a built-in plugin (ELK + generic renderer) like state: control flow over actions,
with initial/final pseudostates and diamond decisions from the shared shape vocabulary.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from tarseem.families import all_plugins, get_plugin
from tarseem.validation import validate

requires_node = pytest.mark.skipif(
    shutil.which("node") is None, reason="Node.js runtime not on PATH (ELK graph families)"
)

EXAMPLE = Path("examples/activity-order-approval.json")


def test_activity_is_a_registered_builtin():
    assert "activity" in all_plugins()
    plugin = get_plugin("activity")
    assert plugin.default_shape == "roundrect"
    assert plugin.layouter_factory is None  # ELK
    assert plugin.svg_renderer is None  # generic renderer


def test_activity_example_validates():
    assert validate(json.loads(EXAMPLE.read_text(encoding="utf-8"))).ok


@requires_node
def test_activity_renders_control_flow_with_pseudostates_and_decision():
    from tarseem import Engine

    diagram = Engine().render(json.loads(EXAMPLE.read_text(encoding="utf-8"))).diagram
    assert diagram.diagram_type == "activity"
    shapes = {n.shape for n in diagram.nodes}
    assert {"initial", "final", "diamond", "roundrect"} <= shapes  # activity vocabulary
    assert len(diagram.edges) == 9


@requires_node
def test_activity_works_through_the_agent_surface():
    from tarseem import generate

    out = generate(json.loads(EXAMPLE.read_text(encoding="utf-8")))
    assert out["ok"] is True
    assert out["diagramType"] == "activity"
    assert out["svg"].lstrip().startswith("<svg")
