"""Phase 5 sub-stage 5 — ER family with per-row port anchoring.

An entity is a node with `attributes`; each attribute is a table row whose vertical geometry
is stamped by the measurement stage. Relationship edges reference attribute ids via
`sourcePort`/`targetPort`, and the ELK adapter anchors the connector to the exact row on each
entity's facing side. Layout runs through ELK (Node-gated end-to-end); compile, measure,
validation, the row connector, and the table writer are tested without Node.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from defusedxml.ElementTree import fromstring  # safe parser (project invariant)

from tarseem.layout.elk import _row_anchor, _row_connector
from tarseem.measure import measure_graph
from tarseem.model import compile_spec
from tarseem.model.ir import EntityRow, Label, PositionedDiagram, PositionedEdge, PositionedNode
from tarseem.render import render_svg
from tarseem.validation import validate

ROOT = Path(__file__).resolve().parent.parent
requires_node = pytest.mark.skipif(
    shutil.which("node") is None, reason="Node.js runtime not on PATH (ELK layout)"
)

_ENTITY = {
    "id": "customer", "label": {"text": "Customer"},
    "attributes": [
        {"id": "id", "label": {"text": "id"}, "key": "PK"},
        {"id": "email", "label": {"text": "email"}},
    ],
}


def _spec(nodes, edges) -> dict:
    return {"specVersion": "0.1", "diagramType": "er", "nodes": nodes, "edges": edges}


# ---- compile ----------------------------------------------------------------
def test_attributes_compile_to_rows():
    g = compile_spec(_spec([_ENTITY], []))
    node = g.nodes[0]
    assert node.shape == "table"  # er default shape
    assert [r.id for r in node.rows] == ["id", "email"]
    assert node.rows[0].key == "PK" and node.rows[1].key is None


# ---- measure ----------------------------------------------------------------
def test_table_rows_get_stamped_geometry():
    g = measure_graph(compile_spec(_spec([_ENTITY], [])))
    node = g.nodes[0]
    assert node.width and node.height  # sized
    # rows tile downward below the title, each with a positive height
    assert node.rows[0].y_offset < node.rows[1].y_offset
    assert all(r.height > 0 for r in node.rows)
    # title + two rows == total height
    assert node.rows[-1].y_offset + node.rows[-1].height == pytest.approx(node.height)


# ---- validation -------------------------------------------------------------
def test_port_referencing_an_attribute_is_valid():
    order = {"id": "order", "label": {"text": "Order"},
             "attributes": [{"id": "cust", "label": {"text": "cust"}, "key": "FK"}]}
    spec = _spec([_ENTITY, order], [
        {"id": "r", "source": "order", "target": "customer",
         "sourcePort": "cust", "targetPort": "id"}])
    assert validate(spec).ok


def test_unknown_port_still_rejected():
    spec = _spec([_ENTITY], [
        {"id": "r", "source": "customer", "target": "customer", "sourcePort": "nope"}])
    result = validate(spec)
    assert not result.ok
    assert any(issue.code == "E_BAD_PORT" for issue in result.errors)


# ---- row connector (no Node) ------------------------------------------------
def _node(nid, x, rows) -> PositionedNode:
    return PositionedNode(id=nid, x=x, y=0, width=120, height=100, label=Label(text=nid),
                          shape="table", rows=rows)


def test_row_anchor_targets_the_named_row():
    rows = (EntityRow(id="a", label=Label(text="a"), y_offset=30, height=20),
            EntityRow(id="b", label=Label(text="b"), y_offset=50, height=20))
    n = _node("e", 0, rows)
    assert _row_anchor(n, "b") == 0 + 50 + 10  # y + y_offset + height/2
    assert _row_anchor(n, "missing") == n.y + n.height / 2  # falls back to node centre


def test_connector_attaches_on_facing_sides():
    rows = (EntityRow(id="k", label=Label(text="k"), y_offset=30, height=20),)
    left = _node("l", 0, rows)      # right edge at x=120
    right = _node("r", 300, rows)   # left edge at x=300
    pts = _row_connector(left, "k", right, "k")
    assert pts[0][0] == 120  # exits the left entity's right side
    assert pts[-1][0] == 300  # enters the right entity's left side
    assert pts[0][1] == _row_anchor(left, "k")  # at the row centre


# ---- table writer (no Node) -------------------------------------------------
def test_er_writer_draws_table_and_key_tags():
    rows = (EntityRow(id="id", label=Label(text="id"), key="PK", y_offset=30, height=24),
            EntityRow(id="email", label=Label(text="email"), y_offset=54, height=24))
    diagram = PositionedDiagram(
        width=200, height=140,
        nodes=(PositionedNode(id="customer", x=10, y=10, width=140, height=78,
                              label=Label(text="Customer"), shape="table", rows=rows),),
        edges=(PositionedEdge(id="r", points=((10, 40), (10, 40)), label=Label(text="N:1"),
                              label_xy=(10, 40)),),
        diagram_type="er")
    svg = render_svg(diagram)
    fromstring(svg)  # well-formed
    assert "Customer" in svg and "email" in svg
    assert ">PK<" in svg  # the key tag rendered


# ---- end-to-end (Node-gated) ------------------------------------------------
@requires_node
def test_er_example_renders_through_elk():
    from tarseem.engine import Engine

    spec = json.loads((ROOT / "examples" / "er-shop.json").read_text(encoding="utf-8"))
    res = Engine().render(spec)
    assert res.versions.get("elkjs")
    svg = res.svg
    fromstring(svg)
    for node in spec["nodes"]:
        assert node["label"]["text"] in svg
        for attr in node["attributes"]:
            assert attr["label"]["text"] in svg
