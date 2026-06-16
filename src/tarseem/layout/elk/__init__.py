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

from tarseem.geometry import PARALLELOGRAM_SLANT as _PARALLELOGRAM_SLANT
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

# edge.preferredDirection -> the node side the edge exits from (probe-proven fixed-side port)
_PREFERRED_SIDE = {"UP": "NORTH", "DOWN": "SOUTH", "LEFT": "WEST", "RIGHT": "EAST"}

_BASE_OPTIONS = {
    "elk.algorithm": "layered",
    "elk.layered.spacing.nodeNodeBetweenLayers": "60",
    "elk.spacing.nodeNode": "40",
    "elk.layered.spacing.edgeNodeBetweenLayers": "30",
    "elk.edgeRouting": "ORTHOGONAL",
    "elk.layered.nodePlacement.strategy": "NETWORK_SIMPLEX",
}

# respectManualPositions: switch every layered phase to its INTERACTIVE variant so ELK
# derives layering/ordering/placement from the seeded node coordinates instead of from
# scratch. This preserves the manual *arrangement* (relative order on both axes); ELK still
# normalizes spacing, so it is a strong ordering hint, not exact-pixel pinning (probe-proven).
_INTERACTIVE_OPTIONS = {
    "elk.layered.layering.strategy": "INTERACTIVE",
    "elk.layered.crossingMinimization.strategy": "INTERACTIVE",
    "elk.layered.nodePlacement.strategy": "INTERACTIVE",
    "elk.layered.cycleBreaking.strategy": "INTERACTIVE",
}

# Mindmap layouters (spike-6). Non-layered trees; NOT the layered _BASE_OPTIONS (so an
# overlap is a real failure, not a layered-config artifact). mrtree = default (overlap-free on
# deep/uneven trees); radial = opt-in (root-centred, balanced maps only).
_MRTREE_OPTIONS = {
    "elk.algorithm": "mrtree",
    "elk.spacing.nodeNode": "40",
    "elk.mrtree.spacing.nodeNode": "40",
}
_RADIAL_OPTIONS = {
    "elk.algorithm": "radial",
    "elk.spacing.nodeNode": "40",
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
            "algorithms": ["layered", "mrtree", "radial"],
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
        diagram = self._from_elk(graph, laid)
        # ELK radial has no overlap removal; spread a deep/uneven map outward until clean (no-op
        # when nothing overlaps, so balanced radial maps are untouched). mrtree never overlaps.
        if (graph.diagram_type == "mindmap"
                and graph.layout_options.get("mindmapStyle") == "radial"):
            from tarseem.layout.radial import remove_radial_overlaps

            diagram = remove_radial_overlaps(diagram, graph)
        return diagram

    # -- translation (ELK JSON confined here) ---------------------------------
    def _to_elk(self, graph: LogicalGraph) -> dict:
        if graph.diagram_type == "mindmap":
            return self._to_elk_mindmap(graph)
        respect = graph.respect_manual_positions
        # Per-edge preferred exit side -> a dedicated fixed-side source port on that node.
        # Collect ports per node so the node can declare FIXED_SIDE port constraints.
        ports_by_node: dict[str, list[dict]] = {}
        edge_source_port: dict[str, str] = {}
        for e in graph.edges:
            side = _PREFERRED_SIDE.get((e.preferred_direction or "").upper())
            if side is not None:
                port_id = f"{e.id}__src@{side}"
                ports_by_node.setdefault(e.source, []).append(
                    {"id": port_id, "width": 4.0, "height": 4.0,
                     "layoutOptions": {"elk.port.side": side}}
                )
                edge_source_port[e.id] = port_id

        children = []
        for n in graph.nodes:
            w = n.width if n.width is not None else 84.0
            h = n.height if n.height is not None else 44.0
            child: dict = {"id": n.id, "width": float(w), "height": float(h)}
            if respect and n.position is not None:
                child["x"], child["y"] = float(n.position[0]), float(n.position[1])
            if n.id in ports_by_node:
                child["ports"] = ports_by_node[n.id]
                child["layoutOptions"] = {"elk.portConstraints": "FIXED_SIDE"}
            children.append(child)

        edges = []
        for e in graph.edges:
            source = edge_source_port.get(e.id, e.source)
            elk_edge: dict = {"id": e.id, "sources": [source], "targets": [e.target]}
            if e.label and e.label.text:
                lw = self._measurer.width(e.label.text, _EDGE_LABEL_SIZE) + 12.0
                elk_edge["labels"] = [
                    {"id": f"{e.id}__lbl", "width": round(lw, 2), "height": 18.0}
                ]
            # Higher priority -> ELK keeps this edge straighter through the layered placement.
            if e.priority is not None:
                elk_edge["layoutOptions"] = {
                    "elk.layered.priority.straightness": str(int(e.priority))
                }
            edges.append(elk_edge)

        direction = _DIRECTION.get(graph.direction, "DOWN")
        options = {**_BASE_OPTIONS, "elk.direction": direction}
        if respect:
            options = {**options, **_INTERACTIVE_OPTIONS}
        return {"id": "root", "layoutOptions": options, "children": children, "edges": edges}

    def _to_elk_mindmap(self, graph: LogicalGraph) -> dict:
        """Mindmap → a non-layered ELK tree (spike-6). ``layout.mindmapStyle`` selects ``mrtree``
        (default, overlap-free on deep trees) or ``radial`` (opt-in, balanced maps). Mindmap
        nodes are plain boxes, so this emits no ports / priority / INTERACTIVE machinery (all
        layered-only); ``_from_elk`` then consumes the result through the shared path."""
        style = str(graph.layout_options.get("mindmapStyle", "tree"))
        options = dict(_RADIAL_OPTIONS if style == "radial" else _MRTREE_OPTIONS)
        if style != "radial":  # radial is rotationally symmetric -> flow direction is meaningless
            options["elk.direction"] = _DIRECTION.get(graph.direction, "RIGHT")
        children = [
            {"id": n.id,
             "width": float(n.width if n.width is not None else 84.0),
             "height": float(n.height if n.height is not None else 44.0)}
            for n in graph.nodes
        ]
        edges = []
        for e in graph.edges:
            elk_edge: dict = {"id": e.id, "sources": [e.source], "targets": [e.target]}
            if e.label and e.label.text:
                lw = self._measurer.width(e.label.text, _EDGE_LABEL_SIZE) + 12.0
                elk_edge["labels"] = [
                    {"id": f"{e.id}__lbl", "width": round(lw, 2), "height": 18.0}
                ]
            edges.append(elk_edge)
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
                    rows=src.rows,  # ER entity rows (with stamped geometry) for the table writer
                    members=src.members,  # UML class member lines (stamped) for the class writer
                )
            )

        pos_by_id = {n.id: n for n in nodes}
        edges_by_id = {e.id: e for e in graph.edges}
        corridors = _ported_corridors(graph, pos_by_id)
        edges: list[PositionedEdge] = []
        for ce in laid.get("edges", []):
            logical_edge = edges_by_id.get(ce["id"])
            points = _edge_points(ce)
            # Manual waypoints (06 §2): splice the user's interior points over ELK's routed
            # polyline, keeping ELK's terminal points as the node attachments. Re-applied on
            # every render from the spec, so a re-render reproduces them exactly (round-trip).
            if logical_edge is not None and logical_edge.waypoints and len(points) >= 2:
                points = [points[0], *(p for p in logical_edge.waypoints), points[-1]]
            # ELK attaches edges to the node bounding box; snap the terminal points onto the
            # actual outline of non-rectangular shapes (diamond/parallelogram) so edges meet
            # the shape instead of leaving a gap where the bbox extends past the rhombus.
            if logical_edge is not None and len(points) >= 2:
                src_node = pos_by_id.get(logical_edge.source)
                tgt_node = pos_by_id.get(logical_edge.target)
                if src_node is not None:
                    points[0] = _snap_to_shape(points[0], points[1], src_node)
                if tgt_node is not None:
                    points[-1] = _snap_to_shape(points[-1], points[-2], tgt_node)
            # ER per-row anchoring: a ported edge attaches to a specific attribute row on each
            # entity, so replace ELK's box-to-box route with a clean orthogonal connector
            # between the two row anchors (on the facing sides). Entities are still placed +
            # spaced by ELK from the node-to-node edge; only the ported route is overridden.
            if logical_edge is not None and (logical_edge.source_port or logical_edge.target_port):
                src_node = pos_by_id.get(logical_edge.source)
                tgt_node = pos_by_id.get(logical_edge.target)
                if src_node is not None and tgt_node is not None:
                    count, index = corridors.get(ce["id"], (1, 0))
                    points = _row_connector(
                        src_node, logical_edge.source_port,
                        tgt_node, logical_edge.target_port,
                        count, index,
                    )
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


def _snap_to_shape(
    pt: tuple[float, float], adj: tuple[float, float], node: PositionedNode
) -> tuple[float, float]:
    """Move an edge endpoint from the node bbox onto the actual outline of an inscribed
    shape. ELK routes orthogonally, so the terminal segment ``pt``->``adj`` is axis-aligned;
    we project the bbox-boundary endpoint onto the diamond/parallelogram edge at the same
    coordinate. Rect-like shapes already attach correctly, so they are returned unchanged."""
    px, py = pt
    ax, ay = adj
    x, y, w, h = node.x, node.y, node.width, node.height
    cx, cy = x + w / 2, y + h / 2
    horizontal = abs(ay - py) <= abs(ax - px)  # terminal segment runs mostly horizontally

    if node.shape == "diamond":
        hw, hh = w / 2, h / 2
        if horizontal and hh:
            frac = 1.0 - min(1.0, abs(py - cy) / hh)
            return (cx + hw * frac if px >= cx else cx - hw * frac, py)
        if not horizontal and hw:
            frac = 1.0 - min(1.0, abs(px - cx) / hw)
            return (px, cy + hh * frac if py >= cy else cy - hh * frac)
    elif node.shape == "parallelogram" and horizontal and h:
        frac = min(1.0, max(0.0, (py - y) / h))  # 0 at top, 1 at bottom
        if px <= cx:  # left (slanted) side
            return (x + _PARALLELOGRAM_SLANT * (1.0 - frac), py)
        return (x + w - _PARALLELOGRAM_SLANT * frac, py)
    return pt


def _ported_corridors(
    graph: LogicalGraph, pos_by_id: dict[str, PositionedNode]
) -> dict[str, tuple[int, int]]:
    """Assign each ported edge a (count, index) within the set of connectors leaving the same
    entity on the same side (bug #1). Siblings are ordered by target-row height so their fanned
    corridors nest without overlapping; a lone connector keeps (1, 0) -> centred midpoint."""
    groups: dict[tuple[str, str], list[str]] = {}
    for e in graph.edges:
        if not (e.source_port or e.target_port):
            continue
        s, t = pos_by_id.get(e.source), pos_by_id.get(e.target)
        if s is None or t is None:
            continue
        side = "R" if (s.x + s.width / 2) <= (t.x + t.width / 2) else "L"
        groups.setdefault((e.source, side), []).append(e.id)
    out: dict[str, tuple[int, int]] = {}
    edges_by_id = {e.id: e for e in graph.edges}
    for ids in groups.values():
        ids.sort(key=lambda eid: _row_anchor(pos_by_id[edges_by_id[eid].target],
                                             edges_by_id[eid].target_port))
        for i, eid in enumerate(ids):
            out[eid] = (len(ids), i)
    return out


def _row_anchor(node: PositionedNode, port_id: str | None) -> float:
    """Vertical center of the attribute row named ``port_id`` (node center if unmatched)."""
    if port_id:
        for r in node.rows:
            if r.id == port_id:
                return node.y + r.y_offset + r.height / 2
    return node.y + node.height / 2


def _row_connector(
    src: PositionedNode, src_port: str | None,
    tgt: PositionedNode, tgt_port: str | None,
    count: int = 1, index: int = 0,
) -> list[tuple[float, float]]:
    """Orthogonal connector between two entity rows, attaching on the facing sides.

    The source exits the side that faces the target and the target is entered from the side
    facing the source. ``count``/``index`` fan out connectors that share a source side so
    their vertical corridors don't overlap (bug #1): the run meets at ``(index+1)/(count+1)``
    of the gap rather than always the midpoint, which keeps a single connector centred
    (1/2) while spreading siblings into distinct corridors."""
    sy = _row_anchor(src, src_port)
    ty = _row_anchor(tgt, tgt_port)
    src_cx, tgt_cx = src.x + src.width / 2, tgt.x + tgt.width / 2
    if src_cx <= tgt_cx:  # source on the left -> exit right, enter target's left
        sx, tx = src.x + src.width, tgt.x
    else:
        sx, tx = src.x, tgt.x + tgt.width
    mx = sx + (tx - sx) * (index + 1) / (count + 1)
    return [(sx, sy), (mx, sy), (mx, ty), (tx, ty)]


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
