"""A10 — sequence diagrams via a deterministic, pure-Python layouter.

Sequence diagrams are NOT a graph-engine job (06 §layout): lifelines are ordered
columns, messages are time-ordered rows, activation bars are overlays. The layouter is
fully deterministic (declared order in, fixed geometry out). It reuses the one positioned
IR (ADR-001): participant heads -> nodes, messages -> edges (dashed = return), activation
bars -> the new ``activations`` overlay; lifeline stems are drawn by the writer.
"""
from __future__ import annotations

import copy

from defusedxml.ElementTree import fromstring  # safe parser (project invariant)

from tarseem.layout.sequence import SequenceLayout
from tarseem.measure import measure_graph
from tarseem.model import PositionedDiagram, compile_spec
from tarseem.render import render_svg

# Login flow: 4 participants, sync calls + dashed returns, one self-message (sign JWT).
LOGIN = {
    "specVersion": "1.0",
    "diagramType": "sequence",
    "meta": {"title": "Login"},
    "nodes": [
        {"id": "user", "label": {"text": "User"}},
        {"id": "ui", "label": {"text": "Browser"}},
        {"id": "api", "label": {"text": "API"}},
        {"id": "db", "label": {"text": "Database"}},
    ],
    "edges": [
        {"id": "m1", "source": "user", "target": "ui", "label": {"text": "submit credentials"}},
        {"id": "m2", "source": "ui", "target": "api", "label": {"text": "POST /login"}},
        {"id": "m3", "source": "api", "target": "db", "label": {"text": "SELECT user"}},
        {"id": "m4", "source": "db", "target": "api", "label": {"text": "row"}, "dashed": True},
        {"id": "m5", "source": "api", "target": "api", "label": {"text": "sign JWT"}},
        {"id": "m6", "source": "api", "target": "ui", "label": {"text": "200 + token"},
         "dashed": True},
        {"id": "m7", "source": "ui", "target": "user", "label": {"text": "dashboard"},
         "dashed": True},
    ],
}


def _layout(spec: dict) -> PositionedDiagram:
    return SequenceLayout().layout(measure_graph(compile_spec(spec)))


# ---- compile ----------------------------------------------------------------
def test_compile_sequence_carries_participants_and_messages():
    g = compile_spec(LOGIN)
    assert g.diagram_type == "sequence"
    assert g.title == "Login"
    assert [n.id for n in g.nodes] == ["user", "ui", "api", "db"]
    assert len(g.edges) == 7


def test_compile_is_pure():
    before = copy.deepcopy(LOGIN)
    compile_spec(LOGIN)
    assert LOGIN == before


# ---- layout: lifelines = ordered columns ------------------------------------
def test_participants_are_columns_in_declared_order():
    d = _layout(LOGIN)
    assert isinstance(d, PositionedDiagram)
    assert d.diagram_type == "sequence"
    heads = {n.id: n for n in d.nodes}
    assert set(heads) == {"user", "ui", "api", "db"}
    xs = [heads[i].x for i in ("user", "ui", "api", "db")]
    assert xs == sorted(xs) and len(set(xs)) == 4  # strictly increasing
    head_y = {n.y for n in d.nodes}
    assert len(head_y) == 1  # all heads share the top row


# ---- layout: messages = time-ordered rows -----------------------------------
def _row_y(edge) -> float:
    return min(p[1] for p in edge.points)


def test_messages_stack_top_to_bottom_in_declared_order():
    d = _layout(LOGIN)
    msgs = [e for e in d.edges if e.id.startswith("m")]
    ys = [_row_y(e) for e in msgs]
    assert ys == sorted(ys) and len(set(ys)) == len(ys)  # strictly increasing rows


def test_return_messages_are_dashed():
    d = _layout(LOGIN)
    by_id = {e.id: e for e in d.edges}
    assert by_id["m4"].style.get("style") == "dashed"
    assert by_id["m6"].style.get("style") == "dashed"
    assert by_id["m1"].style.get("style") != "dashed"  # sync call is solid


def test_self_message_is_a_bracket_to_the_right_of_its_lifeline():
    d = _layout(LOGIN)
    api = next(n for n in d.nodes if n.id == "api")
    lifeline_x = api.x + api.width / 2
    m5 = next(e for e in d.edges if e.id == "m5")
    assert len(m5.points) >= 3  # self-message loops out and back, not a straight line
    assert max(px for px, _ in m5.points) > lifeline_x  # bulges right of the lifeline


# ---- layout: activation bars ------------------------------------------------
def test_activation_bars_overlay_lifelines():
    d = _layout(LOGIN)
    assert len(d.activations) >= 1
    heads = {n.id: n for n in d.nodes}
    top = next(iter(heads.values())).y
    for a in d.activations:
        assert a.height > 0 and a.width > 0
        assert a.y >= top  # bars hang below the head row


# ---- determinism (A3 invariant carried into the new family) -----------------
def test_layout_and_render_are_deterministic():
    d1, d2 = _layout(LOGIN), _layout(LOGIN)
    assert [(n.id, n.x, n.y) for n in d1.nodes] == [(n.id, n.x, n.y) for n in d2.nodes]
    assert render_svg(d1) == render_svg(d2)


# ---- render -----------------------------------------------------------------
def test_render_includes_title_participants_and_messages():
    svg = render_svg(_layout(LOGIN))
    assert svg.lstrip().startswith("<svg")
    assert "Login" in svg
    for n in LOGIN["nodes"]:
        assert n["label"]["text"] in svg
    for e in LOGIN["edges"]:
        assert e["label"]["text"] in svg


def test_rendered_svg_is_wellformed_xml():
    svg = render_svg(_layout(LOGIN))
    fromstring(svg)  # raises on malformed XML (e.g. duplicate attrs)


def test_diagram_has_positive_extent():
    d = _layout(LOGIN)
    assert d.width > 0 and d.height > 0
