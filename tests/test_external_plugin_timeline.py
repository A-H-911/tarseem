"""Phase 7 / F9 — plugin exercise #2: an external CUSTOM LAYOUTER, zero core edits.

``tarseem-timeline`` (``examples/plugins/timeline/``) is the second freeze-gate exercise. Unlike
incident-flow (a cosmetic ``default_shape`` change), it supplies its own ``layouter_factory`` — a
pure-Python single-axis layouter replacing ELK — proving the plugin API extends *layout*, not just
defaults. Requires the example package installed (CI installs it); cases skip when it is absent.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tarseem.families import all_plugins

EXAMPLE = Path("examples/plugins/timeline/example.json")

requires_plugin = pytest.mark.skipif(
    "timeline" not in all_plugins(),
    reason="example plugin not installed (pip install -e examples/plugins/timeline)",
)


@requires_plugin
def test_timeline_discovered_and_supplies_a_layouter():
    from importlib import metadata

    names = {ep.name for ep in metadata.entry_points(group="tarseem.types")}
    assert "timeline" in names
    plugin = all_plugins()["timeline"]
    assert plugin.layouter_factory is not None  # the extension point under test
    assert plugin.layout_engine_name == "timeline"


@requires_plugin
def test_custom_layouter_places_events_along_one_axis():
    from tarseem import Engine

    spec = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    diagram = Engine().render(spec).diagram
    xs = [n.x for n in diagram.nodes]
    assert xs == sorted(xs)  # left-to-right, no ELK
    assert len(set(round(n.y, 3) for n in diagram.nodes)) == 1  # single axis: shared centre line
    assert len(diagram.edges) == 3


@requires_plugin
def test_custom_layouter_mirrors_for_rtl():
    from tarseem import Engine

    spec = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    spec["direction"] = "RL"
    nodes = Engine().render(spec).diagram.nodes
    first = next(n for n in nodes if n.id == spec["nodes"][0]["id"])
    assert first.x == max(n.x for n in nodes)  # first event mirrored to the right (invariant 4)


@requires_plugin
def test_timeline_works_through_the_agent_surface():
    from tarseem import generate

    out = generate(json.loads(EXAMPLE.read_text(encoding="utf-8")))
    assert out["ok"] is True
    assert out["diagramType"] == "timeline"
    assert out["provenance"]["layoutEngine"] == "timeline"


def test_engine_core_never_names_the_timeline_type():
    """F9 guard: the engine must not contain the string ``timeline`` — the family (and its
    layouter) is supplied entirely by the external plugin."""
    src = Path("src/tarseem")
    offenders = [
        p.relative_to(src).as_posix()
        for p in src.rglob("*.py")
        if "timeline" in p.read_text(encoding="utf-8")
    ]
    assert offenders == [], f"core source references the external type: {offenders}"
