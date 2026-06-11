"""Screenshot pixel-diff tooling for visual regression (Phase 3, 09 §1).

A pixelmatch-style comparator over two PNGs: counts pixels differing beyond a per-channel
tolerance, reports the changed-pixel ratio, and can write a highlighted diff image. The
regression suite renders a sample to PNG and compares it to a committed baseline; any
unintended geometry/style change shifts pixels and is caught.

Baselines are OS-specific (Chromium rasterizes fonts differently per platform), so callers
store and select baselines per ``sys.platform`` — see tests/baselines/<platform>/.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

__all__ = ["DiffResult", "compare_png"]

_DIFF_COLOR = (255, 0, 128)  # magenta highlight for changed pixels


@dataclass(frozen=True)
class DiffResult:
    width: int
    height: int
    diff_pixels: int
    total_pixels: int
    size_mismatch: bool

    @property
    def ratio(self) -> float:
        """Fraction of pixels that changed (1.0 when the images differ in size)."""
        if self.size_mismatch:
            return 1.0
        return self.diff_pixels / self.total_pixels if self.total_pixels else 0.0

    @property
    def matches(self) -> bool:
        return not self.size_mismatch and self.diff_pixels == 0

    def to_dict(self) -> dict:
        return {
            "width": self.width,
            "height": self.height,
            "diff_pixels": self.diff_pixels,
            "total_pixels": self.total_pixels,
            "size_mismatch": self.size_mismatch,
            "ratio": self.ratio,
        }


def compare_png(
    baseline: str | Path,
    current: str | Path,
    *,
    tolerance: int = 0,
    diff_out: str | Path | None = None,
) -> DiffResult:
    """Compare two PNGs pixel-by-pixel.

    ``tolerance`` is the max per-channel absolute difference (0..255) still counted as
    equal — a small value absorbs sub-pixel anti-aliasing jitter. If ``diff_out`` is given
    and the images are the same size, a diff image (changed pixels highlighted) is written.
    """
    base = Image.open(baseline).convert("RGB")
    cur = Image.open(current).convert("RGB")
    if base.size != cur.size:
        return DiffResult(
            width=base.width, height=base.height,
            diff_pixels=base.width * base.height, total_pixels=base.width * base.height,
            size_mismatch=True,
        )

    w, h = base.size
    braw = base.tobytes()  # raw RGB bytes, row-major (version-stable, fast)
    craw = cur.tobytes()
    out = bytearray(braw) if diff_out else None
    dr, dg, db = _DIFF_COLOR

    diff_count = 0
    for i in range(0, len(braw), 3):
        changed = (
            abs(braw[i] - craw[i]) > tolerance
            or abs(braw[i + 1] - craw[i + 1]) > tolerance
            or abs(braw[i + 2] - craw[i + 2]) > tolerance
        )
        if changed:
            diff_count += 1
            if out is not None:
                out[i], out[i + 1], out[i + 2] = dr, dg, db

    if out is not None and diff_out is not None:
        Path(diff_out).parent.mkdir(parents=True, exist_ok=True)
        Image.frombytes("RGB", (w, h), bytes(out)).save(diff_out)

    return DiffResult(
        width=w, height=h, diff_pixels=diff_count, total_pixels=w * h, size_mismatch=False
    )
