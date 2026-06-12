"""Intermediate representation: logical (pre-layout) and positioned (post-layout).

One positioned IR feeds every writer (ADR-001). Writers never compute layout; they
consume a ``PositionedDiagram``. All IR types are frozen dataclasses — stages build
new instances rather than mutating, so the pipeline stays side-effect free.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

__all__ = [
    "Label",
    "EntityRow",
    "LogicalLane",
    "LogicalPhase",
    "LogicalNode",
    "LogicalEdge",
    "LogicalGraph",
    "LaneBand",
    "PhaseBand",
    "Marker",
    "Activation",
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
class EntityRow:
    """A row in an ER entity table (family: er). ``key`` is ``"PK"`` | ``"FK"`` | None.

    ``y_offset``/``height`` are the row's vertical geometry relative to the node's top edge,
    stamped once by the measurement stage so the table writer and the layout adapter (per-row
    edge anchoring) share one source of truth."""

    id: str
    label: Label
    key: str | None = None
    y_offset: float = 0.0
    height: float = 0.0


@dataclass(frozen=True)
class LogicalNode:
    id: str
    label: Label
    shape: str = "rect"
    kind: str | None = None
    lane: str | None = None  # swimlane membership
    phase: str | None = None  # swimlane phase-column membership (FR-6.3)
    show_badge: bool = True  # False = auto-number badge exempt (start/terminal pills)
    rows: tuple[EntityRow, ...] = ()  # ER entity attribute rows (family: er)
    style: dict = field(default_factory=dict)
    # manual placement (x, y) for respectManualPositions layouts; None = engine-placed (FR-5.x)
    position: tuple[float, float] | None = None
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
    # routing hints (Phase 5, FR-5.x; 06 §2). All defaults inert: an edge without hints
    # lays out exactly as before.
    priority: int | None = None  # layered straightness bias (higher = straighter)
    preferred_direction: str | None = None  # UP|DOWN|LEFT|RIGHT exit side for the edge
    waypoints: tuple[tuple[float, float], ...] = ()  # manual interior points (post-layout splice)
    source_port: str | None = None  # ER: attribute-row id to anchor the edge's start
    target_port: str | None = None  # ER: attribute-row id to anchor the edge's end


@dataclass(frozen=True)
class LogicalLane:
    id: str
    label: Label
    hue: dict = field(default_factory=dict)  # palette entry: row/box/label tints
    parent: str | None = None  # id of an enclosing lane group (nested lanes, best-effort AM-6)


@dataclass(frozen=True)
class LogicalPhase:
    """A phase groups one or more flow columns under a header band (FR-6.3)."""

    id: str
    label: Label
    order: float = 0.0


@dataclass(frozen=True)
class LogicalGraph:
    diagram_type: str
    direction: str = "TB"  # TB | BT | LR | RL
    nodes: tuple[LogicalNode, ...] = ()
    edges: tuple[LogicalEdge, ...] = ()
    lanes: tuple[LogicalLane, ...] = ()  # swimlane families only
    phases: tuple[LogicalPhase, ...] = ()  # swimlane phase columns (FR-6.3)
    title: str | None = None
    markers: bool = False  # UML start/end markers (swimlane)
    # swimlane lane axis: "horizontal" (lanes = rows, flow L->R) | "vertical" (lanes =
    # columns, flow top->bottom). FR-6.1. Vertical is a transpose of the horizontal layout.
    lane_orientation: str = "horizontal"
    layout_options: dict = field(default_factory=dict)  # spec `layout` hints (sidePadding…)
    respect_manual_positions: bool = False  # honour node.position via interactive placement
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
    rows: tuple[EntityRow, ...] = ()  # ER entity attribute rows, with stamped row geometry


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
class PhaseBand:
    """A phase header band spanning the columns of its member nodes (FR-6.3). Geometry
    only; positioned above the lane bands, with a separator drawn down through the lanes."""

    id: str
    label: Label
    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class Marker:
    kind: str  # "start" | "end"
    cx: float
    cy: float
    r: float


@dataclass(frozen=True)
class Activation:
    """Activation bar overlay for sequence diagrams: a thin rect on a lifeline marking
    the span where a participant is active (between a call and its return)."""

    x: float
    y: float
    width: float
    height: float


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
    orientation: str = "horizontal"  # swimlane lane axis (FR-6.1); "vertical" = transposed
    title: str | None = None
    lanes: tuple[LaneBand, ...] = ()  # swimlane band chrome
    lane_groups: tuple[LaneBand, ...] = ()  # nested-lane parent group bands (best-effort, AM-6)
    phases: tuple[PhaseBand, ...] = ()  # swimlane phase header bands (FR-6.3)
    markers: tuple[Marker, ...] = ()  # swimlane UML markers
    activations: tuple[Activation, ...] = ()  # sequence activation bars
    phase_separator: dict = field(default_factory=dict)  # resolved phase-separator style
    theme: dict = field(default_factory=dict)
