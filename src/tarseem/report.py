"""RenderReport: deterministic quality metrics over the positioned IR (Phase 3).

Pure geometry — edge-crossing count, node-overlap count, extent — plus an engine-injected
render time. These are the numeric signal the gallery shows per sample and the regression
suite asserts on (09 §1). Nothing here mutates the diagram.

This module also defines the **CapabilityReport** (invariant 6: "capability reports, never
silent drops"). Every export writer declares what it ``supports`` and emits machine-readable
``warnings`` for any feature it cannot carry. All writers report against ONE shared feature
vocabulary (``FEATURES``) so the Phase-6 fidelity-ceiling table is a pivot over real report
data, not prose.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from tarseem.model.ir import PositionedDiagram, PositionedEdge, PositionedNode

__all__ = [
    "RenderReport",
    "analyze",
    "FEATURES",
    "Support",
    "CapabilityWarning",
    "CapabilityReport",
    "build_capability_report",
]

# ---------------------------------------------------------------------------
# Capability reporting (invariant 6) — shared across every export writer.
# ---------------------------------------------------------------------------

# The axes every writer reports fidelity against. Keep this the single source of truth:
# adding a writer concern means adding it here once, so the fidelity table stays aligned.
FEATURES: tuple[str, ...] = (
    "shapes",  # full IR shape vocabulary (rect/diamond/cylinder/cube/...)
    "lanes",  # swimlane pool/lane chrome
    "phases",  # swimlane phase header bands (FR-6.3)
    "badges",  # auto-number badges
    "markers",  # UML start/end markers
    "edge_routes",  # exact orthogonal polyline geometry from the positioned IR
    "edge_labels",
    "curved_edges",  # curved/spline edge mode
    "ports",  # per-row / per-side edge anchoring (ER)
    "gradients",
    "fonts_embedded",  # font bytes travel with the artifact
    "rtl_shaping",  # shaped Arabic / bidi handled by the artifact itself
    "theme_fidelity",  # fills/strokes/text colours carried faithfully
    "metadata",  # provenance embedded in the artifact
)

# Per-feature support level a writer declares.
#   "full"    — carried with no loss within the writer's medium
#   "partial" — carried approximately, or delegated to the viewer; see warnings
#   "none"    — not representable; dropped (a warning is emitted iff the spec used it)
Support = str  # one of: "full" | "partial" | "none"

_SUPPORT_LEVELS = ("full", "partial", "none")


@dataclass(frozen=True)
class CapabilityWarning:
    """One machine-readable fidelity note. ``element`` names the offending node/edge id
    when the loss is element-specific, else None for a whole-diagram limitation."""

    code: str  # stable machine code, e.g. "feature-dropped" | "feature-approximated"
    feature: str  # one of FEATURES
    message: str  # human-readable detail
    element: str | None = None

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "feature": self.feature,
            "message": self.message,
            "element": self.element,
        }


@dataclass(frozen=True)
class CapabilityReport:
    """What a writer could and could not carry for one export. Deterministic: derived
    purely from the diagram + the writer's fixed capabilities (no wall-clock, no I/O)."""

    writer: str
    supports: dict[str, Support] = field(default_factory=dict)
    warnings: tuple[CapabilityWarning, ...] = ()

    @property
    def lossy(self) -> bool:
        return bool(self.warnings) or any(v != "full" for v in self.supports.values())

    def to_dict(self) -> dict:
        return {
            "writer": self.writer,
            "supports": dict(self.supports),
            "warnings": [w.to_dict() for w in self.warnings],
            "lossy": self.lossy,
        }


def build_capability_report(
    writer: str,
    supports: dict[str, Support],
    warnings: list[CapabilityWarning] | None = None,
) -> CapabilityReport:
    """Construct a CapabilityReport, validating it speaks the shared vocabulary. Catches a
    writer drifting from ``FEATURES`` (typo / stale key) at build time rather than silently
    producing an off-axis fidelity table."""
    unknown = set(supports) - set(FEATURES)
    if unknown:
        raise ValueError(f"{writer}: unknown capability feature(s): {sorted(unknown)}")
    bad_level = {k: v for k, v in supports.items() if v not in _SUPPORT_LEVELS}
    if bad_level:
        raise ValueError(f"{writer}: invalid support level(s): {bad_level}")
    warns = tuple(warnings or ())
    bad_feature = [w.feature for w in warns if w.feature not in FEATURES]
    if bad_feature:
        raise ValueError(f"{writer}: warning(s) cite unknown feature(s): {bad_feature}")
    return CapabilityReport(writer=writer, supports=dict(supports), warnings=warns)

Point = tuple[float, float]


@dataclass(frozen=True)
class RenderReport:
    node_count: int
    edge_count: int
    crossings: int
    overlaps: int
    width: float
    height: float
    render_ms: float | None = None

    def to_dict(self) -> dict:
        return {
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "crossings": self.crossings,
            "overlaps": self.overlaps,
            "width": self.width,
            "height": self.height,
            "render_ms": self.render_ms,
        }


def _segments(edge: PositionedEdge) -> list[tuple[Point, Point]]:
    p = edge.points
    return [(p[i], p[i + 1]) for i in range(len(p) - 1)]


def _orient(a: Point, b: Point, c: Point) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _proper_intersect(s1: tuple[Point, Point], s2: tuple[Point, Point]) -> bool:
    """True only for a proper crossing. Segments that share an endpoint (edges fanning
    out of the same node) or merely touch/overlap collinearly do not count."""
    p1, p2 = s1
    p3, p4 = s2
    if p1 in (p3, p4) or p2 in (p3, p4):
        return False
    d1, d2 = _orient(p3, p4, p1), _orient(p3, p4, p2)
    d3, d4 = _orient(p1, p2, p3), _orient(p1, p2, p4)
    return (d1 > 0) != (d2 > 0) and (d3 > 0) != (d4 > 0)


def _count_crossings(edges: tuple[PositionedEdge, ...]) -> int:
    segs = [(e.id, s) for e in edges for s in _segments(e)]
    crossings = 0
    for i in range(len(segs)):
        eid_i, si = segs[i]
        for j in range(i + 1, len(segs)):
            eid_j, sj = segs[j]
            if eid_i == eid_j:  # ignore self-bends within one polyline
                continue
            if _proper_intersect(si, sj):
                crossings += 1
    return crossings


def _overlaps(a: PositionedNode, b: PositionedNode) -> bool:
    return (
        a.x < b.x + b.width
        and b.x < a.x + a.width
        and a.y < b.y + b.height
        and b.y < a.y + a.height
    )


def _count_overlaps(nodes: tuple[PositionedNode, ...]) -> int:
    count = 0
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            if _overlaps(nodes[i], nodes[j]):
                count += 1
    return count


def analyze(diagram: PositionedDiagram, render_ms: float | None = None) -> RenderReport:
    """Compute geometry metrics for ``diagram``. ``render_ms`` is injected (timed by the
    caller); geometry is deterministic, so equal diagrams give equal reports."""
    return RenderReport(
        node_count=len(diagram.nodes),
        edge_count=len(diagram.edges),
        crossings=_count_crossings(diagram.edges),
        overlaps=_count_overlaps(diagram.nodes),
        width=diagram.width,
        height=diagram.height,
        render_ms=render_ms,
    )
