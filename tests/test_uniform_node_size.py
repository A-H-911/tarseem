"""Opt-in uniform node sizing (layout.uniformNodeSize) — measure-stage feature (note #3)."""
from __future__ import annotations

from tarseem.measure import measure_graph
from tarseem.model import compile_spec


def _spec(uniform: object) -> dict:
    spec: dict = {
        "specVersion": "1.0",
        "diagramType": "flowchart",
        "nodes": [
            {"id": "a", "label": {"text": "Hi"}},
            {"id": "b", "label": {"text": "A considerably longer node label"}},
        ],
        "edges": [{"source": "a", "target": "b"}],
    }
    if uniform is not None:
        spec["layout"] = {"uniformNodeSize": uniform}
    return spec


def test_off_by_default_keeps_intrinsic_sizes():
    graph = measure_graph(compile_spec(_spec(None)))
    widths = {n.id: n.width for n in graph.nodes}
    assert widths["a"] != widths["b"]  # sized to their own text


def test_true_equalises_all_nodes():
    graph = measure_graph(compile_spec(_spec(True)))
    assert len({n.width for n in graph.nodes}) == 1
    assert len({n.height for n in graph.nodes}) == 1


def test_explicit_dims_force_size():
    graph = measure_graph(compile_spec(_spec({"width": 120, "height": 60})))
    assert all(n.width == 120 and n.height == 60 for n in graph.nodes)


def test_byshape_equalises_within_shape_only():
    spec = _spec("byShape")
    spec["nodes"].append({"id": "d", "shape": "diamond", "label": {"text": "x"}})
    graph = measure_graph(compile_spec(spec))
    by_shape: dict[str, set[float]] = {}
    for n in graph.nodes:
        by_shape.setdefault(n.shape, set()).add(n.width)
    # each shape class is internally uniform
    assert all(len(widths) == 1 for widths in by_shape.values())
