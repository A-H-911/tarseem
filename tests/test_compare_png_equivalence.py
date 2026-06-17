"""The vectorized ``compare_png`` must match the original per-pixel implementation exactly.

We keep an inlined copy of the old pure-Python loop as the reference oracle and assert the
NumPy version agrees on ``diff_pixels`` / ``ratio`` / ``size_mismatch`` across random image pairs
and tolerances, and that the written diff image is byte-identical.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from tarseem.visualtest import _DIFF_COLOR, compare_png


def _reference(baseline: Path, current: Path, tolerance: int, diff_out: Path | None):
    """The original per-pixel loop — the behavioral oracle (returns (diff_pixels, total, mism))."""
    base = Image.open(baseline).convert("RGB")
    cur = Image.open(current).convert("RGB")
    if base.size != cur.size:
        return base.width * base.height, base.width * base.height, True
    w, h = base.size
    braw, craw = base.tobytes(), cur.tobytes()
    out = bytearray(braw) if diff_out else None
    dr, dg, db = _DIFF_COLOR
    diff = 0
    for i in range(0, len(braw), 3):
        if (abs(braw[i] - craw[i]) > tolerance
                or abs(braw[i + 1] - craw[i + 1]) > tolerance
                or abs(braw[i + 2] - craw[i + 2]) > tolerance):
            diff += 1
            if out is not None:
                out[i], out[i + 1], out[i + 2] = dr, dg, db
    if out is not None and diff_out is not None:
        Image.frombytes("RGB", (w, h), bytes(out)).save(diff_out)
    return diff, w * h, False


def _noisy_pair(tmp: Path, seed: int, size=(11, 7)):
    """A deterministic baseline + a perturbed current (varied per-channel deltas + some equal)."""
    import random

    rng = random.Random(seed)
    w, h = size
    base = Image.new("RGB", size)
    cur = Image.new("RGB", size)
    for y in range(h):
        for x in range(w):
            r, g, b = rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255)
            base.putpixel((x, y), (r, g, b))
            # deltas spanning 0 (equal), small (within tolerance), and large
            d = rng.choice([0, 0, 1, 2, 3, 5, 40, 200])
            cur.putpixel((x, y), (min(255, r + d), max(0, g - d), b))
    a, c = tmp / f"a{seed}.png", tmp / f"c{seed}.png"
    base.save(a)
    cur.save(c)
    return a, c


@pytest.mark.parametrize("seed", range(6))
@pytest.mark.parametrize("tolerance", [0, 2, 8])
def test_vectorized_equals_reference(tmp_path, seed, tolerance):
    a, c = _noisy_pair(tmp_path, seed)
    ref_diff, ref_total, ref_mism = _reference(a, c, tolerance, None)
    got = compare_png(a, c, tolerance=tolerance)
    assert got.diff_pixels == ref_diff
    assert got.total_pixels == ref_total
    assert got.size_mismatch == ref_mism
    assert got.ratio == pytest.approx(ref_diff / ref_total)


def test_size_mismatch_matches_reference(tmp_path):
    Image.new("RGB", (10, 8), (0, 0, 0)).save(tmp_path / "a.png")
    Image.new("RGB", (12, 8), (0, 0, 0)).save(tmp_path / "b.png")
    got = compare_png(tmp_path / "a.png", tmp_path / "b.png")
    assert got.size_mismatch and got.ratio == 1.0


def test_diff_image_bytes_identical_to_reference(tmp_path):
    a, c = _noisy_pair(tmp_path, seed=99)
    ref_out, got_out = tmp_path / "ref.png", tmp_path / "got.png"
    _reference(a, c, tolerance=4, diff_out=ref_out)
    compare_png(a, c, tolerance=4, diff_out=got_out)
    assert got_out.read_bytes() == ref_out.read_bytes()
