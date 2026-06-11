"""Adapter contract (⚠1 / 09 §1 adapter-contract row).

Every layout adapter — ELK (graph families), lane-grid (swimlane), sequence — must satisfy
the SAME positioned-IR invariants, regardless of how it computes layout. This single
parametrized suite is the shared gate: a new adapter is wired in here and must pass the
same contract, instead of relying on each family's bespoke tests. Invariants checked:
valid positive extent, finite/positive node geometry, finite edge points, determinism
(two runs identical), and no ELK JSON leaking into the IR (ADR-002).
"""
from __future__ import annotations

import json
import math
import shutil
from pathlib import Path

import pytest

from tarseem.layout.lanegrid import LaneGridLayout
from tarseem.layout.sequence import SequenceLayout
from tarseem.measure import measure_graph
from tarseem.model import PositionedDiagram, compile_spec

ROOT = Path(__file__).resolve().parent.parent
requires_node = pytest.mark.skipif(shutil.which("node") is None, reason="Node.js not on PATH")


def _graph(name: str):
    spec = json.loads((ROOT / "examples" / f"{name}.json").read_text(encoding="utf-8"))
    return measure_graph(compile_spec(spec))


def _build_lanegrid() -> PositionedDiagram:
    return LaneGridLayout().layout(_graph("swimlane-bug-triage"))


def _build_sequence() -> PositionedDiagram:
    return SequenceLayout().layout(_graph("sequence-login"))


def _build_elk() -> PositionedDiagram:
    from tarseem.layout.elk import ElkLayout

    with ElkLayout() as elk:
        return elk.layout(_graph("flowchart"))


# (id, builder, needs_node)
ADAPTERS = [
    ("lanegrid", _build_lanegrid, False),
    ("sequence", _build_sequence, False),
    ("elk", _build_elk, True),
]


def _finite(*vals: float) -> bool:
    return all(math.isfinite(v) for v in vals)


def _no_elk_leak(style: dict) -> bool:
    """ELK JSON must stay inside the layout adapter (ADR-002): resolved style dicts must
    not carry ELK structural keys."""
    forbidden = {"layoutOptions", "children", "$H", "x", "y"}
    return not (set(style) & forbidden)


def _assert_contract(d: PositionedDiagram) -> None:
    assert isinstance(d, PositionedDiagram)
    assert d.width > 0 and d.height > 0 and _finite(d.width, d.height)
    for n in d.nodes:
        assert n.width > 0 and n.height > 0, f"{n.id}: non-positive size"
        assert _finite(n.x, n.y, n.width, n.height), f"{n.id}: non-finite geometry"
        assert _no_elk_leak(n.style), f"{n.id}: ELK keys leaked into node style"
    for e in d.edges:
        assert len(e.points) >= 1, f"{e.id}: empty routing"
        for px, py in e.points:
            assert _finite(px, py), f"{e.id}: non-finite point"
        assert _no_elk_leak(e.style), f"{e.id}: ELK keys leaked into edge style"


def _params():
    out = []
    for name, builder, needs_node in ADAPTERS:
        mark = (requires_node,) if needs_node else ()
        out.append(pytest.param(builder, id=name, marks=mark))
    return out


@pytest.mark.parametrize("builder", _params())
def test_adapter_satisfies_positioned_ir_contract(builder):
    _assert_contract(builder())


@pytest.mark.parametrize("builder", _params())
def test_adapter_is_deterministic(builder):
    a, b = builder(), builder()
    assert [(n.id, n.x, n.y, n.width, n.height) for n in a.nodes] == \
           [(n.id, n.x, n.y, n.width, n.height) for n in b.nodes]
    assert [e.points for e in a.edges] == [e.points for e in b.edges]
