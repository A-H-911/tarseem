"""RenderReport: deterministic quality metrics over the positioned IR (Phase 3).

Pure geometry — edge-crossing count, node-overlap count, extent — plus an engine-injected
render time. These are the numeric signal the gallery shows per sample and the regression
suite asserts on (09 §1). Nothing here mutates the diagram.
"""
from __future__ import annotations

from dataclasses import dataclass

from tarseem.model.ir import PositionedDiagram, PositionedEdge, PositionedNode

__all__ = ["RenderReport", "analyze"]

Point = tuple[float, float]


@dataclass(frozen=True)
class RenderReport:
    node_count: int
    edge_count: int
    crossings: int
    overlaps: int
    width: float
    height: float
    render_ms: float | None = None

    def to_dict(self) -> dict:
        return {
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "crossings": self.crossings,
            "overlaps": self.overlaps,
            "width": self.width,
            "height": self.height,
            "render_ms": self.render_ms,
        }


def _segments(edge: PositionedEdge) -> list[tuple[Point, Point]]:
    p = edge.points
    return [(p[i], p[i + 1]) for i in range(len(p) - 1)]


def _orient(a: Point, b: Point, c: Point) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _proper_intersect(s1: tuple[Point, Point], s2: tuple[Point, Point]) -> bool:
    """True only for a proper crossing. Segments that share an endpoint (edges fanning
    out of the same node) or merely touch/overlap collinearly do not count."""
    p1, p2 = s1
    p3, p4 = s2
    if p1 in (p3, p4) or p2 in (p3, p4):
        return False
    d1, d2 = _orient(p3, p4, p1), _orient(p3, p4, p2)
    d3, d4 = _orient(p1, p2, p3), _orient(p1, p2, p4)
    return (d1 > 0) != (d2 > 0) and (d3 > 0) != (d4 > 0)


def _count_crossings(edges: tuple[PositionedEdge, ...]) -> int:
    segs = [(e.id, s) for e in edges for s in _segments(e)]
    crossings = 0
    for i in range(len(segs)):
        eid_i, si = segs[i]
        for j in range(i + 1, len(segs)):
            eid_j, sj = segs[j]
            if eid_i == eid_j:  # ignore self-bends within one polyline
                continue
            if _proper_intersect(si, sj):
                crossings += 1
    return crossings


def _overlaps(a: PositionedNode, b: PositionedNode) -> bool:
    return (
        a.x < b.x + b.width
        and b.x < a.x + a.width
        and a.y < b.y + b.height
        and b.y < a.y + a.height
    )


def _count_overlaps(nodes: tuple[PositionedNode, ...]) -> int:
    count = 0
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            if _overlaps(nodes[i], nodes[j]):
                count += 1
    return count


def analyze(diagram: PositionedDiagram, render_ms: float | None = None) -> RenderReport:
    """Compute geometry metrics for ``diagram``. ``render_ms`` is injected (timed by the
    caller); geometry is deterministic, so equal diagrams give equal reports."""
    return RenderReport(
        node_count=len(diagram.nodes),
        edge_count=len(diagram.edges),
        crossings=_count_crossings(diagram.edges),
        overlaps=_count_overlaps(diagram.nodes),
        width=diagram.width,
        height=diagram.height,
        render_ms=render_ms,
    )
