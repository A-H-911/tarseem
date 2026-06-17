"""SVG writer for graph diagrams (ADR-003): the canonical artifact.

Consumes a ``PositionedDiagram`` (layout already done) and emits a deterministic,
self-contained SVG: embedded font subset, resolved styles, shape set + arrowheads,
edge polylines from the adapter's routed points. No layout math happens here — writers
never position (ADR-001). Per-label ``direction``/``xml:lang`` keep RTL first-class.
"""
from __future__ import annotations

from tarseem.families import get_plugin
from tarseem.geometry import (
    DEFAULT_EDGE as _DEFAULT_EDGE,
    DEFAULT_FILL as _DEFAULT_FILL,
    DEFAULT_STROKE as _DEFAULT_STROKE,
    DEFAULT_TEXT as _DEFAULT_TEXT,
    PARALLELOGRAM_SLANT,
    pseudostate_circles,
)
from tarseem.model.ir import Label, PositionedDiagram, PositionedNode
from tarseem.render.fonts import FONT_FAMILY, subset_woff2_datauri
from tarseem.render.text import label_attrs as _resolve_label_attrs, resolve_edge_corners

__all__ = ["render_svg", "render_generic_svg"]

_MARGIN = 24.0
_CYL_CAP = 6.0  # cylinder label drop (px) so text centres on the body, below the top ellipse cap
# Subtle drop shadow for 3-D shapes (cube/cylinder) — owner-preferred; mirrored in draw.io/pptx.
SHADOW_DEF = (
    '<filter id="tarseem-shadow" x="-20%" y="-20%" width="140%" height="140%">'
    '<feDropShadow dx="2" dy="3" stdDeviation="2" flood-color="#000000" flood-opacity="0.32"/>'
    "</filter>"
)
_SHADOW = ' filter="url(#tarseem-shadow)"'


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _num(v: float) -> str:
    return f"{v:.2f}".rstrip("0").rstrip(".")


def _node_fill(style: dict) -> str:
    return str(style.get("fill", _DEFAULT_FILL))


def _node_stroke(style: dict) -> tuple[str, float]:
    border = style.get("border") or {}
    return str(border.get("color", _DEFAULT_STROKE)), float(border.get("width", 1) or 1)


def _p(x: float, y: float) -> str:
    return f"{_num(x)},{_num(y)}"


def _poly(coords: list[tuple[float, float]], attrs: str) -> str:
    pts = " ".join(_p(cx, cy) for cx, cy in coords)
    return f'<polygon points="{pts}" {attrs}/>'


def _rect(x: float, y: float, w: float, h: float, attrs: str, rx: float | None = None) -> str:
    r = f' rx="{_num(rx)}"' if rx is not None else ""
    return f'<rect x="{_num(x)}" y="{_num(y)}" width="{_num(w)}" height="{_num(h)}"{r} {attrs}/>'


def _shape_svg(n: PositionedNode) -> str:
    x, y, w, h = n.x, n.y, n.width, n.height
    fill = _node_fill(n.style)
    stroke, sw = _node_stroke(n.style)
    st = f'fill="{fill}" stroke="{stroke}" stroke-width="{_num(sw)}"'
    kind = n.shape
    if kind == "stadium":
        return _rect(x, y, w, h, st, rx=h / 2)
    if kind in ("roundrect", "rounded"):
        return _rect(x, y, w, h, st, rx=10)
    if kind == "diamond":
        cx, cy = x + w / 2, y + h / 2
        return _poly([(cx, y), (x + w, cy), (cx, y + h), (x, cy)], st)
    if kind == "parallelogram":
        s = PARALLELOGRAM_SLANT
        return _poly([(x + s, y), (x + w, y), (x + w - s, y + h), (x, y + h)], st)
    if kind == "cylinder":
        ry = 9.0
        rw = _num(w / 2)
        body = (
            f'<path d="M {_p(x, y + ry)} A {rw} {_num(ry)} 0 0 1 {_p(x + w, y + ry)} '
            f'L {_p(x + w, y + h - ry)} A {rw} {_num(ry)} 0 0 1 {_p(x, y + h - ry)} Z" {st}/>'
        )
        top = (
            f'<path d="M {_p(x, y + ry)} A {rw} {_num(ry)} 0 0 0 {_p(x + w, y + ry)}" '
            f'fill="none" stroke="{stroke}" stroke-width="{_num(sw)}"/>'
        )
        return f'<g{_SHADOW}>{body}{top}</g>'
    if kind == "document":
        wv = 14.0
        return (
            f'<path d="M {_p(x, y)} L {_p(x + w, y)} L {_p(x + w, y + h - wv)} '
            f'Q {_p(x + 3 * w / 4, y + h)} {_p(x + w / 2, y + h - wv / 2)} '
            f'T {_p(x, y + h - wv)} Z" {st}/>'
        )
    if kind == "initial":  # state-machine start pseudostate: a solid filled dot
        ps = pseudostate_circles(n)
        return f'<circle cx="{_num(ps.cx)}" cy="{_num(ps.cy)}" r="{_num(ps.r)}" fill="{stroke}"/>'
    if kind == "final":  # state-machine end pseudostate: a ring around a filled dot
        ps = pseudostate_circles(n)
        return (
            f'<circle cx="{_num(ps.cx)}" cy="{_num(ps.cy)}" r="{_num(ps.r)}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{_num(sw)}"/>'
            f'<circle cx="{_num(ps.cx)}" cy="{_num(ps.cy)}" r="{_num(ps.inner_r)}" '
            f'fill="{stroke}"/>'
        )
    if kind == "cube":  # deployment 3D node: front face + top + right depth faces
        d = 14.0
        front = _rect(x, y + d, w - d, h - d, st)
        top = _poly([(x, y + d), (x + d, y), (x + w, y), (x + w - d, y + d)], st)
        right = _poly(
            [(x + w - d, y + d), (x + w, y), (x + w, y + h - d), (x + w - d, y + h)], st
        )
        return f'<g{_SHADOW}>{top}{right}{front}</g>'
    return _rect(x, y, w, h, st)


def _arrowhead(p1: tuple[float, float], p2: tuple[float, float], color: str) -> str:
    """Filled triangle at ``p2``, pointing along the true ``p1``->``p2`` direction so it follows
    diagonal edges (mindmap mrtree/radial), not just the four orthogonal directions. For an
    axis-aligned segment this is the same triangle as a 4-direction head (pixel-identical), so
    orthogonal families are unchanged."""
    (x1, y1), (x2, y2) = p1, p2
    sz = 9.0
    dx, dy = x2 - x1, y2 - y1
    dist = (dx * dx + dy * dy) ** 0.5
    if not dist:  # degenerate segment carries no direction
        return ""
    ux, uy = dx / dist, dy / dist  # unit vector toward the tip
    px, py = -uy, ux  # left-hand perpendicular
    half = sz * 0.6
    bx, by = x2 - ux * sz, y2 - uy * sz  # base centre, one length back from the tip
    tip = [(x2, y2), (bx + px * half, by + py * half), (bx - px * half, by - py * half)]
    return _poly(tip, f'fill="{color}"')


_EDGE_RADIUS = 8.0


def _toward(b: tuple[float, float], a: tuple[float, float], r: float) -> tuple[float, float]:
    """Point ``r`` from ``b`` toward ``a`` (clamped to half the segment)."""
    dx, dy = a[0] - b[0], a[1] - b[1]
    dist = (dx * dx + dy * dy) ** 0.5 or 1.0
    rr = min(r, dist / 2)
    return b[0] + dx / dist * rr, b[1] + dy / dist * rr


def edge_svg_line(
    points: list[tuple[float, float]], stroke: str, sw: float, dash: str, curved: bool
) -> str:
    """One edge line — rounded-corner ``<path>`` when ``curved`` (default), else ``<polyline>``.
    Shared by every edge writer so engine and draw.io agree (theme.edgeCorners)."""
    if curved and len(points) > 2:
        d = [f"M {_p(*points[0])}"]
        for i in range(1, len(points) - 1):
            a, b, c = points[i - 1], points[i], points[i + 1]
            d.append(f"L {_p(*_toward(b, a, _EDGE_RADIUS))}")
            d.append(f"Q {_p(*b)} {_p(*_toward(b, c, _EDGE_RADIUS))}")
        d.append(f"L {_p(*points[-1])}")
        path = " ".join(d)
        return (
            f'<path d="{path}" fill="none" stroke="{stroke}" '
            f'stroke-width="{_num(sw)}"{dash}/>'
        )
    poly = " ".join(_p(px, py) for px, py in points)
    return (
        f'<polyline points="{poly}" fill="none" stroke="{stroke}" '
        f'stroke-width="{_num(sw)}"{dash}/>'
    )


def _label_center(n: PositionedNode) -> tuple[float, float]:
    """Centre point for a node's label. A cube reserves depth at top+right, so its label
    centres on the FRONT face, not the bbox (bug: deployment label off-centre)."""
    if n.shape == "cube":
        d = 14.0  # MUST match _shape_svg cube depth + measure._CUBE_DEPTH
        return n.x + (n.width - d) / 2, n.y + d + (n.height - d) / 2
    if n.shape == "cylinder":  # drop below the top cap so text centres on the body (PPTX CAN look)
        return n.x + n.width / 2, n.y + n.height / 2 + _CYL_CAP
    return n.x + n.width / 2, n.y + n.height / 2


def _label_attrs(label: Label) -> str:
    """Anchoring + bidi (direction/xml:lang) for a label. Auto-detects Arabic so RTL
    text renders naturally; LTR labels keep their pre-Phase-4 attribute bytes (07 §2)."""
    return _resolve_label_attrs(label)


def _collect_chars(diagram: PositionedDiagram) -> frozenset[str]:
    chars: set[str] = set()
    for n in diagram.nodes:
        chars.update(n.label.text)
    for e in diagram.edges:
        if e.label:
            chars.update(e.label.text)
    return frozenset(chars)


def render_svg(diagram: PositionedDiagram) -> str:
    """Dispatch to the family's renderer via the registry; the generic graph renderer is the
    default for any family that declares none (flowchart/architecture/dependency/state/
    deployment/mindmap and external ELK clones).

    Swimlanes keep a structural fast-path: detected by ``diagram.lanes`` (band chrome + absolute
    coords), not by ``diagramType`` — so a laneless graph never reaches the swimlane writer."""
    if diagram.lanes:
        from tarseem.render.swimlane import render_swimlane_svg

        return render_swimlane_svg(diagram)
    renderer = get_plugin(diagram.diagram_type).svg_renderer
    return renderer(diagram) if renderer is not None else render_generic_svg(diagram)


def render_generic_svg(diagram: PositionedDiagram) -> str:
    """The default node + edge graph renderer: embedded font subset, routed edge polylines,
    shapes, and labels. Dedicated families (swimlane/sequence/er/class) override via their
    plugin's ``svg_renderer``."""
    dx, dy = _MARGIN, _MARGIN
    width = diagram.width + 2 * _MARGIN
    height = diagram.height + 2 * _MARGIN
    b64 = subset_woff2_datauri(_collect_chars(diagram))

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_num(width)}" height="{_num(height)}" '
        f'viewBox="0 0 {_num(width)} {_num(height)}">',
        "<style>",
        f"@font-face{{font-family:'{FONT_FAMILY}';"
        f"src:url(data:font/woff2;base64,{b64}) format('woff2');}}",
        f"text{{font-family:'{FONT_FAMILY}';}}",
        "</style>",
        f"<defs>{SHADOW_DEF}</defs>",
        f'<rect width="{_num(width)}" height="{_num(height)}" fill="#FFFFFF"/>',
        f'<g transform="translate({_num(dx)},{_num(dy)})">',
    ]

    # edges first so node shapes sit on top of arrowheads tucked at borders
    curved = resolve_edge_corners(diagram.theme)
    for e in diagram.edges:
        color = str(e.style.get("stroke", _DEFAULT_EDGE))
        sw = float(e.style.get("width", 1) or 1)
        dash = ' stroke-dasharray="6 4"' if e.style.get("style") == "dashed" else ""
        parts.append(edge_svg_line(list(e.points), color, sw, dash, curved))
        if len(e.points) >= 2:
            parts.append(_arrowhead(e.points[-2], e.points[-1], color))
        if e.label and e.label_xy:
            lx, ly = e.label_xy
            parts.append(
                f'<text x="{_num(lx)}" y="{_num(ly)}" font-size="12" fill="{color}" '
                f'{_label_attrs(e.label)}>{_esc(e.label.text)}</text>'
            )

    # nodes + labels
    for n in diagram.nodes:
        parts.append(_shape_svg(n))
        text_color = str((n.style.get("text") or {}).get("color", _DEFAULT_TEXT))
        size = float((n.style.get("text") or {}).get("size", 12))
        lcx, lcy = _label_center(n)
        parts.append(
            f'<text x="{_num(lcx)}" y="{_num(lcy)}" '
            f'font-size="{_num(size)}" fill="{text_color}" {_label_attrs(n.label)}>'
            f"{_esc(n.label.text)}</text>"
        )

    parts.append("</g>")
    parts.append("</svg>")
    return "\n".join(parts)
