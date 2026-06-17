"""Phase 7 / F9 — the diagram-type plugin registry and its entry-point dogfood.

Proves (a) every built-in family is discoverable through the *same* ``tarseem.types``
entry-point mechanism a third party uses, (b) each pipeline stage resolves a family through
the registry rather than a hardcoded name, and (c) an unregistered type degrades to a generic
ELK graph instead of crashing.
"""
from __future__ import annotations

import shutil
from importlib import metadata

import pytest

from tarseem.families import all_plugins, get_plugin
from tarseem.families.base import DiagramTypePlugin
from tarseem.model import compile_spec

requires_node = pytest.mark.skipif(
    shutil.which("node") is None, reason="Node.js runtime not on PATH"
)

BUILTINS = {
    "flowchart", "architecture", "dependency", "swimlane", "sequence",
    "state", "deployment", "er", "class", "mindmap",
}


# ---- entry-point dogfood (built-ins use the public mechanism) ---------------
def test_all_builtins_registered_via_entry_points():
    """The built-ins must be discoverable through the public ``tarseem.types`` group — the
    identical path an external plugin takes (invariant 8). Not via a private hardcoded list."""
    names = {ep.name for ep in metadata.entry_points(group="tarseem.types")}
    assert BUILTINS <= names


def test_registry_exposes_all_builtins():
    # subset, not equality: external plugins (e.g. the incident-flow example) may also be installed.
    assert BUILTINS <= set(all_plugins())


def test_public_alias_reexports_contract():
    from tarseem.plugins import DiagramTypePlugin as Alias, all_plugins as alias_all

    assert Alias is DiagramTypePlugin
    assert BUILTINS <= set(alias_all())


# ---- per-family descriptors --------------------------------------------------
def test_family_descriptors_match_pipeline_behavior():
    assert get_plugin("flowchart").default_shape == "roundrect"
    assert get_plugin("architecture").default_shape == "rect"
    assert get_plugin("deployment").default_shape == "cube"
    # swimlane + sequence use one-shot Python layouters (no ELK subprocess)
    assert get_plugin("swimlane").layouter_factory is not None
    assert get_plugin("swimlane").layout_engine_name == "lanegrid"
    assert get_plugin("sequence").layouter_factory is not None
    assert get_plugin("sequence").export_chrome == "sequence"
    assert get_plugin("sequence").layout_engine_name == "sequence"
    # dedicated renderers
    assert get_plugin("er").svg_renderer is not None
    assert get_plugin("class").svg_renderer is not None
    assert get_plugin("class").member_compartments is True
    # ELK graph families declare no one-shot layouter and no dedicated renderer
    assert get_plugin("flowchart").layouter_factory is None
    assert get_plugin("flowchart").svg_renderer is None


# ---- unknown type degrades to the generic default ---------------------------
def test_unknown_type_resolves_to_generic_default():
    plugin = get_plugin("totally-unregistered-type")
    assert plugin.default_shape == "rect"
    assert plugin.layouter_factory is None  # ELK
    assert plugin.svg_renderer is None  # generic renderer
    assert plugin.export_chrome is None
    assert plugin.layout_engine_name == "elk"


# ---- the registry actually drives the pipeline (de-risks F9) ----------------
def test_compile_reads_default_shape_from_registry(monkeypatch):
    """A runtime-registered family must steer compilation with no core edit — the exact
    contract F9 (and the incident-flow clone) depends on."""
    custom = DiagramTypePlugin(type_id="custom-doc", default_shape="document")
    monkeypatch.setattr("tarseem.families._registry", {**all_plugins(), "custom-doc": custom})

    spec = {
        "specVersion": "1.0",
        "diagramType": "custom-doc",
        "nodes": [{"id": "n1", "label": {"text": "X"}}],  # no explicit shape
        "edges": [],
    }
    graph = compile_spec(spec)
    assert graph.nodes[0].shape == "document"  # came from the plugin's default_shape


@requires_node
def test_unregistered_type_still_renders_as_generic_graph():
    """An unknown diagramType renders as a generic ELK graph (pre-registry behavior preserved)."""
    from tarseem import Engine

    spec = {
        "specVersion": "1.0",
        "diagramType": "incident-flow",  # not registered until PR2
        "meta": {"title": "Probe"},
        "nodes": [
            {"id": "a", "label": {"text": "Alert"}},
            {"id": "b", "label": {"text": "Resolve"}},
        ],
        "edges": [{"id": "e", "source": "a", "target": "b"}],
    }
    result = Engine().render(spec)
    assert result.diagram.diagram_type == "incident-flow"
    assert result.svg.lstrip().startswith("<svg")
