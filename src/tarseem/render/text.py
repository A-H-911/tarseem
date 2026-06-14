"""Per-label bidi base-direction & language resolution for the SVG writers (07 §2).

Shaping is the *renderer's* job — Chromium runs HarfBuzz over the logical-order Unicode
we emit. We never reorder or pre-shape codepoints into the IR (R-5: that double-shapes in
shaping-capable renderers). What a writer legitimately decides per label is its bidi *base
direction* and language, so the renderer applies the Unicode Bidi Algorithm correctly and
sets the right anchoring. Arabic is auto-detected, so ``direction: auto`` (or an untagged
label) renders naturally without the spec author annotating every string.

Emission rule: ``direction="rtl"`` is added only when RTL is resolved (or a direction was
set explicitly). LTR is the SVG default, so LTR labels emit no ``direction`` attribute and
stay byte-identical to the pre-Phase-4 output — existing baselines do not churn.
"""
from __future__ import annotations

from tarseem.model.ir import Label

__all__ = [
    "has_rtl",
    "resolve_direction",
    "resolve_lang",
    "bidi_attrs",
    "label_attrs",
    "resolve_badge_side",
    "resolve_edge_corners",
]


def resolve_entity_corners(theme: dict | None = None) -> str:
    """ER entity corner style: ``"rounded"`` (default, matches the SVG) or ``"square"``.
    Spec override: ``theme.entityCorners``."""
    corner = str((theme or {}).get("entityCorners") or "rounded").lower()
    return "square" if corner == "square" else "rounded"


def resolve_edge_corners(theme: dict | None = None) -> bool:
    """True when edge bends are drawn curved (rounded) — the default. Spec
    ``theme.edgeCorners`` = ``"straight"`` switches every edge to sharp corners."""
    return str((theme or {}).get("edgeCorners") or "curved").lower() != "straight"


def resolve_badge_side(rtl: bool, theme: dict | None = None) -> str:
    """Corner the auto-number badge sits on. Default: LTR -> right, RTL -> left. Overridable
    per spec via ``theme.badgeCorner`` = ``"left"`` | ``"right"`` (``"auto"`` keeps the default)."""
    corner = str((theme or {}).get("badgeCorner") or "auto").lower()
    if corner in ("left", "right"):
        return corner
    return "left" if rtl else "right"

# Strong-RTL Unicode blocks: Hebrew, Arabic (+ Supplement, Extended-A), Thaana,
# and the Arabic Presentation Forms. Membership of any code point flips a label to RTL
# base direction when the spec leaves direction as auto/unset.
_RTL_RANGES: tuple[tuple[int, int], ...] = (
    (0x0590, 0x05FF),  # Hebrew
    (0x0600, 0x06FF),  # Arabic
    (0x0700, 0x074F),  # Syriac
    (0x0750, 0x077F),  # Arabic Supplement
    (0x0780, 0x07BF),  # Thaana
    (0x08A0, 0x08FF),  # Arabic Extended-A
    (0xFB1D, 0xFDFF),  # Hebrew + Arabic Presentation Forms-A
    (0xFE70, 0xFEFF),  # Arabic Presentation Forms-B
)


def _is_rtl_char(ch: str) -> bool:
    cp = ord(ch)
    return any(lo <= cp <= hi for lo, hi in _RTL_RANGES)


def has_rtl(text: str) -> bool:
    """True if any character is strong-RTL (Arabic/Hebrew/…). Drives auto-detection."""
    return any(_is_rtl_char(c) for c in text)


def resolve_direction(direction: str | None, text: str) -> str:
    """Resolve a label's bidi base direction to a concrete ``"ltr"`` / ``"rtl"``.

    Explicit ``ltr``/``rtl`` win; ``auto`` or ``None`` auto-detect from the script.
    """
    d = (direction or "auto").lower()
    if d in ("ltr", "rtl"):
        return d
    return "rtl" if has_rtl(text) else "ltr"


def resolve_lang(lang: str | None, direction: str, text: str) -> str | None:
    """Explicit ``lang`` wins; otherwise tag detected Arabic-script RTL as ``ar`` so the
    renderer selects Arabic shaping/justification behaviour."""
    if lang:
        return lang
    return "ar" if direction == "rtl" and has_rtl(text) else None


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def bidi_attrs(
    text: str,
    *,
    direction: str | None = None,
    lang: str | None = None,
    anchor: str = "middle",
    baseline: str = "central",
) -> str:
    """SVG ``<text>`` attributes for ``text``: anchoring plus bidi ``direction``/``xml:lang``.

    ``direction`` is emitted only when it resolves to RTL or was set explicitly, so LTR
    output is unchanged from before Phase 4 (no baseline churn)."""
    parts = [f'text-anchor="{anchor}"', f'dominant-baseline="{baseline}"']
    explicit = (direction or "").lower() in ("ltr", "rtl")
    eff = resolve_direction(direction, text)
    if eff == "rtl" or explicit:
        parts.append(f'direction="{eff}"')
    eff_lang = resolve_lang(lang, eff, text)
    if eff_lang:
        parts.append(f'xml:lang="{_esc(eff_lang)}"')
    return " ".join(parts)


def label_attrs(
    label: Label, *, anchor: str = "middle", baseline: str = "central"
) -> str:
    """Bidi/anchoring attributes for a :class:`Label` (delegates to :func:`bidi_attrs`)."""
    return bidi_attrs(
        label.text,
        direction=label.direction,
        lang=label.lang,
        anchor=anchor,
        baseline=baseline,
    )
