"""Regression: textAsPaths glyphs were not vertically centered in shapes/title.

Reported bug (swimlane-document-rtl-paths.png): with ``export.svg.textAsPaths`` on, text
inside shapes and the title sat too high — not vertically centered like the ``<text>``
rendering.

Root cause was the render/export layer (``render/textpath.py``). The ``<text>`` writer uses
``dominant-baseline="central"`` (centre at y); the outline conversion placed the glyph
baseline at ``y - center_frac*size`` — the wrong sign — shifting glyphs *up* by ~2·0.366·
size (≈ 8.8px at 12px). The central point is (asc+desc)/2 *above* the baseline, so the
baseline must sit *below* y: ``baseline_y = y + center_frac*size``. (Not an upstream
limitation — our own outline math.)

This locks the baseline below the shape centre and the run vertically centred on it.
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest

from tarseem.engine import Engine
from tarseem.render.textpath import _glyph_set_and_metrics

HERE = Path(__file__).resolve().parent

requires_node = pytest.mark.skipif(
    shutil.which("node") is None, reason="Node.js runtime not on PATH (ELK graph families)"
)


def test_unit_baseline_is_below_center_for_central_alignment():
    from tarseem.render.textpath import text_to_paths

    _gs, _order, _upem, cf = _glyph_set_and_metrics()
    size, cy = 12.0, 100.0
    svg = text_to_paths(
        f'<text x="50" y="{cy}" font-size="{size}" text-anchor="middle">A</text>'
    )
    gy = float(re.search(r"translate\([-\d.]+,([-\d.]+)\)", svg).group(1))
    # baseline must be BELOW the centre (was above before the fix), by exactly center_frac*size
    assert gy > cy
    assert abs(gy - (cy + cf * size)) < 0.05


@requires_node
def test_textaspaths_label_centered_in_node_box():
    spec = json.loads((HERE / "textaspaths_vertical_centering.json").read_text(encoding="utf-8"))
    res = Engine().render({**spec, "export": {"svg": {"textAsPaths": True}}})
    n = res.diagram.nodes[0]
    _gs, _order, _upem, cf = _glyph_set_and_metrics()
    size = float((n.style.get("text") or {}).get("size", 12))
    center_y = n.y + n.height / 2  # diagram coords (writer's <g> uses diagram-local coords)
    # every glyph in the label shares one baseline; assert it equals centre + center_frac*size
    gys = [float(m) for m in re.findall(r"translate\([-\d.]+,([-\d.]+)\) scale", res.svg)]
    assert gys, "no glyph outlines emitted"
    baseline = max(set(gys), key=gys.count)  # the label's shared baseline
    assert abs(baseline - (center_y + cf * size)) < 1.0
