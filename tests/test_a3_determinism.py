"""A3 — SVG + PNG export deterministic across runs (same engine versions).

Same spec ⇒ identical bytes (invariant 7). The strong check renders the same spec in
two subprocesses with different PYTHONHASHSEED: set/frozenset iteration order (e.g. the
font-subset codepoint set) must never leak into the output bytes.
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import textwrap

import pytest

from tarseem.layout.lanegrid import LaneGridLayout
from tarseem.measure import measure_graph
from tarseem.model import compile_spec
from tarseem.render import render_svg

requires_node = pytest.mark.skipif(
    shutil.which("node") is None, reason="Node.js runtime not on PATH"
)


def _render_swimlane(path: str) -> str:
    import json
    from pathlib import Path

    spec = json.loads(Path(path).read_text(encoding="utf-8"))
    return render_svg(LaneGridLayout().layout(measure_graph(compile_spec(spec))))


def test_svg_identical_in_process():
    a = _render_swimlane("examples/swimlane-pipeline.json")
    b = _render_swimlane("examples/swimlane-pipeline.json")
    assert a == b


def _render_in_subprocess(hash_seed: str) -> str:
    script = textwrap.dedent(
        """
        import json, hashlib
        from pathlib import Path
        from tarseem.model import compile_spec
        from tarseem.measure import measure_graph
        from tarseem.layout.lanegrid import LaneGridLayout
        from tarseem.render import render_svg
        spec = json.loads(Path("examples/swimlane-pipeline.json").read_text(encoding="utf-8"))
        svg = render_svg(LaneGridLayout().layout(measure_graph(compile_spec(spec))))
        print(hashlib.sha256(svg.encode("utf-8")).hexdigest())
        """
    )
    env = {**_base_env(), "PYTHONHASHSEED": hash_seed}
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    return result.stdout.strip()


def _base_env() -> dict:
    import os

    return dict(os.environ)


def test_svg_identical_across_hash_seeds():
    """Embedded font subset (set-ordered codepoints) must not vary by hash seed."""
    digest_a = _render_in_subprocess("0")
    digest_b = _render_in_subprocess("12345")
    assert digest_a == digest_b


def test_font_subset_invariant_to_input_order():
    from tarseem.render.fonts import subset_woff2_datauri

    forward = subset_woff2_datauri(frozenset("abcdef"))
    # frozenset equality means same cache key; assert the function itself is stable
    again = subset_woff2_datauri(frozenset("fedcba"))
    assert forward == again


@requires_node
def test_graph_svg_identical_in_process():
    import json
    from pathlib import Path

    from tarseem.layout.elk import ElkLayout

    spec = json.loads(Path("examples/flowchart.json").read_text(encoding="utf-8"))
    g = measure_graph(compile_spec(spec))
    with ElkLayout() as elk:
        d1 = elk.layout(g)
        d2 = elk.layout(g)
    assert render_svg(d1) == render_svg(d2)


def test_png_bytes_identical_in_process():
    from tarseem.export import svg_to_png

    svg = _render_swimlane("examples/swimlane-pipeline.json")
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        p1 = svg_to_png(svg, Path(tmp) / "a.png")
        p2 = svg_to_png(svg, Path(tmp) / "b.png")
        h1 = hashlib.sha256(p1.read_bytes()).hexdigest()
        h2 = hashlib.sha256(p2.read_bytes()).hexdigest()
    assert h1 == h2
