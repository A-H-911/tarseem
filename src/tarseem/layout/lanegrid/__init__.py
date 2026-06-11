"""Lane-grid layouter for swimlanes (Phase-0 decision; A12 / FR-6).

Deterministic, pure-Python — NOT ELK. Phase-0 spike 3 showed ELK ``partitioning``
groups nodes along the FLOW axis (phases), not lanes, so swimlanes use this instead:
one step per column = its topological number; lanes are fixed rows. Routing is a
from-scratch orthogonal router that exploits the one-step-per-column property — vertical
segments stay in single-node columns, horizontals ride node-free row centers — so long
cross-lane edges and back-edges avoid nodes. Geometry constants ported from the
``horizontal-swimlane-diagram`` prior art (analysis.md §reference-1/3).
"""
from __future__ import annotations

from collections import defaultdict, deque

from tarseem.model.ir import (
    LaneBand,
    LogicalEdge,
    LogicalGraph,
    LogicalNode,
    Marker,
    PhaseBand,
    PositionedDiagram,
    PositionedEdge,
    PositionedNode,
)

__all__ = ["LaneGridLayout"]

# geometry (px) — ported from the skill's DEFAULT_LAYOUT (analysis.md prior art)
_M = 20.0
_TITLE_H = 50.0
_LABEL_W = 160.0
_LANE_H = 120.0
_STEP_W = 150.0
_STEP_H = 70.0
_COL_GAP = 40.0
_LABEL_GAP = 30.0
_MARKER = 36.0
_END_W = 80.0
_TRAIL = 80.0
_PHASE_H = 34.0  # phase header band height (FR-6.3); 0 when no phases declared
_MARKER_BLACK = "#000000"


def _topo_numbers(nodes: tuple[LogicalNode, ...], edges: tuple[LogicalEdge, ...]) -> dict[str, int]:
    """Column index per node = position in a stable topological order (1-based).

    Declared order breaks ties so output is deterministic; a cycle falls back to
    declared order."""
    declared = {n.id: i for i, n in enumerate(nodes)}
    indeg = {n.id: 0 for n in nodes}
    succ: dict[str, list[str]] = defaultdict(list)
    for e in edges:
        if e.source in indeg and e.target in indeg:
            succ[e.source].append(e.target)
            indeg[e.target] += 1
    queue = deque(sorted((nid for nid, d in indeg.items() if d == 0), key=lambda x: declared[x]))
    order: list[str] = []
    while queue:
        nid = queue.popleft()
        order.append(nid)
        for nb in sorted(succ[nid], key=lambda x: declared[x]):
            indeg[nb] -= 1
            if indeg[nb] == 0:
                queue.append(nb)
    if len(order) != len(nodes):  # cycle -> declared order
        order = [n.id for n in nodes]
    return {nid: i + 1 for i, nid in enumerate(order)}


class LaneGridLayout:
    """Places a swimlane LogicalGraph into a PositionedDiagram (LTR; RTL in Phase 4)."""

    def layout(self, graph: LogicalGraph) -> PositionedDiagram:
        lanes = graph.lanes
        lane_index = {lane.id: i for i, lane in enumerate(lanes)}
        nums = _topo_numbers(graph.nodes, graph.edges)
        n_cols = max(nums.values(), default=1)
        markers = graph.markers
        end_w = _END_W if markers else 0.0

        # per-column width = widest node (>= step), so long labels never clip
        col_width: dict[int, float] = {}
        node_w: dict[str, float] = {}
        for n in graph.nodes:
            w = max(_STEP_W, n.width or _STEP_W)
            node_w[n.id] = w
            col = nums[n.id]
            col_width[col] = max(col_width.get(col, _STEP_W), w)

        start_x = _M + _LABEL_W + _LABEL_GAP + end_w
        col_x: dict[int, float] = {}
        cursor = start_x
        for c in range(1, n_cols + 1):
            col_x[c] = cursor
            cursor += col_width.get(c, _STEP_W) + _COL_GAP
        inner_right = cursor - _COL_GAP
        total_w = inner_right + end_w + _TRAIL + _M
        phase_h = _PHASE_H if graph.phases else 0.0
        lanes_top = _M + _TITLE_H + phase_h
        total_h = lanes_top + len(lanes) * _LANE_H + _M

        bands = self._lane_bands(lanes, total_w, lanes_top)
        band_y = {lanes[i].id: lanes_top + i * _LANE_H for i in range(len(lanes))}

        nodes, geom = self._place_nodes(graph, nums, lane_index, col_x, col_width, node_w, band_y)
        edges = self._route_edges(graph.edges, geom)
        phase_bands = self._phase_bands(graph, nums, col_x, col_width)
        if markers:
            marker_objs, marker_edges = self._markers(graph, nums, geom, total_w)
            edges = edges + marker_edges
        else:
            marker_objs = ()

        return PositionedDiagram(
            width=total_w,
            height=total_h,
            nodes=tuple(nodes),
            edges=tuple(edges),
            diagram_type=graph.diagram_type,
            direction=graph.direction,
            title=graph.title,
            lanes=tuple(bands),
            phases=tuple(phase_bands),
            markers=tuple(marker_objs),
            theme=graph.theme,
        )

    # -- pieces ---------------------------------------------------------------
    def _lane_bands(self, lanes: tuple, total_w: float, lanes_top: float) -> list[LaneBand]:
        bands = []
        for i, lane in enumerate(lanes):
            bands.append(
                LaneBand(
                    id=lane.id,
                    label=lane.label,
                    x=_M,
                    y=lanes_top + i * _LANE_H,
                    width=total_w - 2 * _M,
                    height=_LANE_H,
                    hue=lane.hue,
                )
            )
        return bands

    def _phase_bands(self, graph, nums, col_x, col_width) -> list[PhaseBand]:
        """One header band per phase, tiling the column space contiguously: each band spans
        its member columns extended by half a column gap on each side, so adjacent phases
        meet exactly — no gap, no overlap (the column gap is shared 50/50 at the boundary).
        Assumes phases occupy contiguous column ranges (the documented MVP shape)."""
        cols_by_phase: dict[str, list[int]] = {}
        for n in graph.nodes:
            if n.phase:
                cols_by_phase.setdefault(n.phase, []).append(nums[n.id])
        half = _COL_GAP / 2
        bands: list[PhaseBand] = []
        for ph in sorted(graph.phases, key=lambda p: p.order):
            cols = cols_by_phase.get(ph.id)
            if not cols:
                continue
            first, last = min(cols), max(cols)
            left = col_x[first] - half
            right = col_x[last] + col_width[last] + half
            bands.append(
                PhaseBand(
                    id=ph.id, label=ph.label,
                    x=left, y=_M + _TITLE_H, width=right - left, height=_PHASE_H,
                )
            )
        return bands

    def _place_nodes(self, graph, nums, lane_index, col_x, col_width, node_w, band_y):
        hue_by_lane = {lane.id: lane.hue for lane in graph.lanes}
        nodes: list[PositionedNode] = []
        geom: dict[str, dict] = {}
        for n in graph.nodes:
            col = nums[n.id]
            w, h = node_w[n.id], _STEP_H
            lane_id = n.lane or ""
            hue = hue_by_lane.get(lane_id, {})
            x = col_x[col] + (col_width[col] - w) / 2
            y = band_y[lane_id] + (_LANE_H - h) / 2
            # lane hue paints the node: medium-tint fill, darker same-hue border
            style = {
                **n.style,
                "fill": hue.get("box", n.style.get("fill", "#FFFFFF")),
                "border": {"color": hue.get("label", "#333333"), "width": 2, "style": "solid"},
            }
            badge = f"{col}." if n.show_badge else None
            nodes.append(
                PositionedNode(
                    id=n.id, x=x, y=y, width=w, height=h,
                    label=n.label, shape=n.shape, style=style, badge=badge,
                )
            )
            geom[n.id] = {
                "x": x, "y": y, "w": w, "h": h,
                "lane_i": lane_index[lane_id], "hue": hue, "shape": n.shape,
            }
        return nodes, geom

    def _route_edges(self, edges: tuple, geom: dict) -> list[PositionedEdge]:
        out: list[PositionedEdge] = []
        for e in edges:
            a, b = geom.get(e.source), geom.get(e.target)
            if a is None or b is None:
                continue
            pts = _route(a, b)
            label_xy = _polyline_midpoint(pts) if e.label and e.label.text else None
            out.append(
                PositionedEdge(
                    id=e.id, points=tuple(pts), label=e.label,
                    label_xy=label_xy, style=e.style,
                )
            )
        return out

    def _markers(self, graph, nums, geom, total_w):
        first = min(nums, key=lambda k: nums[k])
        last = max(nums, key=lambda k: nums[k])
        fp, lp = geom[first], geom[last]
        r = _MARKER / 2
        sx = _M + _LABEL_W + _LABEL_GAP + (_END_W - _MARKER) / 2
        sy = fp["y"] + (_STEP_H - _MARKER) / 2
        ex = total_w - _M - _TRAIL - _END_W + (_END_W - _MARKER) / 2
        ey = lp["y"] + (_STEP_H - _MARKER) / 2
        start = Marker(kind="start", cx=sx + r, cy=sy + r, r=r)
        end = Marker(kind="end", cx=ex + r, cy=ey + r, r=r)
        black = {"stroke": _MARKER_BLACK, "width": 2}
        fp_cy = fp["y"] + _STEP_H / 2
        lp_cy = lp["y"] + _STEP_H / 2
        edges = [
            PositionedEdge(
                id="__marker_start__",
                points=((sx + _MARKER, sy + r), (_side_x(fp, "l", fp_cy), fp_cy)),
                label=None, label_xy=None, style=black,
            ),
            PositionedEdge(
                id="__marker_end__",
                points=((_side_x(lp, "r", lp_cy), lp_cy), (ex, ey + r)),
                label=None, label_xy=None, style=black,
            ),
        ]
        return (start, end), edges


_PARALLELOGRAM_SLANT = 20.0  # must match the renderer's parallelogram skew


def _anchors(g: dict) -> dict:
    x, y, w, h = g["x"], g["y"], g["w"], g["h"]
    return {"cx": x + w / 2, "cy": y + h / 2, "l": x, "r": x + w, "t": y, "b": y + h}


def _side_x(g: dict, side: str, y: float) -> float:
    """X where a horizontal edge at height ``y`` meets the node's actual side.

    Rect-like shapes use the bounding box; parallelograms are slanted, so the
    attach point is inset along the skew (otherwise the arrow stops short -> gap)."""
    left, right = g["x"], g["x"] + g["w"]
    if g.get("shape") == "parallelogram":
        frac = (y - g["y"]) / g["h"] if g["h"] else 0.0  # 0 at top, 1 at bottom
        frac = min(1.0, max(0.0, frac))
        if side == "l":
            return left + _PARALLELOGRAM_SLANT * (1 - frac)
        return right - _PARALLELOGRAM_SLANT * frac
    return left if side == "l" else right


def _route(a: dict, b: dict) -> list[tuple[float, float]]:
    """Orthogonal polyline exploiting one-step-per-column; attaches to real shape sides."""
    A, B = _anchors(a), _anchors(b)
    if a["lane_i"] == b["lane_i"]:  # same lane -> straight horizontal at center y
        cy = A["cy"]
        if B["cx"] > A["cx"]:
            return [(_side_x(a, "r", cy), cy), (_side_x(b, "l", cy), cy)]
        return [(_side_x(a, "l", cy), cy), (_side_x(b, "r", cy), cy)]
    exit_y = A["t"] if B["cy"] < A["cy"] else A["b"]  # top/bottom edges are flat -> bbox ok
    side = "l" if B["cx"] >= A["cx"] else "r"
    enter_x = _side_x(b, side, B["cy"])
    return [(A["cx"], exit_y), (A["cx"], B["cy"]), (enter_x, B["cy"])]


def _polyline_midpoint(points: list[tuple[float, float]]) -> tuple[float, float]:
    if len(points) < 2:
        return points[0] if points else (0.0, 0.0)
    segs = [(points[i], points[i + 1]) for i in range(len(points) - 1)]
    total = sum(abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in segs)
    half = total / 2
    for p, q in segs:
        seg = abs(p[0] - q[0]) + abs(p[1] - q[1])
        if seg >= half:
            t = half / seg if seg else 0.0
            return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)
        half -= seg
    return points[len(points) // 2]
