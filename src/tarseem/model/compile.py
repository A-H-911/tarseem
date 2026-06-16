"""Compile a validated spec into the logical IR (ADR-001, FR-5.4).

Style resolution happens here (via the A5 cascade) so downstream stages — measurement,
layout, writers — receive nodes/edges with already-resolved style dicts. Pure: never
mutates the input spec.
"""
from __future__ import annotations

from tarseem.model.ir import (
    ClassMember,
    EntityRow,
    Label,
    LogicalEdge,
    LogicalGraph,
    LogicalLane,
    LogicalNode,
    LogicalPhase,
)
from tarseem.themes import LANE_PALETTE, get_theme
from tarseem.themes.cascade import resolve_edge_style, resolve_node_style

__all__ = ["compile_spec"]

# Per-family default node shape when a node omits ``shape``.
_DEFAULT_SHAPE: dict[str, str] = {
    "flowchart": "roundrect",
    "architecture": "rect",
    "dependency": "rect",
    "swimlane": "roundrect",
    "sequence": "rect",  # participant head boxes
    "state": "roundrect",  # states are rounded boxes; initial/final use marker shapes
    "deployment": "cube",  # deployment nodes are 3D boxes (devices/containers)
    "er": "table",  # ER entities render as attribute tables
    "class": "class",  # UML class boxes render as name/attribute/method compartments
}


def _label(raw: dict | None) -> Label | None:
    if not raw:
        return None
    return Label(
        text=str(raw.get("text", "")),
        lang=raw.get("lang"),
        direction=raw.get("direction"),
    )


def _position(raw: dict | None) -> tuple[float, float] | None:
    """Manual node placement (x, y) -> tuple, or None when unset."""
    if not raw:
        return None
    return (float(raw["x"]), float(raw["y"]))


def _waypoints(routing: dict | None) -> tuple[tuple[float, float], ...]:
    """Manual interior points from ``edge.routing.waypoints`` -> tuple of (x, y)."""
    pts = (routing or {}).get("waypoints") or []
    return tuple((float(p[0]), float(p[1])) for p in pts)


def _rows(raw: dict) -> tuple[EntityRow, ...]:
    """ER entity attribute rows from a node's ``attributes`` (geometry stamped at measure)."""
    out: list[EntityRow] = []
    for attr in raw.get("attributes") or []:
        label = _label(attr.get("label")) or Label(text=str(attr.get("id", "")))
        out.append(EntityRow(id=attr["id"], label=label, key=attr.get("key")))
    return tuple(out)


def _members(raw: dict) -> tuple[ClassMember, ...]:
    """UML class member lines from a node's ``attributes`` + ``methods`` (geometry stamped at
    measure). Each item is a plain string (the member text) or a ``{label: {...}}`` / ``{text}``
    dict. The two groups render as separate compartments with a divider between them."""
    out: list[ClassMember] = []
    for group, key in (("attr", "attributes"), ("method", "methods")):
        for i, item in enumerate(raw.get(key) or []):
            if isinstance(item, str):
                label: Label = Label(text=item)
            else:
                label = _label(item.get("label")) or Label(text=str(item.get("text", "")))
            out.append(ClassMember(id=f"{group}{i}", label=label, group=group))
    return tuple(out)


def compile_spec(spec: dict, theme: dict | None = None) -> LogicalGraph:
    """Build the logical IR from a validated spec. Run :func:`tarseem.validation.validate`
    first; this assumes structural/referential integrity."""
    theme_ref = spec.get("theme") or {}
    # accept either `theme.ref` (schema-preferred) or `theme.name`; ref wins
    theme = theme or get_theme(theme_ref.get("ref") or theme_ref.get("name"))
    # carry presentation-only theme keys the renderers read off diagram.theme.
    for key in ("badgeCorner", "edgeCorners", "entityCorners", "nodeCorners"):
        if theme_ref.get(key) is not None:
            theme = {**theme, key: theme_ref[key]}
    diagram_type = spec.get("diagramType", "flowchart")
    default_shape = _DEFAULT_SHAPE.get(diagram_type, "rect")
    # Rounded rectangle corners are the default across all node shapes (owner directive); opt out
    # globally with theme.nodeCorners="sharp". Mapping rect->roundrect here means every writer
    # renders the rounded shape with no per-writer change (one positioned IR, many writers).
    node_corners = str(theme_ref.get("nodeCorners") or "rounded")
    # class nodes use `attributes`/`methods` as UML compartment members, not ER attribute rows.
    is_class = diagram_type == "class"

    nodes: list[LogicalNode] = []
    for raw in spec.get("nodes", []) or []:
        label = _label(raw.get("label")) or Label(text=str(raw.get("id", "")))
        shape = raw.get("shape", default_shape)
        if node_corners == "rounded" and shape == "rect":
            shape = "roundrect"
        nodes.append(
            LogicalNode(
                id=raw["id"],
                label=label,
                shape=shape,
                kind=raw.get("kind"),
                lane=raw.get("lane"),
                phase=raw.get("phase"),
                show_badge=bool(raw.get("badge", True)),
                rows=() if is_class else _rows(raw),
                members=_members(raw) if is_class else (),
                style=resolve_node_style(spec, raw, theme),
                position=_position(raw.get("position")),
            )
        )

    edges: list[LogicalEdge] = []
    for raw in spec.get("edges", []) or []:
        style = resolve_edge_style(spec, raw, theme)
        if raw.get("dashed"):
            style = {**style, "style": "dashed"}
        priority = raw.get("priority")
        edges.append(
            LogicalEdge(
                id=raw.get("id", f"{raw['source']}->{raw['target']}"),
                source=raw["source"],
                target=raw["target"],
                label=_label(raw.get("label")),
                style=style,
                priority=int(priority) if priority is not None else None,
                preferred_direction=raw.get("preferredDirection"),
                waypoints=_waypoints(raw.get("routing")),
                source_port=raw.get("sourcePort"),
                target_port=raw.get("targetPort"),
            )
        )

    # lane hues come from the *resolved theme's* palette, so swapping themes swaps the
    # swimlane palette over identical geometry (F4). default theme's palette IS the global,
    # so default output is unchanged.
    lane_palette = theme.get("lanePalette") or LANE_PALETTE
    lanes: list[LogicalLane] = []
    for i, raw in enumerate(spec.get("lanes", []) or []):
        hue = lane_palette[i % len(lane_palette)]
        label = _label(raw.get("label")) or Label(text=str(raw.get("id", "")))
        lanes.append(LogicalLane(id=raw["id"], label=label, hue=hue, parent=raw.get("parent")))

    phases: list[LogicalPhase] = []
    for i, raw in enumerate(spec.get("phases", []) or []):
        label = _label(raw.get("label")) or Label(text=str(raw.get("id", "")))
        phases.append(LogicalPhase(id=raw["id"], label=label, order=float(raw.get("order", i))))

    title = (spec.get("meta") or {}).get("title")
    layout_options = dict(spec.get("layout") or {})
    markers = bool(layout_options.get("markers", False))
    respect_manual_positions = bool(layout_options.get("respectManualPositions", False))
    lane_orientation = str(layout_options.get("laneOrientation", "horizontal"))

    return LogicalGraph(
        diagram_type=diagram_type,
        direction=spec.get("direction", "TB"),
        nodes=tuple(nodes),
        edges=tuple(edges),
        lanes=tuple(lanes),
        phases=tuple(phases),
        title=title,
        markers=markers,
        lane_orientation=lane_orientation,
        layout_options=layout_options,
        respect_manual_positions=respect_manual_positions,
        theme=theme,
    )
