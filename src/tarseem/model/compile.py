"""Compile a validated spec into the logical IR (ADR-001, FR-5.4).

Style resolution happens here (via the A5 cascade) so downstream stages — measurement,
layout, writers — receive nodes/edges with already-resolved style dicts. Pure: never
mutates the input spec.
"""
from __future__ import annotations

from tarseem.model.ir import (
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
}


def _label(raw: dict | None) -> Label | None:
    if not raw:
        return None
    return Label(
        text=str(raw.get("text", "")),
        lang=raw.get("lang"),
        direction=raw.get("direction"),
    )


def compile_spec(spec: dict, theme: dict | None = None) -> LogicalGraph:
    """Build the logical IR from a validated spec. Run :func:`tarseem.validation.validate`
    first; this assumes structural/referential integrity."""
    theme_ref = spec.get("theme") or {}
    # accept either `theme.ref` (schema-preferred) or `theme.name`; ref wins
    theme = theme or get_theme(theme_ref.get("ref") or theme_ref.get("name"))
    diagram_type = spec.get("diagramType", "flowchart")
    default_shape = _DEFAULT_SHAPE.get(diagram_type, "rect")

    nodes: list[LogicalNode] = []
    for raw in spec.get("nodes", []) or []:
        label = _label(raw.get("label")) or Label(text=str(raw.get("id", "")))
        nodes.append(
            LogicalNode(
                id=raw["id"],
                label=label,
                shape=raw.get("shape", default_shape),
                kind=raw.get("kind"),
                lane=raw.get("lane"),
                phase=raw.get("phase"),
                show_badge=bool(raw.get("badge", True)),
                style=resolve_node_style(spec, raw, theme),
            )
        )

    edges: list[LogicalEdge] = []
    for raw in spec.get("edges", []) or []:
        style = resolve_edge_style(spec, raw, theme)
        if raw.get("dashed"):
            style = {**style, "style": "dashed"}
        edges.append(
            LogicalEdge(
                id=raw.get("id", f"{raw['source']}->{raw['target']}"),
                source=raw["source"],
                target=raw["target"],
                label=_label(raw.get("label")),
                style=style,
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
        lanes.append(LogicalLane(id=raw["id"], label=label, hue=hue))

    phases: list[LogicalPhase] = []
    for i, raw in enumerate(spec.get("phases", []) or []):
        label = _label(raw.get("label")) or Label(text=str(raw.get("id", "")))
        phases.append(LogicalPhase(id=raw["id"], label=label, order=float(raw.get("order", i))))

    title = (spec.get("meta") or {}).get("title")
    layout_options = dict(spec.get("layout") or {})
    markers = bool(layout_options.get("markers", False))

    return LogicalGraph(
        diagram_type=diagram_type,
        direction=spec.get("direction", "TB"),
        nodes=tuple(nodes),
        edges=tuple(edges),
        lanes=tuple(lanes),
        phases=tuple(phases),
        title=title,
        markers=markers,
        layout_options=layout_options,
        theme=theme,
    )
