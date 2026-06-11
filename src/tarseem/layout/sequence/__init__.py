"""Deterministic sequence-diagram layouter (A10 / 06 §layout).

Graph engines are the wrong tool for sequence diagrams (R-12): there is no force/flow to
optimise, only a fixed grammar — lifelines are ordered columns, messages are time-ordered
rows, activation bars are overlays. So this is pure Python, fully deterministic: declared
participant order fixes columns, declared message order fixes rows, and activation bars
fall out of call/return nesting. It reuses the one positioned IR (ADR-001): heads -> nodes,
messages -> edges (``style.style == "dashed"`` marks a return), activation bars -> the
``activations`` overlay; the writer draws lifeline stems from each head.
"""
from __future__ import annotations

from tarseem.model.ir import (
    Activation,
    LogicalGraph,
    PositionedDiagram,
    PositionedEdge,
    PositionedNode,
)

__all__ = ["SequenceLayout"]

# geometry (px)
_M = 24.0
_TITLE_H = 32.0
_HEAD_H = 42.0
_HEAD_MIN_W = 90.0
_COL_GAP = 130.0  # space between adjacent lifelines (room for message labels)
_ROW_GAP0 = 36.0  # gap below the head row before the first message
_ROW_H = 46.0  # vertical pitch between messages
_ACT_W = 10.0  # activation-bar width
_SELF_W = 44.0  # self-message bracket reach
_SELF_DROP = 20.0  # self-message bracket height


def _is_return(edge) -> bool:
    return edge.style.get("style") == "dashed"


class SequenceLayout:
    """Lay out a sequence ``LogicalGraph`` into the shared ``PositionedDiagram``."""

    def layout(self, graph: LogicalGraph) -> PositionedDiagram:
        title_h = _TITLE_H if graph.title else 0.0
        head_y = _M + title_h

        # participant columns, left -> right in declared order
        heads: list[PositionedNode] = []
        lifeline_x: dict[str, float] = {}
        cursor = _M
        for n in graph.nodes:
            w = max(_HEAD_MIN_W, n.width or _HEAD_MIN_W)
            x = cursor
            lifeline_x[n.id] = x + w / 2
            heads.append(
                PositionedNode(
                    id=n.id, x=x, y=head_y, width=w, height=_HEAD_H,
                    label=n.label, shape="rect",
                    style={"fill": "#EAF2EF", "border": {"color": "#2E8B57", "width": 2}},
                )
            )
            cursor = x + w + _COL_GAP

        total_w = (cursor - _COL_GAP) + _M if graph.nodes else 2 * _M
        first_row = head_y + _HEAD_H + _ROW_GAP0
        n_msgs = len(graph.edges)
        bottom_y = first_row + max(n_msgs, 1) * _ROW_H
        total_h = bottom_y + _M

        row_of = {e.id: first_row + i * _ROW_H for i, e in enumerate(graph.edges)}
        edges = self._route_messages(graph, lifeline_x, row_of)
        activations = self._activations(graph, lifeline_x, row_of, bottom_y)

        return PositionedDiagram(
            width=total_w,
            height=total_h,
            nodes=tuple(heads),
            edges=tuple(edges),
            diagram_type=graph.diagram_type,
            direction=graph.direction,
            title=graph.title,
            activations=tuple(activations),
            theme=graph.theme,
        )

    def _route_messages(self, graph, lifeline_x, row_of) -> list[PositionedEdge]:
        out: list[PositionedEdge] = []
        for e in graph.edges:
            y = row_of[e.id]
            sx = lifeline_x.get(e.source)
            tx = lifeline_x.get(e.target)
            if sx is None or tx is None:
                continue
            if e.source == e.target:  # self-message: bracket out to the right and back
                pts: tuple[tuple[float, float], ...] = (
                    (sx, y),
                    (sx + _SELF_W, y),
                    (sx + _SELF_W, y + _SELF_DROP),
                    (sx, y + _SELF_DROP),
                )
                label_xy = (sx + _SELF_W + 6, y + _SELF_DROP / 2)
            else:
                pts = ((sx, y), (tx, y))
                label_xy = ((sx + tx) / 2, y - 6)
            out.append(
                PositionedEdge(
                    id=e.id, points=pts, label=e.label,
                    label_xy=label_xy if e.label and e.label.text else None,
                    style=e.style,
                )
            )
        return out

    def _activations(self, graph, lifeline_x, row_of, bottom_y) -> list[Activation]:
        """Activation bars from call/return nesting: a sync call activates its target; a
        return deactivates its source. Unmatched activations close at the diagram bottom."""
        open_starts: dict[str, list[float]] = {}
        spans: list[tuple[str, float, float]] = []
        for e in graph.edges:
            y = row_of[e.id]
            if e.source == e.target:
                continue  # self-messages do not open/close activations in the MVP
            if _is_return(e):
                stack = open_starts.get(e.source)
                if stack:
                    spans.append((e.source, stack.pop(), y))
            else:
                open_starts.setdefault(e.target, []).append(y)
        for pid, stack in open_starts.items():
            for start in stack:
                spans.append((pid, start, bottom_y))
        bars: list[Activation] = []
        for pid, y0, y1 in spans:
            x = lifeline_x[pid] - _ACT_W / 2
            bars.append(Activation(x=x, y=y0, width=_ACT_W, height=max(0.0, y1 - y0)))
        return bars
