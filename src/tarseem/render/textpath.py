"""``textAsPaths`` export: convert ``<text>`` elements to shaped glyph outlines (07 §2).

Off by default. When enabled, every ``<text>`` in the finished SVG is re-shaped with
uharfbuzz (the same engine that measured the label — never pre-shaped into the IR) and each
shaped glyph is traced to a ``<path>`` via fontTools. The result renders identically on any
SVG consumer, including renderers with no bidi/HarfBuzz support (resvg, some PDF stacks) —
at the cost of text selectability/searchability, which is why it is opt-in.

Implemented as a post-processor over the writer output so all three writers (graph,
swimlane, sequence) inherit it without change.
"""
from __future__ import annotations

import functools
import re
from typing import Any

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

from tarseem.measure import default_font_path

__all__ = ["text_to_paths"]

_TEXT_RE = re.compile(r"<text\b([^>]*)>(.*?)</text>", re.DOTALL)
_ATTR_RE = re.compile(r'([\w:-]+)="([^"]*)"')


def _unesc(s: str) -> str:
    return (
        s.replace("&quot;", '"')
        .replace("&gt;", ">")
        .replace("&lt;", "<")
        .replace("&amp;", "&")
    )


@functools.lru_cache(maxsize=1)
def _hb_font() -> hb.Font:
    blob = hb.Blob.from_file_path(str(default_font_path()))
    return hb.Font(hb.Face(blob))


@functools.lru_cache(maxsize=1)
def _glyph_set_and_metrics() -> tuple[Any, list[str], int, float]:
    ttf = TTFont(str(default_font_path()), recalcTimestamp=False)
    glyph_set = ttf.getGlyphSet()
    order = ttf.getGlyphOrder()
    upem = ttf["head"].unitsPerEm
    # central-baseline approximation: shift glyphs down by half the typo height so a
    # baseline-anchored outline sits where dominant-baseline="central" would.
    asc = ttf["hhea"].ascent
    desc = ttf["hhea"].descent
    center_frac = (asc + desc) / 2.0 / upem
    return glyph_set, order, upem, center_frac


def _shape(text: str, direction: str | None) -> list[tuple[int, float, float, float]]:
    """Return (glyph_id, x_advance, x_offset, y_offset) in font units, in visual order."""
    font = _hb_font()
    buf = hb.Buffer()
    buf.add_str(text)
    if direction in ("ltr", "rtl"):
        buf.direction = direction
        buf.guess_segment_properties()
        buf.direction = direction
    else:
        buf.guess_segment_properties()
    hb.shape(font, buf)
    out = []
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions, strict=True):
        out.append((info.codepoint, pos.x_advance, pos.x_offset, pos.y_offset))
    return out


def _glyph_path(gid: int) -> str:
    glyph_set, order, _upem, _c = _glyph_set_and_metrics()
    if gid >= len(order):
        return ""
    pen = SVGPathPen(glyph_set)
    glyph_set[order[gid]].draw(pen)
    return pen.getCommands()


def _text_to_group(attrs_str: str, inner: str) -> str:
    attrs = dict(_ATTR_RE.findall(attrs_str))
    text = _unesc(inner)
    if not text.strip():
        return f"<text{attrs_str}>{inner}</text>"  # leave whitespace-only nodes alone

    x = float(attrs.get("x", "0"))
    y = float(attrs.get("y", "0"))
    size = float(attrs.get("font-size", "12"))
    fill = attrs.get("fill", "#000000")
    anchor = attrs.get("text-anchor", "start")
    direction = attrs.get("direction")

    _gs, _order, upem, center_frac = _glyph_set_and_metrics()
    scale = size / upem
    glyphs = _shape(text, direction)
    total_adv = sum(g[1] for g in glyphs) * scale

    if anchor == "middle":
        pen_x = x - total_adv / 2
    elif anchor == "end":
        pen_x = x - total_adv
    else:
        pen_x = x
    baseline_y = y - center_frac * size  # center the run on y (central baseline)

    paths: list[str] = []
    cursor = pen_x
    for gid, x_adv, x_off, y_off in glyphs:
        d = _glyph_path(gid)
        if d:
            gx = cursor + x_off * scale
            gy = baseline_y - y_off * scale
            # font units y-up -> SVG y-down: scale(s, -s)
            paths.append(
                f'<path transform="translate({gx:.2f},{gy:.2f}) scale({scale:.5f},{-scale:.5f})" '
                f'fill="{fill}" d="{d}"/>'
            )
        cursor += x_adv * scale
    return f'<g class="t2p">{"".join(paths)}</g>'


def text_to_paths(svg: str) -> str:
    """Replace every ``<text>`` in ``svg`` with shaped glyph outlines (``<path>``)."""
    return _TEXT_RE.sub(lambda m: _text_to_group(m.group(1), m.group(2)), svg)
