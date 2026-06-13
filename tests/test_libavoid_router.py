"""Phase 5 — optional libavoid re-router (ADR-006), experimental + opt-in.

Light tests: the bundle is vendored; the opt-in flag routes through libavoid; and on a
fixed-position obstacle layout libavoid avoids routing edges through node boxes far better
than naive orthogonal routing (its proven niche). Default path is untouched (no `router`
key) — covered by the wider suite staying green.
"""
from __future__ import annotations

import shutil

import pytest

from tarseem.layout.libavoid import LibavoidRouter, libavoid_available
from tarseem.report import _segments

requires_node = pytest.mark.skipif(
    shutil.which("node") is None, reason="Node.js runtime not on PATH (libavoid WASM server)"
)

# fixed grid: top a,b,c / bottom d,e,f; cross-field edges must dodge the middle nodes
_POS = {"a": (20, 20), "b": (260, 20), "c": (500, 20),
        "d": (20, 220), "e": (260, 220), "f": (500, 220)}
_EDGES = [("a", "f"), ("c", "d"), ("a", "c"), ("d", "f"),
          ("a", "e"), ("c", "e"), ("d", "b"), ("f", "b")]
_W, _H = 90, 44


def _fixed_spec() -> dict:
    return {
        "specVersion": "0.1", "diagramType": "flowchart", "direction": "TB",
        "layout": {"respectManualPositions": True, "router": "libavoid"},
        "nodes": [{"id": k, "label": {"text": k.upper()}, "position": {"x": x, "y": y}}
                  for k, (x, y) in _POS.items()],
        "edges": [{"id": f"{s}{t}", "source": s, "target": t} for s, t in _EDGES],
    }


def _through_node_count(diagram, endpoints) -> int:
    """How many (edge, intervening-node) pairs have an edge segment crossing the node box."""
    boxes = {n.id: (n.x, n.y, n.width, n.height) for n in diagram.nodes}
    hits = 0
    for e in diagram.edges:
        a, b = endpoints[e.id]
        for nid, (rx, ry, rw, rh) in boxes.items():
            if nid in (a, b):
                continue
            crossed = False
            for p, q in _segments(e):
                for i in range(1, 24):
                    x = p[0] + (q[0] - p[0]) * i / 24
                    y = p[1] + (q[1] - p[1]) * i / 24
                    if rx + 1 < x < rx + rw - 1 and ry + 1 < y < ry + rh - 1:
                        crossed = True
                        break
                if crossed:
                    break
            hits += int(crossed)
    return hits


def test_libavoid_is_vendored():
    assert libavoid_available()


def test_capabilities_report_is_experimental():
    caps = LibavoidRouter().capabilities()
    assert caps["engine"] == "libavoid"
    assert "experimental" in caps["role"]
    assert caps["supports"]["obstacle_avoidance"] is True


@requires_node
def test_opt_in_router_reroutes_and_avoids_obstacles():
    from tarseem.engine import Engine
    from tarseem.model import compile_spec

    spec = _fixed_spec()
    endpoints = {e.id: (e.source, e.target) for e in compile_spec(spec).edges}
    result = Engine().render(spec)

    assert result.versions.get("libavoid-js")  # the opt-in router actually ran
    # naive horizontal-then-vertical routing on the same centres, for comparison
    centres = {k: (x + _W / 2, y + _H / 2) for k, (x, y) in _POS.items()}
    from tarseem.model.ir import Label, PositionedDiagram, PositionedEdge

    naive_edges = tuple(
        PositionedEdge(id=f"{s}{t}", label=Label(text=""), points=(
            centres[s], (centres[t][0], centres[s][1]), centres[t]))
        for s, t in _EDGES
    )
    naive = PositionedDiagram(width=result.diagram.width, height=result.diagram.height,
                              nodes=result.diagram.nodes, edges=naive_edges,
                              diagram_type="flowchart")

    libavoid_hits = _through_node_count(result.diagram, endpoints)
    naive_hits = _through_node_count(naive, endpoints)
    assert libavoid_hits < naive_hits  # obstacle avoidance: the whole point of the niche
