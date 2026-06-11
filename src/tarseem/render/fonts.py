"""Font subsetting + embedding for self-contained SVG (ADR-004, FR-3).

Subsets the bundled font to just the glyphs a diagram uses and embeds it as a base64
WOFF2 data-URI, so an SVG renders identically anywhere without a system font. Default
subsetting retains layout features, so Arabic joining/shaping survives the subset.
"""
from __future__ import annotations

import base64
import functools
import io

from fontTools import subset
from fontTools.ttLib import TTFont

from tarseem.measure import default_font_path

__all__ = ["FONT_FAMILY", "subset_woff2_datauri"]

# Unique family name proves the embedded subset is used, not a host font.
FONT_FAMILY = "TarseemCairo"


@functools.lru_cache(maxsize=64)
def subset_woff2_datauri(chars: frozenset[str]) -> str:
    """Base64 WOFF2 of the bundled font subset covering ``chars`` (whitespace dropped)."""
    codepoints = [ord(c) for c in chars if not c.isspace()]
    ttf = TTFont(str(default_font_path()))
    ss = subset.Subsetter()
    ss.populate(unicodes=codepoints or [ord("?")])
    ss.subset(ttf)
    ttf.flavor = "woff2"
    buf = io.BytesIO()
    ttf.save(buf)
    return base64.b64encode(buf.getvalue()).decode("ascii")
