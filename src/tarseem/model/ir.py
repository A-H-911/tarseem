"""Intermediate representation: logical (pre-layout) and positioned (post-layout).

One positioned IR feeds every writer (ADR-001). Writers never compute layout; they
consume a ``PositionedDiagram``. All IR types are frozen dataclasses — stages build
new instances rather than mutating, so the pipeline stays side-effect free.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

__all__ = [
    "Label",
    "LogicalLane",
    "LogicalNode",
    "LogicalEdge",
    "LogicalGraph",
    "LaneBand",
    "Marker",
    "PositionedNode",
    "PositionedEdge",
    "PositionedDiagram",
    "replace",
]


@dataclass(frozen=True)
class Label:
    """A text label. Never a bare string in the IR (05 §3): direction/lang ride along
    so RTL writers can set ``direction``/``xml:lang`` per label without re-detecting."""

    text: str
    lang: str | None = None
    direction: str | None = None  # "ltr" | "rtl" | None (auto at render)


@dataclass(frozen=True)
class LogicalNode:
    id: str
    label: Label
    shape: str = "rect"
    kind: str | None = None
    lane: str | None = None  # swimlane membership
    show_badge: bool = True  # False = auto-number badge exempt (start/terminal pills)
    style: dict = field(default_factory=dict)
    # sizes are None until the measurement stage fills them (measure-before-layout)
    width: float | None = None
    height: float | None = None


@dataclass(frozen=True)
class LogicalEdge:
    id: str
    source: str
    target: str
    label: Label | None = None
    style: dict = field(default_factory=dict)


@dataclass(frozen=True)
class LogicalLane:
    id: str
    label: Label
    hue: dict = field(default_factory=dict)  # palette entry: row/box/label tints


@dataclass(frozen=True)
class LogicalGraph:
    diagram_type: str
    direction: str = "TB"  # TB | BT | LR | RL
    nodes: tuple[LogicalNode, ...] = ()
    edges: tuple[LogicalEdge, ...] = ()
    lanes: tuple[LogicalLane, ...] = ()  # swimlane families only
    title: str | None = None
    markers: bool = False  # UML start/end markers (swimlane)
    theme: dict = field(default_factory=dict)


@dataclass(frozen=True)
class PositionedNode:
    id: str
    x: float
    y: float
    width: float
    height: float
    label: Label
    shape: str
    style: dict = field(default_factory=dict)
    badge: str | None = None  # auto-number badge text (e.g. "2."); None = exempt


@dataclass(frozen=True)
class LaneBand:
    id: str
    label: Label
    x: float
    y: float
    width: float
    height: float
    hue: dict  # palette entry: row/box/label tints


@dataclass(frozen=True)
class Marker:
    kind: str  # "start" | "end"
    cx: float
    cy: float
    r: float


@dataclass(frozen=True)
class PositionedEdge:
    id: str
    points: tuple[tuple[float, float], ...]  # routed orthogonal polyline
    label: Label | None = None
    label_xy: tuple[float, float] | None = None
    style: dict = field(default_factory=dict)


@dataclass(frozen=True)
class PositionedDiagram:
    width: float
    height: float
    nodes: tuple[PositionedNode, ...]
    edges: tuple[PositionedEdge, ...]
    diagram_type: str
    direction: str = "TB"
    title: str | None = None
    lanes: tuple[LaneBand, ...] = ()  # swimlane band chrome
    markers: tuple[Marker, ...] = ()  # swimlane UML markers
    theme: dict = field(default_factory=dict)
