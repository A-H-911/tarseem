"""Phase 4 — Arabic & RTL: measurement, bidi resolution, RL mirroring, export options.

Covers the 07 §4 test hooks that are deterministic and Node-free (the ELK Arabic flowchart/
architecture renders are exercised by the gallery E2E + the visual-regression baselines).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from tarseem.doctor import check_arabic_shaping, check_raqm
from tarseem.engine import Engine
from tarseem.measure import TextMeasurer
from tarseem.model import compile_spec
from tarseem.render.text import resolve_direction
from tarseem.themes import get_theme

ROOT = Path(__file__).resolve().parent.parent
_AR = "مقدّم الطلب"  # diacritic-bearing (shadda on مقدّم)


def _raqm_available() -> bool:
    try:
        from PIL import features

        return bool(features.check("raqm"))
    except Exception:  # noqa: BLE001 - Pillow/raqm absent -> cross-check simply skipped
        return False


def _ex(name: str) -> dict:
    return json.loads((ROOT / "examples" / f"{name}.json").read_text(encoding="utf-8"))


# ---- measurement (07 §1, §4) ------------------------------------------------
def test_arabic_shapes_to_positive_advance():
    m = TextMeasurer()
    # diacritized word is wider than a single base letter -> shaping ran, marks counted
    assert m.width(_AR, 12) > m.width("م", 12) > 0


def test_node_width_is_at_least_measured_arabic_text():
    # 07 §4 assertion: a node is never narrower than its shaped label
    m = TextMeasurer()
    d = Engine().render(_ex("swimlane-document-rtl")).diagram
    for n in d.nodes:
        size = float((n.style.get("text") or {}).get("size", 12))
        assert n.width >= m.width(n.label.text, size), f"{n.id} clips its label"


@pytest.mark.skipif(
    not _raqm_available(),
    reason="Pillow+libraqm not available; uharfbuzz is the primary measurer",
)
def test_raqm_cross_check_agrees_with_uharfbuzz():
    # secondary cross-check where libraqm exists: shaped advances agree within tolerance
    from PIL import ImageFont

    from tarseem.measure import default_font_path

    size = 32
    hb_w = TextMeasurer().width(_AR, size)
    pil = ImageFont.truetype(str(default_font_path()), size, layout_engine=ImageFont.Layout.RAQM)
    raqm_w = pil.getlength(_AR)
    assert abs(hb_w - raqm_w) <= 0.06 * size  # within ~2px at 32px


# ---- bidi base-direction resolution (07 §2) ---------------------------------
def test_direction_autodetects_arabic_and_latin():
    assert resolve_direction(None, _AR) == "rtl"
    assert resolve_direction("auto", _AR) == "rtl"
    assert resolve_direction(None, "Hello") == "ltr"


def test_explicit_direction_overrides_detection():
    assert resolve_direction("ltr", _AR) == "ltr"
    assert resolve_direction("rtl", "Hello") == "rtl"


def test_arabic_labels_emit_rtl_attrs_latin_stays_bare():
    svg = Engine().render(_ex("swimlane-document-rtl")).svg
    assert 'direction="rtl"' in svg and 'xml:lang="ar"' in svg
    # a pure-LTR diagram must not gain a direction attribute (no baseline churn)
    ltr = Engine().render(_ex("swimlane-bug-triage")).svg
    assert 'direction="rtl"' not in ltr


# ---- RL mirroring = geometry only (analysis.md §Reference-2) -----------------
def test_rl_swimlane_mirrors_flow_header_and_badges():
    d = Engine().render(_ex("swimlane-document-rtl")).diagram
    assert d.direction == "RL"
    by_x = sorted(d.nodes, key=lambda n: n.x)
    # first step (badge exempt 'submit') is right-most, last step is left-most => right→left
    assert by_x[-1].id == "submit" and by_x[0].id == "receive"
    svg = Engine().render(_ex("swimlane-document-rtl")).svg
    # header chip + separator on the right half (RTL); badge circles flip to the LEFT corner.
    chip = re.search(r'<rect x="([\d.]+)"[^>]*rx="8" fill', svg)
    assert chip and float(chip.group(1)) > d.width / 2
    badge_circles = [
        float(m) for m in re.findall(r'<circle cx="([\d.]+)" cy="[\d.]+" r="11"', svg)
    ]
    assert badge_circles and min(badge_circles) < d.width / 2  # a badge sits on the left


def test_ltr_swimlane_keeps_left_header():
    svg = Engine().render(_ex("swimlane-bug-triage")).svg
    chip = re.search(r'<rect x="([\d.]+)"[^>]*rx="8" fill', svg)
    d = Engine().render(_ex("swimlane-bug-triage")).diagram
    assert chip and float(chip.group(1)) < d.width / 2  # header on the left


# ---- themes are a palette swap over invariant geometry (F4) ------------------
def test_theme_swaps_palette_and_title_not_geometry():
    base = _ex("swimlane-bug-triage")
    geo_default = [(n.id, n.x, n.y, n.width) for n in Engine().render(base).diagram.nodes]
    corp = {**base, "theme": {"ref": "corporate"}}
    rc = Engine().render(corp)
    geo_corp = [(n.id, n.x, n.y, n.width) for n in rc.diagram.nodes]
    assert geo_default == geo_corp  # identical geometry
    assert get_theme("corporate")["title"]["fill"] in rc.svg  # palette changed


def test_compile_resolves_theme_by_ref_or_name():
    g_ref = compile_spec({"specVersion": "0.1", "diagramType": "flowchart",
                          "theme": {"ref": "monochrome"}, "nodes": []})
    g_name = compile_spec({"specVersion": "0.1", "diagramType": "flowchart",
                           "theme": {"name": "monochrome"}, "nodes": []})
    assert g_ref.theme["name"] == g_name.theme["name"] == "monochrome"


# ---- export options (07 §2) -------------------------------------------------
def test_text_as_paths_outlines_arabic_and_drops_text():
    spec = {**_ex("swimlane-document-rtl"), "export": {"svg": {"textAsPaths": True}}}
    svg = Engine().render(spec).svg
    assert "<text" not in svg and svg.count("<path") > 20
    assert "@font-face" not in svg  # outlines make the embedded subset dead weight


def test_embed_fonts_false_drops_subset_for_stack():
    spec = {**_ex("swimlane-document-rtl"), "export": {"svg": {"embedFonts": False}}}
    svg = Engine().render(spec).svg
    assert "@font-face" not in svg and "Noto Sans Arabic" in svg


def test_default_export_still_embeds_and_keeps_text():
    svg = Engine().render(_ex("swimlane-document-rtl")).svg
    assert "@font-face" in svg and "<text" in svg


# ---- doctor (07 §1) ---------------------------------------------------------
def test_doctor_arabic_shaping_passes_with_bundled_font():
    assert check_arabic_shaping().ok


def test_doctor_raqm_is_informational_never_fails():
    assert check_raqm().ok  # absent libraqm must not fail the report
