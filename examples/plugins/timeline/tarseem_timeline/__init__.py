"""timeline: a second example third-party Tarseem diagram type.

Where ``incident-flow`` only changed a cosmetic default, ``timeline`` exercises a *different*
extension point: a **custom layouter**. It supplies its own pure-Python ``layouter_factory`` —
events placed left-to-right on a single axis — instead of ELK, the same way the built-in
swimlane/sequence families do, but from outside the engine (no edits to ``src/tarseem``).

It honours ``direction: "RL"`` (events run right-to-left for Arabic/RTL), showing invariant 4
holds for externally-supplied layout. Rendering is inherited (the generic graph renderer).

Build/register exactly like any plugin (see docs/extending/clone-a-type.md):

    [project.entry-points."tarseem.types"]
    timeline = "tarseem_timeline:PLUGIN"
"""
from __future__ import annotations

from dataclasses import replace

from tarseem.model import PositionedDiagram, PositionedEdge, PositionedNode
from tarseem.plugins import DiagramTypePlugin

_GAP = 72.0  # horizontal space between consecutive events


class TimelineLayout:
    """One-shot layouter: lay measured nodes in a centred row, connect them along the axis.

    Consumes a measured ``LogicalGraph`` (node ``width``/``height`` already stamped) and returns
    a ``PositionedDiagram`` — the same contract ELK and the lane-grid layouter satisfy.
    """

    def layout(self, graph: object) -> PositionedDiagram:
        nodes = list(graph.nodes)  # type: ignore[attr-defined]
        max_h = max((n.height or 0.0) for n in nodes) if nodes else 0.0

        placed: dict[str, tuple[float, float, float, float]] = {}
        positioned: list[PositionedNode] = []
        cursor = 0.0
        for n in nodes:
            w, h = n.width or 0.0, n.height or 0.0
            y = (max_h - h) / 2.0  # vertical centre on the axis
            positioned.append(PositionedNode(
                id=n.id, x=cursor, y=y, width=w, height=h, label=n.label, shape=n.shape,
                style=n.style,
            ))
            placed[n.id] = (cursor, y, w, h)
            cursor += w + _GAP

        total_w = cursor - _GAP if nodes else 0.0
        total_h = max_h

        rtl = getattr(graph, "direction", "LR") == "RL"
        if rtl:  # mirror x so the first event sits on the right (invariant 4, geometry only)
            positioned = [replace(p, x=total_w - p.x - p.width) for p in positioned]
            placed = {p.id: (p.x, p.y, p.width, p.height) for p in positioned}

        edges: list[PositionedEdge] = []
        for e in graph.edges:  # type: ignore[attr-defined]
            if e.source not in placed or e.target not in placed:
                continue
            sx, sy, sw, sh = placed[e.source]
            tx, ty, tw, th = placed[e.target]
            if rtl:  # source's left edge -> target's right edge
                p0, p1 = (sx, sy + sh / 2.0), (tx + tw, ty + th / 2.0)
            else:  # source's right edge -> target's left edge
                p0, p1 = (sx + sw, sy + sh / 2.0), (tx, ty + th / 2.0)
            mid = ((p0[0] + p1[0]) / 2.0, (p0[1] + p1[1]) / 2.0 - 8.0)
            edges.append(PositionedEdge(
                id=e.id, points=(p0, p1), label=e.label,
                label_xy=mid if e.label else None, style=e.style,
            ))

        return PositionedDiagram(
            width=total_w, height=total_h, nodes=tuple(positioned), edges=tuple(edges),
            diagram_type=graph.diagram_type, direction=getattr(graph, "direction", "LR"),  # type: ignore[attr-defined]
            theme=graph.theme,  # type: ignore[attr-defined]
        )


PLUGIN = DiagramTypePlugin(
    type_id="timeline",
    default_shape="stadium",
    layouter_factory=TimelineLayout,
    layout_engine_name="timeline",
)
