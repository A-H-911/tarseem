"""ELK layout adapter (ADR-002).

Translates the logical IR into ELK's JSON dialect, runs the pinned elkjs subprocess,
and translates the laid-out result back into a ``PositionedDiagram``. ELK JSON exists
ONLY inside this module — nothing it returns leaks ELK-shaped keys. Graph families
(flowchart / architecture / dependency) all route through here; sequence + swimlane
use their own layouters.
"""
from __future__ import annotations

import functools
import json
from pathlib import Path
from types import TracebackType

from tarseem.layout.elk._server import ElkServerProcess, vendored_bundle
from tarseem.measure import TextMeasurer
from tarseem.model.ir import (
    LogicalGraph,
    PositionedDiagram,
    PositionedEdge,
    PositionedNode,
)

__all__ = ["ElkLayout", "elk_available"]

# spec direction -> ELK flow direction
_DIRECTION = {"TB": "DOWN", "BT": "UP", "LR": "RIGHT", "RL": "LEFT"}

_BASE_OPTIONS = {
    "elk.algorithm": "layered",
    "elk.layered.spacing.nodeNodeBetweenLayers": "60",
    "elk.spacing.nodeNode": "40",
    "elk.layered.spacing.edgeNodeBetweenLayers": "30",
    "elk.edgeRouting": "ORTHOGONAL",
    "elk.layered.nodePlacement.strategy": "NETWORK_SIMPLEX",
}

_EDGE_LABEL_SIZE = 12.0


@functools.lru_cache(maxsize=1)
def _elkjs_version() -> str:
    pkg = vendored_bundle().parent.parent / "package.json"
    try:
        return json.loads(Path(pkg).read_text(encoding="utf-8")).get("version", "unknown")
    except OSError:
        return "unknown"


def elk_available() -> bool:
    """True when the vendored bundle is present (Node availability is checked on spawn)."""
    return vendored_bundle().exists()


class ElkLayout:
    """Context-managed ELK layouter. Spawns one Node subprocess for its lifetime."""

    def __init__(self, node: str = "node", measurer: TextMeasurer | None = None) -> None:
        self._node = node
        self._measurer = measurer or TextMeasurer()
        self._proc: ElkServerProcess | None = None

    # -- lifecycle ------------------------------------------------------------
    def __enter__(self) -> ElkLayout:
        self._proc = ElkServerProcess(node=self._node)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._proc is not None:
            self._proc.close()
            self._proc = None

    def capabilities(self) -> dict:
        """Machine-readable capability report (ADR-005): never silently drop features."""
        return {
            "engine": "elk",
            "elkjs_version": _elkjs_version(),
            "algorithms": ["layered"],
            "supports": {
                "orthogonal_edges": True,
                "edge_labels": True,
                "ports": True,
                "groups": False,  # nested containers land in a later phase
            },
        }

    # -- layout ---------------------------------------------------------------
    def layout(self, graph: LogicalGraph) -> PositionedDiagram:
        if self._proc is None:
            raise RuntimeError("ElkLayout must be used as a context manager")
        elk_graph = self._to_elk(graph)
        laid = self._proc.layout(elk_graph)
        return self._from_elk(graph, laid)

    # -- translation (ELK JSON confined here) ---------------------------------
    def _to_elk(self, graph: LogicalGraph) -> dict:
        children = []
        for n in graph.nodes:
            w = n.width if n.width is not None else 84.0
            h = n.height if n.height is not None else 44.0
            children.append({"id": n.id, "width": float(w), "height": float(h)})

        edges = []
        for e in graph.edges:
            elk_edge: dict = {"id": e.id, "sources": [e.source], "targets": [e.target]}
            if e.label and e.label.text:
                lw = self._measurer.width(e.label.text, _EDGE_LABEL_SIZE) + 12.0
                elk_edge["labels"] = [
                    {"id": f"{e.id}__lbl", "width": round(lw, 2), "height": 18.0}
                ]
            edges.append(elk_edge)

        direction = _DIRECTION.get(graph.direction, "DOWN")
        options = {**_BASE_OPTIONS, "elk.direction": direction}
        return {"id": "root", "layoutOptions": options, "children": children, "edges": edges}

    def _from_elk(self, graph: LogicalGraph, laid: dict) -> PositionedDiagram:
        nodes_by_id = {n.id: n for n in graph.nodes}
        placed_children = {c["id"]: c for c in laid.get("children", [])}

        nodes: list[PositionedNode] = []
        for nid, src in nodes_by_id.items():
            c = placed_children.get(nid, {})
            nodes.append(
                PositionedNode(
                    id=nid,
                    x=float(c.get("x", 0.0)),
                    y=float(c.get("y", 0.0)),
                    width=float(c.get("width", src.width or 84.0)),
                    height=float(c.get("height", src.height or 44.0)),
                    label=src.label,
                    shape=src.shape,
                    style=src.style,
                )
            )

        edges_by_id = {e.id: e for e in graph.edges}
        edges: list[PositionedEdge] = []
        for ce in laid.get("edges", []):
            logical_edge = edges_by_id.get(ce["id"])
            points = _edge_points(ce)
            label = logical_edge.label if logical_edge else None
            # elkjs reserves edge-label space but reports x/y=0, so place the label at
            # the geometric midpoint of the routed polyline (deterministic, spike-3 proven).
            label_xy = _polyline_midpoint(points) if label and label.text else None
            edges.append(
                PositionedEdge(
                    id=ce["id"],
                    points=tuple(points),
                    label=label,
                    label_xy=label_xy,
                    style=logical_edge.style if logical_edge else {},
                )
            )

        return PositionedDiagram(
            width=float(laid.get("width", 0.0)),
            height=float(laid.get("height", 0.0)),
            nodes=tuple(nodes),
            edges=tuple(edges),
            diagram_type=graph.diagram_type,
            direction=graph.direction,
            theme=graph.theme,
        )


def _edge_points(ce: dict) -> list[tuple[float, float]]:
    sections = ce.get("sections") or []
    if not sections:
        return [(0.0, 0.0), (0.0, 0.0)]
    pts: list[tuple[float, float]] = []
    for sec in sections:
        start = sec.get("startPoint", {})
        pts.append((float(start.get("x", 0.0)), float(start.get("y", 0.0))))
        for bp in sec.get("bendPoints", []) or []:
            pts.append((float(bp["x"]), float(bp["y"])))
        end = sec.get("endPoint", {})
        pts.append((float(end.get("x", 0.0)), float(end.get("y", 0.0))))
    return pts


def _polyline_midpoint(points: list[tuple[float, float]]) -> tuple[float, float]:
    """Point at half the cumulative length of an orthogonal polyline (true middle,
    not an endpoint), so an edge label sits centered along its actual route."""
    if len(points) < 2:
        return points[0] if points else (0.0, 0.0)
    segs = [(points[i], points[i + 1]) for i in range(len(points) - 1)]
    total = sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in segs)
    half = total / 2
    for a, b in segs:
        seg_len = abs(a[0] - b[0]) + abs(a[1] - b[1])
        if seg_len >= half:
            t = half / seg_len if seg_len else 0.0
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        half -= seg_len
    return points[len(points) // 2]
