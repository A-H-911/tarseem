"""Apply ``export.svg`` options to finished SVG (07 §2): font embedding + text-as-paths.

These are post-processors so the writers stay option-free:

- ``embedFonts`` (default true): the writer always embeds a used-glyph WOFF2 subset. When
  false, drop the ``@font-face`` data-URI and fall back to the named font stack — smaller
  file, but the consumer must have an Arabic-capable font installed.
- ``textAsPaths`` (default false): convert ``<text>`` to glyph outlines (see ``textpath``);
  fonts then become irrelevant, so the embedded subset is dropped too.
"""
from __future__ import annotations

import re

from tarseem.render.textpath import text_to_paths
from tarseem.themes import FONT_STACK

__all__ = ["apply_export_options", "DEFAULT_SVG_EXPORT"]

DEFAULT_SVG_EXPORT = {"embedFonts": True, "textAsPaths": False}

_FONT_FACE_RE = re.compile(r"@font-face\{[^}]*\}")
_TEXT_RULE_RE = re.compile(r"text\{font-family:'[^']*';\}")


def _font_stack_css() -> str:
    return ",".join(f"'{f}'" if " " in f else f for f in FONT_STACK)


def apply_export_options(svg: str, svg_opts: dict | None) -> str:
    """Apply the ``export.svg`` options to a rendered SVG string (no-op for defaults)."""
    opts = {**DEFAULT_SVG_EXPORT, **(svg_opts or {})}

    if opts.get("textAsPaths"):
        svg = text_to_paths(svg)
        # no <text> remains -> the embedded subset is dead weight; drop it
        svg = _FONT_FACE_RE.sub("", svg)
        svg = _TEXT_RULE_RE.sub("", svg)
        return svg

    if not opts.get("embedFonts", True):
        svg = _FONT_FACE_RE.sub("", svg)
        svg = _TEXT_RULE_RE.sub(f"text{{font-family:{_font_stack_css()};}}", svg)
    return svg
