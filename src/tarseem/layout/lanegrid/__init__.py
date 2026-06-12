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
    replace,
)

__all__ = ["LaneGridLayout"]

# geometry (px) — ported from the skill's DEFAULT_LAYOUT (analysis.md prior art)
_M = 20.0
_TITLE_H = 50.0
_LABEL_W = 160.0
_LANE_H = 120.0
_STEP_W = 150.0
_STEP_H = 70.0
_COL_GAP = 56.0  # horizontal gap between adjacent step columns
# Symmetric horizontal padding on BOTH content sides: between the actor/label separator and
# the first shape, and between the last shape and the lane's right border. A single fixed
# value keeps the left and right margins equal across every swimlane (they used to differ —
# a small label gap on the left, a large trailing margin on the right).
_SIDE_PAD = 24.0
_MARKER = 36.0
_END_W = 80.0
_PHASE_H = 34.0  # phase header band height (FR-6.3); 0 when no phases declared
_MARKER_BLACK = "#000000"
_ROUTE_CORRIDOR = 16.0  # clearance below/above all nodes for back-edge detour channels


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

        # geometry knobs: spec `layout` hints override the built-in defaults (per-diagram)
        opts = graph.layout_options
        side_pad = float(opts.get("sidePadding", _SIDE_PAD))
        col_gap = float(opts.get("columnGap", _COL_GAP))

        # per-column width = widest node (>= step), so long labels never clip
        col_width: dict[int, float] = {}
        node_w: dict[str, float] = {}
        for n in graph.nodes:
            w = max(_STEP_W, n.width or _STEP_W)
            node_w[n.id] = w
            col = nums[n.id]
            col_width[col] = max(col_width.get(col, _STEP_W), w)

        # RL = right-to-left mirroring (geometry only; theme/text invariant — analysis.md
        # §Reference-2). Total width is direction-independent; only column placement, the
        # header-column side, badge corner and markers flip.
        rtl = graph.direction == "RL"
        content_w = (
            sum(col_width.get(c, _STEP_W) for c in range(1, n_cols + 1))
            + col_gap * (n_cols - 1)
        )
        total_w = 2 * _M + _LABEL_W + 2 * side_pad + 2 * end_w + content_w
        col_x = self._column_x(n_cols, col_width, side_pad, end_w, col_gap, total_w, rtl)

        phase_h = _PHASE_H if graph.phases else 0.0
        lanes_top = _M + _TITLE_H + phase_h
        total_h = lanes_top + len(lanes) * _LANE_H + _M

        bands = self._lane_bands(lanes, total_w, lanes_top)
        band_y = {lanes[i].id: lanes_top + i * _LANE_H for i in range(len(lanes))}

        nodes, geom = self._place_nodes(graph, nums, lane_index, col_x, col_width, node_w, band_y)
        edges = self._route_edges(graph.edges, geom)
        # content area = the non-header side; the header column moves right under RTL
        content_left = _M if rtl else _M + _LABEL_W
        content_right = (total_w - _M - _LABEL_W) if rtl else total_w - _M
        phase_bands = self._phase_bands(
            graph, nums, col_x, col_width, content_left, content_right, col_gap, rtl
        )
        if markers:
            marker_objs, marker_edges = self._markers(graph, nums, geom, total_w, side_pad, rtl)
            edges = edges + marker_edges
        else:
            marker_objs = ()

        diagram = PositionedDiagram(
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
            phase_separator=dict(opts.get("phaseSeparator") or {}),
            theme=graph.theme,
        )
        if graph.lane_orientation == "vertical":
            return _to_vertical(diagram)
        return diagram

    # -- pieces ---------------------------------------------------------------
    def _column_x(
        self, n_cols, col_width, side_pad, end_w, col_gap, total_w, rtl
    ) -> dict[int, float]:
        """Left-edge x of each step column. LTR lays columns left->right from the header
        side; RTL lays them right->left so column 1 (first step) sits on the right and the
        flow proceeds leftward. The LTR branch reproduces the pre-Phase-4 positions exactly."""
        col_x: dict[int, float] = {}
        if rtl:
            cursor = total_w - _M - _LABEL_W - side_pad - end_w  # right edge of content
            for c in range(1, n_cols + 1):
                w = col_width.get(c, _STEP_W)
                col_x[c] = cursor - w
                cursor = col_x[c] - col_gap
        else:
            cursor = _M + _LABEL_W + side_pad + end_w
            for c in range(1, n_cols + 1):
                col_x[c] = cursor
                cursor += col_width.get(c, _STEP_W) + col_gap
        return col_x

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

    def _phase_bands(
        self, graph, nums, col_x, col_width, content_left, content_right, col_gap, rtl=False
    ) -> list[PhaseBand]:
        """One header band per phase, tiling the column space contiguously: internal phase
        boundaries fall at the column-gap midpoint (so adjacent phases meet exactly), while
        the OUTER edges are clamped to the content area — the first phase starts at the
        actor/label separator and the last phase ends at the lane border, so the bands and
        their separators never poke past the swimlane sides. Phases are ordered by flow, so
        under RTL the first phase (lowest column numbers) sits on the *right*. Assumes phases
        occupy contiguous column ranges (the documented MVP shape)."""
        cols_by_phase: dict[str, list[int]] = {}
        for n in graph.nodes:
            if n.phase:
                cols_by_phase.setdefault(n.phase, []).append(nums[n.id])
        ordered = [ph for ph in graph.phases if ph.id in cols_by_phase]
        ordered.sort(key=lambda ph: min(cols_by_phase[ph.id]))
        half = col_gap / 2
        last_i = len(ordered) - 1
        bands: list[PhaseBand] = []
        for i, ph in enumerate(ordered):
            cols = cols_by_phase[ph.id]
            first, last = min(cols), max(cols)  # by flow number
            if rtl:  # first(flow) is the right-most column on screen
                right = content_right if i == 0 else col_x[first] + col_width[first] + half
                left = content_left if i == last_i else col_x[last] - half
            else:
                left = content_left if i == 0 else col_x[first] - half
                right = content_right if i == last_i else col_x[last] + col_width[last] + half
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
        boxes_by_id = {
            nid: (g["x"], g["y"], g["x"] + g["w"], g["y"] + g["h"]) for nid, g in geom.items()
        }
        boxes = list(boxes_by_id.values())
        # node-free corridors just below/above every node, used to detour around obstacles
        bot_y = max((b[3] for b in boxes), default=0.0) + _ROUTE_CORRIDOR
        top_y = min((b[1] for b in boxes), default=0.0) - _ROUTE_CORRIDOR
        out: list[PositionedEdge] = []
        for e in edges:
            a, b = geom.get(e.source), geom.get(e.target)
            if a is None or b is None:
                continue
            obstacles = [box for nid, box in boxes_by_id.items() if nid not in (e.source, e.target)]
            pts = _route(a, b, obstacles, top_y, bot_y)
            label_xy = (
                _label_clear_xy(pts, e.label.text, boxes) if e.label and e.label.text else None
            )
            out.append(
                PositionedEdge(
                    id=e.id, points=tuple(pts), label=e.label,
                    label_xy=label_xy, style=e.style,
                )
            )
        return out

    def _markers(self, graph, nums, geom, total_w, side_pad, rtl=False):
        first = min(nums, key=lambda k: nums[k])
        last = max(nums, key=lambda k: nums[k])
        fp, lp = geom[first], geom[last]
        r = _MARKER / 2
        # start gutter is on the flow-start side (left for LTR, right for RTL); end gutter
        # mirrors it. Connectors attach to the node side that faces its marker.
        if rtl:
            sx = total_w - _M - _LABEL_W - side_pad - _END_W + (_END_W - _MARKER) / 2
            ex = _M + side_pad + (_END_W - _MARKER) / 2
            start_side, end_side = "r", "l"
        else:
            sx = _M + _LABEL_W + side_pad + (_END_W - _MARKER) / 2
            ex = total_w - _M - side_pad - _END_W + (_END_W - _MARKER) / 2
            start_side, end_side = "l", "r"
        sy = fp["y"] + (_STEP_H - _MARKER) / 2
        ey = lp["y"] + (_STEP_H - _MARKER) / 2
        start = Marker(kind="start", cx=sx + r, cy=sy + r, r=r)
        end = Marker(kind="end", cx=ex + r, cy=ey + r, r=r)
        black = {"stroke": _MARKER_BLACK, "width": 2}
        fp_cy = fp["y"] + _STEP_H / 2
        lp_cy = lp["y"] + _STEP_H / 2
        # marker edge that faces the node: right edge (sx+_MARKER) when the marker is to the
        # node's left, left edge (sx) when it is to the node's right.
        start_marker_x = sx if rtl else sx + _MARKER
        end_marker_x = ex + _MARKER if rtl else ex
        edges = [
            PositionedEdge(
                id="__marker_start__",
                points=((start_marker_x, sy + r), (_side_x(fp, start_side, fp_cy), fp_cy)),
                label=None, label_xy=None, style=black,
            ),
            PositionedEdge(
                id="__marker_end__",
                points=((_side_x(lp, end_side, lp_cy), lp_cy), (end_marker_x, ey + r)),
                label=None, label_xy=None, style=black,
            ),
        ]
        return (start, end), edges


def _to_vertical(d: PositionedDiagram) -> PositionedDiagram:
    """Transpose a horizontal lane-grid diagram into vertical lanes (FR-6.1).

    Lanes become columns and flow runs top->bottom. One affine map is applied to every
    coordinate — ``T(x, y) = (m + (y - lanes_top), vtop + (x - m))`` — with width<->height
    swapped for sized boxes (nodes, lane bands). Because edge routes and node boxes share
    the same map, arrowheads still meet borders exactly and the layout stays collision-free
    and deterministic; only the pixel frame flips.

    Documented limitations (AM-6): node boxes rotate to portrait aspect (a wide step becomes
    a tall one — fine for short labels), and phase header bands are not drawn in the vertical
    variant. The title bar stays a horizontal bar on top in both orientations.
    """
    m = _M
    lanes_top = d.lanes[0].y if d.lanes else m + _TITLE_H
    vtop = m + _TITLE_H  # vertical content sits under a fresh top title bar (no phase row)

    def pt(x: float, y: float) -> tuple[float, float]:
        return (m + (y - lanes_top), vtop + (x - m))

    def vnode(n: PositionedNode) -> PositionedNode:
        nx, ny = pt(n.x, n.y)
        # lane axis (was height) -> width; flow axis (was width) -> height
        return replace(n, x=nx, y=ny, width=n.height, height=n.width)

    def vband(b: LaneBand) -> LaneBand:
        nx, ny = pt(b.x, b.y)
        return replace(b, x=nx, y=ny, width=b.height, height=b.width)

    def vmarker(mk: Marker) -> Marker:
        cx, cy = pt(mk.cx, mk.cy)
        return replace(mk, cx=cx, cy=cy)

    nodes = tuple(vnode(n) for n in d.nodes)
    edges = tuple(
        replace(
            e,
            points=tuple(pt(px, py) for px, py in e.points),
            label_xy=(pt(*e.label_xy) if e.label_xy else None),
        )
        for e in d.edges
    )
    bands = tuple(vband(b) for b in d.lanes)
    markers = tuple(vmarker(mk) for mk in d.markers)

    rights = (
        [b.x + b.width for b in bands]
        + [n.x + n.width for n in nodes]
        + [px for e in edges for px, _ in e.points]
        + [mk.cx + mk.r for mk in markers]
    )
    bottoms = (
        [b.y + b.height for b in bands]
        + [n.y + n.height for n in nodes]
        + [py for e in edges for _, py in e.points]
        + [mk.cy + mk.r for mk in markers]
    )
    width = max(rights, default=m) + m
    height = max(bottoms, default=vtop) + m
    return replace(
        d,
        width=width,
        height=height,
        orientation="vertical",
        nodes=nodes,
        edges=edges,
        lanes=bands,
        markers=markers,
        phases=(),  # phase bands are a horizontal-only feature (documented limitation)
    )


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


def _seg_clear(p: tuple, q: tuple, boxes: list) -> bool:
    """True if the axis-aligned segment ``p``-``q`` passes through no box interior."""
    eps = 0.5
    if abs(p[1] - q[1]) < 1e-6:  # horizontal
        y = p[1]
        lo, hi = sorted((p[0], q[0]))
        return not any(
            (y0 + eps < y < y1 - eps) and (x0 < hi - eps) and (x1 > lo + eps)
            for x0, y0, x1, y1 in boxes
        )
    x = p[0]  # vertical
    lo, hi = sorted((p[1], q[1]))
    return not any(
        (x0 + eps < x < x1 - eps) and (y0 < hi - eps) and (y1 > lo + eps)
        for x0, y0, x1, y1 in boxes
    )


def _route_clear(points: list, boxes: list) -> bool:
    return all(_seg_clear(points[i], points[i + 1], boxes) for i in range(len(points) - 1))


def _route(
    a: dict, b: dict, obstacles: list | None = None,
    top_y: float | None = None, bot_y: float | None = None,
) -> list[tuple[float, float]]:
    """Orthogonal polyline exploiting one-step-per-column; attaches to real shape sides.

    The direct route is used whenever it is clear (so the common forward edge is unchanged).
    When it would cross an *intervening* node — a back-edge or long edge passing over a node
    in the target's lane — it detours through a node-free corridor below (then above) all
    nodes, leaving and re-entering the endpoints vertically (south-to-south / north-to-north)
    so the line never crosses a box."""
    A, B = _anchors(a), _anchors(b)
    if a["lane_i"] == b["lane_i"]:  # same lane -> straight horizontal at center y
        cy = A["cy"]
        if B["cx"] > A["cx"]:
            direct = [(_side_x(a, "r", cy), cy), (_side_x(b, "l", cy), cy)]
        else:
            direct = [(_side_x(a, "l", cy), cy), (_side_x(b, "r", cy), cy)]
    else:
        exit_y = A["t"] if B["cy"] < A["cy"] else A["b"]  # top/bottom edges are flat -> bbox ok
        side = "l" if B["cx"] >= A["cx"] else "r"
        enter_x = _side_x(b, side, B["cy"])
        direct = [(A["cx"], exit_y), (A["cx"], B["cy"]), (enter_x, B["cy"])]

    if not obstacles or _route_clear(direct, obstacles):
        return direct
    # detour via a node-free corridor: exit/enter both shapes vertically (south, then north)
    for corridor_y, a_exit, b_enter in (
        (bot_y, A["b"], B["b"]),
        (top_y, A["t"], B["t"]),
    ):
        if corridor_y is None:
            continue
        detour = [
            (A["cx"], a_exit), (A["cx"], corridor_y),
            (B["cx"], corridor_y), (B["cx"], b_enter),
        ]
        if _route_clear(detour, obstacles):
            return detour
    return direct


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


# Edge-label background dimensions — MUST match the swimlane renderer's `_edge_svg`
# (half = max(10, len*3.6); rect height 18 => half-height 9), so the layout-time clearance
# check matches the box actually drawn.
_LABEL_HALF_H = 9.0
_LABEL_CLEAR_MARGIN = 2.0
_LABEL_SAMPLES = 80


def _label_half_w(text: str) -> float:
    return max(10.0, len(text) * 3.6)


def _rect_clear(cx: float, cy: float, hw: float, hh: float, boxes: list) -> bool:
    m = _LABEL_CLEAR_MARGIN
    for x0, y0, x1, y1 in boxes:
        if cx + hw + m > x0 and cx - hw - m < x1 and cy + hh + m > y0 and cy - hh - m < y1:
            return False
    return True


def _point_at(points: list[tuple[float, float]], arclen: float) -> tuple[float, float]:
    for i in range(len(points) - 1):
        p, q = points[i], points[i + 1]
        seg = abs(p[0] - q[0]) + abs(p[1] - q[1])
        if arclen <= seg or i == len(points) - 2:
            t = arclen / seg if seg else 0.0
            return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)
        arclen -= seg
    return points[-1]


def _label_clear_xy(
    points: list[tuple[float, float]], text: str, boxes: list
) -> tuple[float, float]:
    """Place an edge label at the polyline point nearest the midpoint whose background box
    clears every node. The midpoint is used unchanged when it is already clear, so labels
    that never overlapped keep their exact position (no baseline churn); only labels that
    sat on a node — e.g. a back-edge crossing an intervening same-lane node — get nudged
    along the edge to a readable spot."""
    mid = _polyline_midpoint(points)
    hw = _label_half_w(text)
    if len(points) < 2 or _rect_clear(mid[0], mid[1], hw, _LABEL_HALF_H, boxes):
        return mid
    segs = [(points[i], points[i + 1]) for i in range(len(points) - 1)]
    total = sum(abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in segs)
    if total <= 0:
        return mid
    half = total / 2
    best: tuple[float, float] | None = None
    best_d: float | None = None
    for k in range(_LABEL_SAMPLES + 1):
        al = total * k / _LABEL_SAMPLES
        x, y = _point_at(points, al)
        if _rect_clear(x, y, hw, _LABEL_HALF_H, boxes):
            d = abs(al - half)
            if best_d is None or d < best_d:
                best, best_d = (x, y), d
    return best or mid
