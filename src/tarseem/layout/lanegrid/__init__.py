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
_GROUP_W = 34.0  # outer gutter width for a nested-lane parent group header (AM-6)
_MARKER_BLACK = "#000000"
_ROUTE_CORRIDOR = 16.0  # clearance below/above all nodes for back-edge detour channels
# Vertical orientation (lanes = columns, flow top->bottom; landscape node shapes kept). Lane
# columns are relaxed to the widest node + padding so shapes are NOT rotated (bug #7). _V_HEADER
# MUST match the swimlane renderer's vertical header constant.
_V_HEADER = 64.0  # lane header band (the actor/user area) at the top of each column
_V_COL_PAD = 28.0  # horizontal padding inside a lane column (relaxes the width)
_V_ROW_GAP = 60.0  # gap between flow rows
_V_END_H = 72.0  # gutter above/below the flow for UML start/end markers


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
        if graph.lane_orientation == "vertical":
            return self._vertical_layout(graph)  # lanes as columns, landscape shapes (bug #7)
        # nested lanes (best-effort, AM-6): a lane named as another lane's `parent` is a
        # group, not a flow row. Rows are the LEAF lanes; group bands are drawn as an outer
        # gutter in a post-pass. With no parents declared, every lane is a leaf -> unchanged.
        parent_ids = {lane.parent for lane in graph.lanes if lane.parent}
        lanes = tuple(lane for lane in graph.lanes if lane.id not in parent_ids)
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
        if parent_ids:
            return _with_lane_groups(diagram, graph)
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
        entry_y = _convergence_entries(edges, geom)
        valid = [e for e in edges if geom.get(e.source) and geom.get(e.target)]
        obstacles_for = {
            e.id: [box for nid, box in boxes_by_id.items() if nid not in (e.source, e.target)]
            for e in valid
        }
        routes = {
            e.id: _route(geom[e.source], geom[e.target],
                         obstacles_for[e.id], top_y, bot_y, entry_y.get(e.id))
            for e in valid
        }
        # bug #3: a long cross-lane edge's vertical segment can cross another edge's horizontal
        # one. Flip such an edge to the alternate L-orientation (run along its own row, then
        # descend in the target column) when that is clear of nodes AND of the other routed
        # edges. Only edges that actually cross are touched, so well-routed edges are unchanged.
        for e in valid:
            a, b = geom[e.source], geom[e.target]
            if a["lane_i"] == b["lane_i"] or not _route_crosses_other(routes[e.id], e.id, routes):
                continue
            alt = _route_alt(a, b, obstacles_for[e.id])
            if alt is not None and not _route_crosses_other(alt, e.id, routes):
                routes[e.id] = alt
        out: list[PositionedEdge] = []
        for e in valid:
            pts = routes[e.id]
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

    # -- vertical orientation (lanes = columns, flow top->bottom; bug #7) ------
    def _vertical_layout(self, graph: LogicalGraph) -> PositionedDiagram:
        """Lay swimlanes out vertically: lanes become side-by-side COLUMNS and the flow runs
        top->bottom, while node shapes keep their landscape size (NOT rotated). Lane columns
        are relaxed to the widest node + padding. Routing reuses the horizontal orthogonal
        router by feeding it axis-swapped geometry (flow->x, lanes->rows) and transposing the
        routed points back — so back-edge/cross-lane avoidance carries over unchanged."""
        lanes = graph.lanes
        lane_index = {lane.id: i for i, lane in enumerate(lanes)}
        nums = _topo_numbers(graph.nodes, graph.edges)
        n_rows = max(nums.values(), default=1)
        markers = graph.markers
        end_h = _V_END_H if markers else 0.0

        node_w = {n.id: max(_STEP_W, n.width or _STEP_W) for n in graph.nodes}
        lane_w: dict[str, float] = {}
        for n in graph.nodes:
            lane_w[n.lane or ""] = max(lane_w.get(n.lane or "", _STEP_W), node_w[n.id])
        col_w = {lane.id: lane_w.get(lane.id, _STEP_W) + 2 * _V_COL_PAD for lane in lanes}

        col_x: dict[str, float] = {}
        cursor = _M
        for lane in lanes:
            col_x[lane.id] = cursor
            cursor += col_w[lane.id]
        total_w = cursor + _M

        rows_top = _M + _TITLE_H + _V_HEADER + end_h
        row_pitch = _STEP_H + _V_ROW_GAP
        row_y = {r: rows_top + (r - 1) * row_pitch for r in range(1, n_rows + 1)}
        total_h = rows_top + (n_rows - 1) * row_pitch + _STEP_H + end_h + _M

        hue_by_lane = {lane.id: lane.hue for lane in lanes}
        nodes: list[PositionedNode] = []
        router_geom: dict[str, dict] = {}
        for n in graph.nodes:
            w, h = node_w[n.id], _STEP_H
            lane_id = n.lane or ""
            hue = hue_by_lane.get(lane_id, {})
            x = col_x[lane_id] + (col_w[lane_id] - w) / 2
            y = row_y[nums[n.id]]
            style = {
                **n.style,
                "fill": hue.get("box", n.style.get("fill", "#FFFFFF")),
                "border": {"color": hue.get("label", "#333333"), "width": 2, "style": "solid"},
            }
            badge = f"{nums[n.id]}." if n.show_badge else None
            nodes.append(PositionedNode(id=n.id, x=x, y=y, width=w, height=h, label=n.label,
                                        shape=n.shape, style=style, badge=badge))
            # router frame: flow along x (= vertical y), lane axis along y (= vertical x); swap
            # w/h so the box matches. lane_i indexes the router's "rows" (our columns).
            router_geom[n.id] = {"x": y, "y": x, "w": h, "h": w,
                                 "lane_i": lane_index[lane_id], "hue": hue, "shape": n.shape}

        edges = [
            replace(
                e,
                points=tuple((py, px) for px, py in e.points),
                label_xy=((e.label_xy[1], e.label_xy[0]) if e.label_xy else None),
            )
            for e in self._route_edges(graph.edges, router_geom)
        ]

        band_top = _M + _TITLE_H
        band_h = total_h - band_top - _M
        bands = [LaneBand(id=lane.id, label=lane.label, x=col_x[lane.id], y=band_top,
                          width=col_w[lane.id], height=band_h, hue=lane.hue) for lane in lanes]

        if markers:
            marker_objs, marker_edges = self._vertical_markers(nums, nodes, end_h)
            edges = edges + list(marker_edges)
        else:
            marker_objs = ()

        return PositionedDiagram(
            width=total_w, height=total_h, nodes=tuple(nodes), edges=tuple(edges),
            diagram_type=graph.diagram_type, direction=graph.direction, orientation="vertical",
            title=graph.title, lanes=tuple(bands), markers=tuple(marker_objs), theme=graph.theme,
        )

    def _vertical_markers(self, nums, nodes, end_h):
        """UML start/end markers in the flow-start (top) and flow-end (bottom) gutters."""
        by_id = {n.id: n for n in nodes}
        first = by_id[min(nums, key=lambda k: nums[k])]
        last = by_id[max(nums, key=lambda k: nums[k])]
        r = _MARKER / 2
        sx = first.x + first.width / 2
        ex = last.x + last.width / 2
        start = Marker(kind="start", cx=sx, cy=first.y - end_h / 2, r=r)
        end = Marker(kind="end", cx=ex, cy=last.y + last.height + end_h / 2, r=r)
        black = {"stroke": _MARKER_BLACK, "width": 2}
        edges = (
            PositionedEdge(id="__marker_start__",
                           points=((sx, start.cy + r), (sx, first.y)),
                           label=None, label_xy=None, style=black),
            PositionedEdge(id="__marker_end__",
                           points=((ex, last.y + last.height), (ex, end.cy - r)),
                           label=None, label_xy=None, style=black),
        )
        return (start, end), edges


def _with_lane_groups(d: PositionedDiagram, graph: LogicalGraph) -> PositionedDiagram:
    """Nested lanes (best-effort, AM-6): draw each parent group as an outer header gutter.

    The whole diagram is translated right by one gutter width and a group band is placed at
    the left, spanning the row-extent of its child lanes. One affine translate keeps the
    inner layout (and its baselines) intact; only the x-origin moves. Single level only —
    a group's children must be leaf lanes; deeper nesting is not drawn (documented limit).
    """
    g = _GROUP_W
    band_by_id = {b.id: b for b in d.lanes}
    children: dict[str, list[str]] = {}
    for lane in graph.lanes:  # preserve declaration order of children
        if lane.parent and lane.id in band_by_id:
            children.setdefault(lane.parent, []).append(lane.id)
    hue_by_id = {lane.id: lane.hue for lane in graph.lanes}
    label_by_id = {lane.id: lane.label for lane in graph.lanes}

    def sx_node(n: PositionedNode) -> PositionedNode:
        return replace(n, x=n.x + g)

    def sx_band(b: LaneBand) -> LaneBand:
        return replace(b, x=b.x + g, width=b.width)

    nodes = tuple(sx_node(n) for n in d.nodes)
    edges = tuple(
        replace(
            e,
            points=tuple((px + g, py) for px, py in e.points),
            label_xy=((e.label_xy[0] + g, e.label_xy[1]) if e.label_xy else None),
        )
        for e in d.edges
    )
    lanes = tuple(sx_band(b) for b in d.lanes)
    phases = tuple(replace(p, x=p.x + g) for p in d.phases)
    markers = tuple(replace(mk, cx=mk.cx + g) for mk in d.markers)

    groups: list[LaneBand] = []
    for parent_id, child_ids in children.items():
        kids = [band_by_id[c] for c in child_ids]
        top = min(k.y for k in kids)
        bottom = max(k.y + k.height for k in kids)
        groups.append(
            LaneBand(
                id=parent_id,
                label=label_by_id.get(parent_id, kids[0].label),
                x=_M,
                y=top,
                width=g,
                height=bottom - top,
                hue=hue_by_id.get(parent_id, {}),
            )
        )
    return replace(
        d,
        width=d.width + g,
        nodes=nodes,
        edges=edges,
        lanes=lanes,
        lane_groups=tuple(groups),
        phases=phases,
        markers=markers,
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


def _route_alt(a: dict, b: dict, obstacles: list | None) -> list[tuple[float, float]] | None:
    """Alternate L-orientation for a cross-lane edge: leave the source along ITS OWN row
    (horizontal first), then descend/ascend in the TARGET's column to enter the target from
    top/bottom. Returns None when this path is not clear of nodes. Used to dodge another edge
    that the default (source-column-first) orientation would cross (bug #3)."""
    A, B = _anchors(a), _anchors(b)
    exit_x = _side_x(a, "l", A["cy"]) if B["cx"] < A["cx"] else _side_x(a, "r", A["cy"])
    enter_y = B["b"] if A["cy"] > B["cy"] else B["t"]
    alt = [(exit_x, A["cy"]), (B["cx"], A["cy"]), (B["cx"], enter_y)]
    if not obstacles or _route_clear(alt, obstacles):
        return alt
    return None


def _route_crosses_other(route: list, eid: str, routes: dict[str, list]) -> bool:
    """True if a VERTICAL segment of ``route`` properly crosses a HORIZONTAL segment of any
    OTHER edge's route (interior crossing, endpoints excluded)."""
    eps = 1.0
    verts = [(p, q) for p, q in _pairs(route) if abs(p[0] - q[0]) < 1e-6]
    for oid, oroute in routes.items():
        if oid == eid:
            continue
        for ha, hb in _pairs(oroute):
            if abs(ha[1] - hb[1]) >= 1e-6:  # not horizontal
                continue
            hy = ha[1]
            hx0, hx1 = sorted((ha[0], hb[0]))
            for va, vb in verts:
                vx = va[0]
                vy0, vy1 = sorted((va[1], vb[1]))
                if hx0 + eps < vx < hx1 - eps and vy0 + eps < hy < vy1 - eps:
                    return True
    return False


def _pairs(points: list) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    return [(points[i], points[i + 1]) for i in range(len(points) - 1)]


def _convergence_entries(edges: tuple, geom: dict) -> dict[str, float]:
    """Distinct entry heights for cross-lane edges that converge on the same node side.

    Without this, every edge entering a node from (say) the left rides that node's centre row,
    so two of them overlap on the shared horizontal corridor (bug #5). Group cross-lane edges
    by (target, entry-side); for any group of two or more, spread their entry points evenly
    around the node's centre (clamped to the node height) in a deterministic source order."""
    groups: dict[tuple[str, str], list[tuple[str, float, float]]] = {}
    for e in edges:
        a, b = geom.get(e.source), geom.get(e.target)
        if a is None or b is None or a["lane_i"] == b["lane_i"]:
            continue  # only cross-lane edges enter a node from a side
        A, B = _anchors(a), _anchors(b)
        side = "l" if B["cx"] >= A["cx"] else "r"
        groups.setdefault((e.target, side), []).append((e.id, A["cy"], A["cx"]))
    out: dict[str, float] = {}
    for (tgt, _side), items in groups.items():
        if len(items) < 2:
            continue
        B = _anchors(geom[tgt])
        n = len(items)
        spacing = min(16.0, max(6.0, (B["b"] - B["t"] - 12.0) / n))
        items.sort(key=lambda t: (t[1], t[2]))  # by source centre y then x (deterministic)
        for k, (eid, _cy, _cx) in enumerate(items):
            out[eid] = B["cy"] + spacing * (k - (n - 1) / 2)
    return out


def _route(
    a: dict, b: dict, obstacles: list | None = None,
    top_y: float | None = None, bot_y: float | None = None,
    entry_y: float | None = None,
) -> list[tuple[float, float]]:
    """Orthogonal polyline exploiting one-step-per-column; attaches to real shape sides.

    The direct route is used whenever it is clear (so the common forward edge is unchanged).
    When it would cross an *intervening* node — a back-edge or long edge passing over a node
    in the target's lane — it detours through a node-free corridor below (then above) all
    nodes, leaving and re-entering the endpoints vertically (south-to-south / north-to-north)
    so the line never crosses a box. ``entry_y`` overrides the cross-lane entry height so
    multiple edges converging on one node side ride distinct corridors instead of one (bug #5).
    """
    A, B = _anchors(a), _anchors(b)
    if a["lane_i"] == b["lane_i"]:  # same lane -> straight horizontal at center y
        cy = A["cy"]
        if B["cx"] > A["cx"]:
            direct = [(_side_x(a, "r", cy), cy), (_side_x(b, "l", cy), cy)]
        else:
            direct = [(_side_x(a, "l", cy), cy), (_side_x(b, "r", cy), cy)]
    else:
        enter_y = B["cy"] if entry_y is None else entry_y
        exit_y = A["t"] if B["cy"] < A["cy"] else A["b"]  # top/bottom edges are flat -> bbox ok
        side = "l" if B["cx"] >= A["cx"] else "r"
        enter_x = _side_x(b, side, enter_y)
        direct = [(A["cx"], exit_y), (A["cx"], enter_y), (enter_x, enter_y)]

    if not obstacles or _route_clear(direct, obstacles):
        return direct
    # detour via a node-free corridor: exit/enter both shapes vertically (south, then north).
    # Try the NEAREST clear channel first — just below / just above the two endpoints — and
    # only fall back to the global bottom/top corridor when those are blocked. This keeps a
    # back-edge hugging its own rows instead of always diving to the bottom of the diagram
    # (bug #6): a long dive looks like the edge avoids an obstacle that isn't there.
    near_below = max(A["b"], B["b"]) + _ROUTE_CORRIDOR
    near_above = min(A["t"], B["t"]) - _ROUTE_CORRIDOR
    candidates = [
        (near_below, A["b"], B["b"]),
        (near_above, A["t"], B["t"]),
    ]
    if bot_y is not None:
        candidates.append((bot_y, A["b"], B["b"]))
    if top_y is not None:
        candidates.append((top_y, A["t"], B["t"]))
    for corridor_y, a_exit, b_enter in candidates:
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
