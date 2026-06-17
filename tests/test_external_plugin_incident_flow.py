"""Phase 7 / F9 — plugin exercise #1: an EXTERNAL diagram type, zero core edits.

``tarseem-incident-flow`` (under ``examples/plugins/incident-flow/``) is a separate distribution
that adds an ``incident-flow`` family purely by registering a ``DiagramTypePlugin`` on the
``tarseem.types`` entry-point group — built only from ``docs/extending/clone-a-type.md``.

These tests require that example package to be installed (``pip install -e
examples/plugins/incident-flow``); CI installs it. When it is absent (a plain checkout) the
entry-point cases skip, but the "core is untouched" guard always runs.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from tarseem.families import all_plugins

EXAMPLE = Path("examples/plugins/incident-flow/example.json")

requires_node = pytest.mark.skipif(
    shutil.which("node") is None, reason="Node.js runtime not on PATH"
)
requires_plugin = pytest.mark.skipif(
    "incident-flow" not in all_plugins(),
    reason="example plugin not installed (pip install -e examples/plugins/incident-flow)",
)


@requires_plugin
def test_external_type_discovered_via_entry_points():
    from importlib import metadata

    names = {ep.name for ep in metadata.entry_points(group="tarseem.types")}
    assert "incident-flow" in names
    assert all_plugins()["incident-flow"].default_shape == "stadium"


@requires_plugin
@requires_node
def test_external_type_renders_through_the_full_pipeline():
    from tarseem import Engine

    spec = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    result = Engine().render(spec)
    assert result.diagram.diagram_type == "incident-flow"
    assert result.svg.lstrip().startswith("<svg")
    # the plugin's default_shape drove compilation: a node with no explicit `shape` is a stadium
    detect = next(n for n in result.diagram.nodes if n.id == "detect")
    assert detect.shape == "stadium"
    # a node WITH an explicit shape keeps it (the default only fills the gap)
    triage = next(n for n in result.diagram.nodes if n.id == "triage")
    assert triage.shape == "diamond"


@requires_plugin
def test_external_type_exports_with_capability_report(tmp_path):
    from tarseem import Engine

    spec = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    result = Engine().render(spec)
    paths = result.export(["svg", "drawio"], tmp_path, name="incident")
    assert paths["svg"].exists()
    assert paths["drawio"].exists()
    # the drawio writer ran for an unknown-to-core family and reported its fidelity (invariant 6)
    assert "drawio" in result.reports


def test_engine_core_never_names_the_external_type():
    """The crux of F9: the engine must not contain the string ``incident-flow`` anywhere — the
    type is supplied entirely by the external plugin, not learned by the core."""
    src = Path("src/tarseem")
    offenders = [
        p.relative_to(src).as_posix()
        for p in src.rglob("*.py")
        if "incident-flow" in p.read_text(encoding="utf-8")
    ]
    assert offenders == [], f"core source references the external type: {offenders}"
