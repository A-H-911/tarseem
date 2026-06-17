"""Phase 5 sub-stage 5 — state + deployment families (ELK-layered, new shape vocab).

Both families route through the existing ELK graph path; they only add shapes (state's
initial/final pseudostate markers, deployment's 3D cube node) and per-family default
shapes. Shape rendering is unit-tested on a hand-built PositionedDiagram (no Node needed);
an end-to-end Engine render of each golden example is gated on a Node runtime for ELK.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from defusedxml.ElementTree import fromstring  # safe parser (project invariant)

from tarseem.measure import _shared_measurer
from tarseem.model import compile_spec
from tarseem.model.ir import Label, PositionedDiagram, PositionedNode
from tarseem.render import render_svg

ROOT = Path(__file__).resolve().parent.parent
requires_node = pytest.mark.skipif(
    shutil.which("node") is None, reason="Node.js runtime not on PATH (ELK layout)"
)


def _node(nid: str, shape: str, text: str = "") -> PositionedNode:
    return PositionedNode(id=nid, x=20, y=20, width=40, height=40, label=Label(text=text),
                          shape=shape)


def _diagram(nodes, family: str) -> PositionedDiagram:
    return PositionedDiagram(width=200, height=120, nodes=tuple(nodes), edges=(),
                             diagram_type=family)


# ---- defaults + sizing ------------------------------------------------------
def test_state_default_shape_is_roundrect():
    g = compile_spec({"specVersion": "1.0", "diagramType": "state",
                      "nodes": [{"id": "a", "label": {"text": "A"}}], "edges": []})
    assert g.nodes[0].shape == "roundrect"


def test_deployment_default_shape_is_cube():
    g = compile_spec({"specVersion": "1.0", "diagramType": "deployment",
                      "nodes": [{"id": "a", "label": {"text": "A"}}], "edges": []})
    assert g.nodes[0].shape == "cube"


def test_pseudostate_markers_are_fixed_square():
    m = _shared_measurer()
    from tarseem.model.ir import LogicalNode

    init = m.node_size(LogicalNode(id="i", label=Label(text=""), shape="initial"))
    fin = m.node_size(LogicalNode(id="f", label=Label(text=""), shape="final"))
    assert init[0] == init[1]  # square
    assert fin[0] == fin[1]
    assert fin > init  # final ring is larger than the initial dot


# ---- shape rendering (no Node) ----------------------------------------------
def test_initial_renders_a_filled_dot():
    svg = render_svg(_diagram([_node("s", "initial")], "state"))
    fromstring(svg)
    assert svg.count("<circle") == 1  # a single solid dot


def test_final_renders_a_bullseye():
    svg = render_svg(_diagram([_node("e", "final")], "state"))
    fromstring(svg)
    assert svg.count("<circle") == 2  # outer ring + inner dot


def test_cube_renders_three_faces():
    svg = render_svg(_diagram([_node("n", "cube", "Server")], "deployment"))
    fromstring(svg)
    assert svg.count("<polygon") == 2  # top + right depth faces
    assert "<rect" in svg and "Server" in svg  # front face + label


# ---- end-to-end (Node-gated) ------------------------------------------------
@requires_node
@pytest.mark.parametrize("name", ["state-order-lifecycle", "deployment-web-stack"])
def test_example_renders_through_elk(name: str):
    from tarseem.engine import Engine

    spec = json.loads((ROOT / "examples" / f"{name}.json").read_text(encoding="utf-8"))
    res = Engine().render(spec)
    assert res.versions.get("elkjs")  # laid out by ELK
    svg = res.svg
    fromstring(svg)
    for node in spec["nodes"]:
        assert node["label"]["text"] in svg
