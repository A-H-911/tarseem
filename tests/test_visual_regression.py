"""Visual regression (Phase 3, 09 §1): rendered PNGs must match committed baselines.

Two layers:
1. compare_png unit tests — synthetic images, OS-independent, prove the diff detects a
   change as small as a single pixel and a size mismatch.
2. Baseline comparison — render each Node-free golden to PNG and pixel-diff it against the
   committed baseline for THIS platform. Baselines are OS-specific (Chromium rasterises
   fonts per platform), so the suite skips when no baseline exists for sys.platform;
   regenerate with scripts/regen_baselines.py (an explicit, reviewed action — R-21).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from PIL import Image

from tarseem.engine import Engine
from tarseem.visualtest import compare_png

ROOT = Path(__file__).resolve().parent.parent
BASELINE_SAMPLES = ["sequence-login", "swimlane-bug-triage", "swimlane-pipeline",
                    "swimlane-phases"]


# ---- compare_png unit tests (OS-independent) --------------------------------
def _solid(path: Path, size, color) -> None:
    Image.new("RGB", size, color).save(path)


def test_identical_images_match(tmp_path):
    a, b = tmp_path / "a.png", tmp_path / "b.png"
    _solid(a, (20, 20), (10, 120, 80))
    _solid(b, (20, 20), (10, 120, 80))
    r = compare_png(a, b)
    assert r.matches and r.diff_pixels == 0 and r.ratio == 0.0


def test_single_pixel_change_is_detected(tmp_path):
    a, b = tmp_path / "a.png", tmp_path / "b.png"
    _solid(a, (20, 20), (255, 255, 255))
    img = Image.new("RGB", (20, 20), (255, 255, 255))
    img.putpixel((5, 5), (0, 0, 0))  # flip one pixel
    img.save(b)
    r = compare_png(a, b)
    assert not r.matches and r.diff_pixels == 1


def test_tolerance_absorbs_subpixel_jitter(tmp_path):
    a, b = tmp_path / "a.png", tmp_path / "b.png"
    _solid(a, (10, 10), (100, 100, 100))
    _solid(b, (10, 10), (102, 101, 100))  # +2/+1/0 per channel
    assert compare_png(a, b, tolerance=0).diff_pixels == 100
    assert compare_png(a, b, tolerance=2).diff_pixels == 0  # within tolerance


def test_size_mismatch_reports_full_diff(tmp_path):
    a, b = tmp_path / "a.png", tmp_path / "b.png"
    _solid(a, (10, 10), (0, 0, 0))
    _solid(b, (12, 10), (0, 0, 0))
    r = compare_png(a, b)
    assert r.size_mismatch and r.ratio == 1.0


def test_diff_image_is_written(tmp_path):
    a, b = tmp_path / "a.png", tmp_path / "b.png"
    _solid(a, (8, 8), (255, 255, 255))
    img = Image.new("RGB", (8, 8), (255, 255, 255))
    img.putpixel((1, 1), (0, 0, 0))
    img.save(b)
    out = tmp_path / "diff.png"
    compare_png(a, b, diff_out=out)
    assert out.exists()


# ---- baseline comparison (platform-gated) -----------------------------------
def _baseline_dir() -> Path:
    return ROOT / "tests" / "baselines" / sys.platform


requires_baselines = pytest.mark.skipif(
    not _baseline_dir().exists(),
    reason=f"no committed baselines for platform '{sys.platform}' "
           f"(regenerate with scripts/regen_baselines.py)",
)


# Same OS + same Chromium => byte-identical (A3), so the baseline diff is normally 0. The
# tolerance absorbs single-level anti-aliasing jitter from a Chromium build drift; the ratio
# gate is set tight (0.1%) because a real change is sharp/high-contrast and clears the
# tolerance everywhere it touches. Empirically a 2px head-border change is ~0.55% — caught.
_AA_TOLERANCE = 8
_MAX_DIFF_RATIO = 0.001  # 0.1% of pixels


@requires_baselines
@pytest.mark.parametrize("name", BASELINE_SAMPLES)
def test_render_matches_baseline(name, tmp_path):
    spec = json.loads((ROOT / "examples" / f"{name}.json").read_text(encoding="utf-8"))
    Engine().render(spec).export(["png"], tmp_path, name)
    current = tmp_path / f"{name}.png"
    baseline = _baseline_dir() / f"{name}.png"
    result = compare_png(
        baseline, current, tolerance=_AA_TOLERANCE, diff_out=tmp_path / f"{name}.diff.png"
    )
    assert result.ratio <= _MAX_DIFF_RATIO, (
        f"{name}: {result.diff_pixels}/{result.total_pixels} px changed "
        f"({result.ratio:.3%}) vs baseline (size_mismatch={result.size_mismatch}); "
        f"review {tmp_path / f'{name}.diff.png'}"
    )
