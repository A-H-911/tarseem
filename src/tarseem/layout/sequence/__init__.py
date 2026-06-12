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
        # activation spans are computed BEFORE routing so messages can attach to the bar edge
        # (not the lifeline centre) wherever a participant is active — otherwise arrows
        # penetrate the bar instead of touching its border.
        spans = self._activation_spans(graph, row_of, bottom_y)
        edges = self._route_messages(graph, lifeline_x, row_of, spans)
        activations = tuple(
            Activation(x=lifeline_x[pid] - _ACT_W / 2, y=y0, width=_ACT_W,
                       height=max(0.0, y1 - y0))
            for pid, y0, y1 in spans
        )

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

    def _route_messages(self, graph, lifeline_x, row_of, spans) -> list[PositionedEdge]:
        out: list[PositionedEdge] = []
        for e in graph.edges:
            y = row_of[e.id]
            sx = lifeline_x.get(e.source)
            tx = lifeline_x.get(e.target)
            if sx is None or tx is None:
                continue
            # offset endpoints to the activation-bar edge wherever a participant is active, on
            # the side facing the other end, so the message touches the bar instead of piercing
            # it. An inactive participant attaches to the lifeline centre as before.
            s_off = _ACT_W / 2 if _active_at(spans, e.source, y) else 0.0
            t_off = _ACT_W / 2 if _active_at(spans, e.target, y) else 0.0
            if e.source == e.target:  # self-message: bracket out to the right and back
                bx = sx + s_off  # leave from the right edge of the bar (the bracket side)
                pts: tuple[tuple[float, float], ...] = (
                    (bx, y),
                    (bx + _SELF_W, y),
                    (bx + _SELF_W, y + _SELF_DROP),
                    (bx, y + _SELF_DROP),
                )
                label_xy = (bx + _SELF_W + 6, y + _SELF_DROP / 2)
            else:
                if tx >= sx:  # rightward: leave source's right edge, enter target's left edge
                    sx, tx = sx + s_off, tx - t_off
                else:  # leftward
                    sx, tx = sx - s_off, tx + t_off
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

    def _activation_spans(self, graph, row_of, bottom_y) -> list[tuple[str, float, float]]:
        """Activation spans (participant, y0, y1) from call/return nesting: a sync call
        activates its target; a return deactivates its source. Unmatched activations close at
        the diagram bottom. The bars and the message edge-attachment both derive from these."""
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
        return spans


def _active_at(spans: list[tuple[str, float, float]], pid: str, y: float) -> bool:
    """True when participant ``pid`` is inside an activation bar at row ``y`` (inclusive of
    the bar's top/bottom edge, where calls and returns attach)."""
    return any(p == pid and y0 <= y <= y1 for p, y0, y1 in spans)
