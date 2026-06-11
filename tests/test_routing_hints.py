"""Phase 5 — routing hints threaded through the pipeline.

Pass A (this file's compile-level tests, no Node): the schema accepts the hint keys and
``compile_spec`` carries them into the logical IR. Pass B (Node-gated, below) asserts the
ELK adapter honours them — manual waypoints survive a render round-trip, edge priority and
preferred direction reach the ELK request, and ``respectManualPositions`` pins nodes.

Hints (06 §2): ``edge.routing.waypoints`` (manual, post-layout splice), ``edge.priority``
(straightness bias), ``edge.preferredDirection`` (per-edge exit side), node ``position`` +
``layout.respectManualPositions`` (interactive/fixed placement).
"""
from __future__ import annotations

import shutil

import pytest

from tarseem.model import compile_spec
from tarseem.validation import validate

requires_node = pytest.mark.skipif(
    shutil.which("node") is None, reason="Node.js runtime not on PATH (ELK graph families)"
)


def _spec(**over: object) -> dict:
    base: dict = {
        "specVersion": "0.1",
        "diagramType": "flowchart",
        "direction": "TB",
        "nodes": [
            {"id": "a", "label": {"text": "A"}},
            {"id": "b", "label": {"text": "B"}},
        ],
        "edges": [{"id": "e1", "source": "a", "target": "b"}],
    }
    base.update(over)
    return base


# -- schema acceptance --------------------------------------------------------


def test_schema_accepts_routing_hints():
    spec = _spec(
        nodes=[
            {"id": "a", "label": {"text": "A"}, "position": {"x": 10, "y": 20}},
            {"id": "b", "label": {"text": "B"}},
        ],
        edges=[
            {
                "id": "e1",
                "source": "a",
                "target": "b",
                "priority": 5,
                "preferredDirection": "DOWN",
                "routing": {"mode": "orthogonal", "waypoints": [[30, 40], [30, 80]]},
            }
        ],
        layout={"respectManualPositions": True},
    )
    result = validate(spec)
    assert result.ok, [i.message for i in result.issues]


# -- compile carries hints into the IR ----------------------------------------


def test_compile_threads_edge_priority_and_preferred_direction():
    g = compile_spec(
        _spec(edges=[{"id": "e1", "source": "a", "target": "b", "priority": 7,
                      "preferredDirection": "LEFT"}])
    )
    edge = g.edges[0]
    assert edge.priority == 7
    assert edge.preferred_direction == "LEFT"


def test_compile_threads_manual_waypoints():
    g = compile_spec(
        _spec(edges=[{"id": "e1", "source": "a", "target": "b",
                      "routing": {"waypoints": [[30, 40], [30, 80]]}}])
    )
    assert g.edges[0].waypoints == ((30.0, 40.0), (30.0, 80.0))


def test_compile_threads_node_position_and_respect_flag():
    g = compile_spec(
        _spec(
            nodes=[
                {"id": "a", "label": {"text": "A"}, "position": {"x": 10, "y": 20}},
                {"id": "b", "label": {"text": "B"}},
            ],
            layout={"respectManualPositions": True},
        )
    )
    by_id = {n.id: n for n in g.nodes}
    assert by_id["a"].position == (10.0, 20.0)
    assert by_id["b"].position is None
    assert g.respect_manual_positions is True


def test_defaults_are_inert_when_hints_absent():
    g = compile_spec(_spec())
    assert g.edges[0].priority is None
    assert g.edges[0].preferred_direction is None
    assert g.edges[0].waypoints == ()
    assert g.nodes[0].position is None
    assert g.respect_manual_positions is False


# -- Pass B: ELK adapter honours the hints ------------------------------------


def test_edge_priority_reaches_the_elk_request():
    """White-box: priority maps to the layered straightness option in the ELK request.
    No Node needed — this exercises only the IR->ELK translation, which stays in-module."""
    from tarseem.layout.elk import ElkLayout

    g = compile_spec(_spec(edges=[{"id": "e1", "source": "a", "target": "b", "priority": 9}]))
    elk_graph = ElkLayout()._to_elk(g)
    edge = next(e for e in elk_graph["edges"] if e["id"] == "e1")
    assert edge["layoutOptions"]["elk.layered.priority.straightness"] == "9"


def test_no_priority_emits_no_edge_layout_options():
    from tarseem.layout.elk import ElkLayout

    g = compile_spec(_spec())
    edge = next(e for e in ElkLayout()._to_elk(g)["edges"] if e["id"] == "e1")
    assert "layoutOptions" not in edge


@requires_node
def test_manual_waypoints_appear_in_routed_edge():
    from tarseem.engine import Engine

    wp = [[40.0, 70.0], [40.0, 130.0]]
    spec = _spec(edges=[{"id": "e1", "source": "a", "target": "b",
                         "routing": {"waypoints": wp}}])
    edge = next(e for e in Engine().render(spec).diagram.edges if e.id == "e1")
    interior = edge.points[1:-1]
    assert (40.0, 70.0) in interior and (40.0, 130.0) in interior
    # waypoints sit strictly between the node attachment endpoints (not first/last)
    assert edge.points[0] not in wp and edge.points[-1] not in wp


@requires_node
def test_manual_waypoints_survive_a_render_round_trip():
    from tarseem.engine import Engine

    spec = _spec(edges=[{"id": "e1", "source": "a", "target": "b",
                         "routing": {"waypoints": [[40.0, 70.0], [40.0, 130.0]]}}])
    first = next(e for e in Engine().render(spec).diagram.edges if e.id == "e1")
    second = next(e for e in Engine().render(spec).diagram.edges if e.id == "e1")
    assert first.points == second.points  # deterministic re-render reproduces the route


@requires_node
def test_respect_manual_positions_preserves_seeded_arrangement():
    """Interactive placement keeps the manual relative ordering on both axes (probe-proven:
    spacing is normalized, ordering is honoured)."""
    from tarseem.engine import Engine

    spec = {
        "specVersion": "0.1",
        "diagramType": "flowchart",
        "direction": "TB",
        "layout": {"respectManualPositions": True},
        "nodes": [
            {"id": "top", "label": {"text": "Top"}, "position": {"x": 200, "y": 10}},
            {"id": "left", "label": {"text": "Left"}, "position": {"x": 20, "y": 200}},
            {"id": "right", "label": {"text": "Right"}, "position": {"x": 400, "y": 200}},
        ],
        "edges": [
            {"id": "e1", "source": "top", "target": "left"},
            {"id": "e2", "source": "top", "target": "right"},
        ],
    }
    by_id = {n.id: n for n in Engine().render(spec).diagram.nodes}
    assert by_id["top"].y < by_id["left"].y  # seeded-top stays above
    assert by_id["top"].y < by_id["right"].y
    assert by_id["left"].x < by_id["right"].x  # seeded-left stays left of seeded-right


@requires_node
def test_preferred_direction_forces_source_exit_side():
    """preferredDirection=LEFT makes the edge leave the source's west side (start x near the
    node's left edge, left of the node centre)."""
    from tarseem.engine import Engine

    spec = _spec(
        direction="TB",
        edges=[{"id": "e1", "source": "a", "target": "b", "preferredDirection": "LEFT"}],
    )
    d = Engine().render(spec).diagram
    a = next(n for n in d.nodes if n.id == "a")
    e = next(e for e in d.edges if e.id == "e1")
    start_x = e.points[0][0]
    assert start_x <= a.x + 1.0  # exits at/left of the node's left edge, not the bottom
