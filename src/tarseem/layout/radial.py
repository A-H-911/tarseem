"""Deterministic overlap removal for the mindmap ``radial`` style.

ELK ``radial`` places nodes on depth-rings with **no overlap removal**, so a branch much deeper
than its siblings collides with other nodes. This post-pass nudges each overlapping node *pair*
apart along its axis of least penetration, iterating until no boxes overlap. It moves only what
overlaps, so the layout stays **compact** (a global rescale would blow a 14-node map up ~8×) and
each node keeps roughly its radial position. A uniform expansion about the centroid is a final
*guarantee* if the local pass leaves any residue. Radial edges are straight spokes, re-derived
boundary-to-boundary afterwards.

Pure + deterministic (fixed pair order + iteration caps; no RNG / wall-clock). **No-op when
nothing overlaps**, so balanced maps stay exactly as ELK placed them (zero baseline churn).
"""
from __future__ import annotations

from dataclasses import replace

from tarseem.model.ir import LogicalGraph, PositionedDiagram, PositionedEdge

__all__ = ["remove_radial_overlaps"]

_GAP = 32.0         # breathing room between separated boxes — wide enough that the spoke + its
#                     9px arrowhead are clearly visible between adjacent chain nodes (was 6: too
#                     tight, the arrowhead had no room to show).
_MARGIN = 24.0      # diagram padding after re-origining
_MAX_ITERS = 400    # ample for a tree-sized mindmap; the loop exits early once stable
_EPS = 0.01         # nudge past exact contact so a separated pair stays separated
_MAX_SCALE = 64.0   # ceiling for the guarantee fallback


def _has_overlap(cx, cy, hw, hh, gap) -> bool:
    n = len(cx)
    for i in range(n):
        for j in range(i + 1, n):
            if (abs(cx[i] - cx[j]) < hw[i] + hw[j] + gap
                    and abs(cy[i] - cy[j]) < hh[i] + hh[j] + gap):
                return True
    return False


def _clip(cx: float, cy: float, hw: float, hh: float, tx: float, ty: float) -> tuple[float, float]:
    """Where the ray from box centre ``(cx,cy)`` toward ``(tx,ty)`` crosses the box edge."""
    dx, dy = tx - cx, ty - cy
    if not dx and not dy:
        return cx, cy
    sx = hw / abs(dx) if dx else float("inf")
    sy = hh / abs(dy) if dy else float("inf")
    s = min(sx, sy)
    return cx + dx * s, cy + dy * s


def remove_radial_overlaps(diagram: PositionedDiagram, graph: LogicalGraph) -> PositionedDiagram:
    """Separate overlapping radial nodes while keeping the map compact; no-op if already clean."""
    nodes = diagram.nodes
    n = len(nodes)
    if n < 2:
        return diagram
    cx = [nd.x + nd.width / 2.0 for nd in nodes]
    cy = [nd.y + nd.height / 2.0 for nd in nodes]
    hw = [nd.width / 2.0 for nd in nodes]
    hh = [nd.height / 2.0 for nd in nodes]
    if not _has_overlap(cx, cy, hw, hh, 0.0):
        return diagram  # nothing genuinely overlaps -> leave the layout as ELK placed it

    # local separation: push each overlapping pair apart along its least-penetration axis.
    for _ in range(_MAX_ITERS):
        moved = False
        for i in range(n):
            for j in range(i + 1, n):
                dx, dy = cx[j] - cx[i], cy[j] - cy[i]
                ox = hw[i] + hw[j] + _GAP - abs(dx)  # x-overlap incl. gap
                oy = hh[i] + hh[j] + _GAP - abs(dy)  # y-overlap incl. gap
                if ox > 0 and oy > 0:
                    moved = True
                    if ox <= oy:
                        push = ox / 2.0 + _EPS
                        s = 1.0 if dx >= 0 else -1.0
                        cx[i] -= s * push
                        cx[j] += s * push
                    else:
                        push = oy / 2.0 + _EPS
                        s = 1.0 if dy >= 0 else -1.0
                        cy[i] -= s * push
                        cy[j] += s * push
        if not moved:
            break

    # guarantee: if any residue remains, expand uniformly about the centroid until clean.
    if _has_overlap(cx, cy, hw, hh, 0.0):
        mx, my = sum(cx) / n, sum(cy) / n
        scale = 1.0
        while scale < _MAX_SCALE:
            scale *= 1.5
            ex = [mx + scale * (cx[i] - mx) for i in range(n)]
            ey = [my + scale * (cy[i] - my) for i in range(n)]
            if not _has_overlap(ex, ey, hw, hh, _GAP):
                cx, cy = ex, ey
                break

    # re-origin to a clean margin and rebuild nodes.
    shift_x = _MARGIN - min(cx[i] - hw[i] for i in range(n))
    shift_y = _MARGIN - min(cy[i] - hh[i] for i in range(n))
    new_nodes = []
    centre: dict[str, tuple[float, float]] = {}
    half: dict[str, tuple[float, float]] = {}
    for i, nd in enumerate(nodes):
        ncx, ncy = cx[i] + shift_x, cy[i] + shift_y
        new_nodes.append(replace(nd, x=ncx - hw[i], y=ncy - hh[i]))
        centre[nd.id] = (ncx, ncy)
        half[nd.id] = (hw[i], hh[i])

    # radial edges are spokes: re-derive boundary-to-boundary so they attach to the moved nodes
    # (the arrowhead then points along the true spoke direction).
    new_edges = []
    for e in graph.edges:
        if e.source not in centre or e.target not in centre:
            continue
        scx, scy = centre[e.source]
        tcx, tcy = centre[e.target]
        shw, shh = half[e.source]
        thw, thh = half[e.target]
        p0 = _clip(scx, scy, shw, shh, tcx, tcy)
        p1 = _clip(tcx, tcy, thw, thh, scx, scy)
        label = e.label
        label_xy = ((p0[0] + p1[0]) / 2.0, (p0[1] + p1[1]) / 2.0) if label and label.text else None
        new_edges.append(
            PositionedEdge(id=e.id, points=(p0, p1), label=label, label_xy=label_xy, style=e.style)
        )

    width = max(nd.x + nd.width for nd in new_nodes) + _MARGIN
    height = max(nd.y + nd.height for nd in new_nodes) + _MARGIN
    return PositionedDiagram(
        width=width, height=height, nodes=tuple(new_nodes), edges=tuple(new_edges),
        diagram_type=diagram.diagram_type, direction=diagram.direction, theme=diagram.theme,
    )
