"""SVG writer for graph diagrams (ADR-003): the canonical artifact.

Consumes a ``PositionedDiagram`` (layout already done) and emits a deterministic,
self-contained SVG: embedded font subset, resolved styles, shape set + arrowheads,
edge polylines from the adapter's routed points. No layout math happens here — writers
never position (ADR-001). Per-label ``direction``/``xml:lang`` keep RTL first-class.
"""
from __future__ import annotations

from tarseem.model.ir import Label, PositionedDiagram, PositionedNode
from tarseem.render.fonts import FONT_FAMILY, subset_woff2_datauri

__all__ = ["render_svg"]

_MARGIN = 24.0
_DEFAULT_FILL = "#FFFFFF"
_DEFAULT_STROKE = "#333333"
_DEFAULT_TEXT = "#14281D"
_DEFAULT_EDGE = "#333333"


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
        s = 20.0
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
        return body + top
    if kind == "document":
        wv = 14.0
        return (
            f'<path d="M {_p(x, y)} L {_p(x + w, y)} L {_p(x + w, y + h - wv)} '
            f'Q {_p(x + 3 * w / 4, y + h)} {_p(x + w / 2, y + h - wv / 2)} '
            f'T {_p(x, y + h - wv)} Z" {st}/>'
        )
    return _rect(x, y, w, h, st)


def _arrowhead(p1: tuple[float, float], p2: tuple[float, float], color: str) -> str:
    (x1, y1), (x2, y2) = p1, p2
    sz = 9.0
    if abs(x2 - x1) >= abs(y2 - y1):  # horizontal-ish
        d = 1.0 if x2 > x1 else -1.0
        tip = [(x2, y2), (x2 - d * sz, y2 - sz * 0.6), (x2 - d * sz, y2 + sz * 0.6)]
    else:
        d = 1.0 if y2 > y1 else -1.0
        tip = [(x2, y2), (x2 - sz * 0.6, y2 - d * sz), (x2 + sz * 0.6, y2 - d * sz)]
    return _poly(tip, f'fill="{color}"')


def _label_attrs(label: Label) -> str:
    attrs = 'text-anchor="middle" dominant-baseline="central"'
    if label.direction:
        attrs += f' direction="{label.direction}"'
    if label.lang:
        attrs += f' xml:lang="{_esc(label.lang)}"'
    return attrs


def _collect_chars(diagram: PositionedDiagram) -> frozenset[str]:
    chars: set[str] = set()
    for n in diagram.nodes:
        chars.update(n.label.text)
    for e in diagram.edges:
        if e.label:
            chars.update(e.label.text)
    return frozenset(chars)


def render_svg(diagram: PositionedDiagram) -> str:
    # swimlanes carry band chrome and absolute coords -> dedicated writer
    if diagram.lanes:
        from tarseem.render.swimlane import render_swimlane_svg

        return render_swimlane_svg(diagram)
    # sequence diagrams have lifeline stems + activation bars -> dedicated writer
    if diagram.diagram_type == "sequence":
        from tarseem.render.sequence import render_sequence_svg

        return render_sequence_svg(diagram)

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
        f'<rect width="{_num(width)}" height="{_num(height)}" fill="#FFFFFF"/>',
        f'<g transform="translate({_num(dx)},{_num(dy)})">',
    ]

    # edges first so node shapes sit on top of arrowheads tucked at borders
    for e in diagram.edges:
        color = str(e.style.get("stroke", _DEFAULT_EDGE))
        sw = float(e.style.get("width", 1) or 1)
        dash = ' stroke-dasharray="6 4"' if e.style.get("style") == "dashed" else ""
        poly = " ".join(f"{_num(px)},{_num(py)}" for px, py in e.points)
        parts.append(
            f'<polyline points="{poly}" fill="none" stroke="{color}" '
            f'stroke-width="{_num(sw)}"{dash}/>'
        )
        if len(e.points) >= 2:
            parts.append(_arrowhead(e.points[-2], e.points[-1], color))
        if e.label and e.label_xy:
            lx, ly = e.label_xy
            half = max(8.0, len(e.label.text) * 3.5)
            parts.append(
                f'<rect x="{_num(lx - half)}" y="{_num(ly - 9)}" width="{_num(2 * half)}" '
                f'height="18" fill="#FFFFFF" opacity="0.9"/>'
            )
            parts.append(
                f'<text x="{_num(lx)}" y="{_num(ly)}" font-size="12" fill="{color}" '
                f'{_label_attrs(e.label)}>{_esc(e.label.text)}</text>'
            )

    # nodes + labels
    for n in diagram.nodes:
        parts.append(_shape_svg(n))
        text_color = str((n.style.get("text") or {}).get("color", _DEFAULT_TEXT))
        size = float((n.style.get("text") or {}).get("size", 12))
        parts.append(
            f'<text x="{_num(n.x + n.width / 2)}" y="{_num(n.y + n.height / 2)}" '
            f'font-size="{_num(size)}" fill="{text_color}" {_label_attrs(n.label)}>'
            f"{_esc(n.label.text)}</text>"
        )

    parts.append("</g>")
    parts.append("</svg>")
    return "\n".join(parts)
