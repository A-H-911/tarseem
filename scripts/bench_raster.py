"""Benchmark the raster path: time the baseline corpus -> PNG and snapshot process churn.

Run before/after the Chromium-pool change to confirm the win (one launch, not per-spec) and that
no Chromium/Node processes are orphaned.

Usage (project venv):
    .venv/Scripts/python.exe scripts/bench_raster.py            # Windows
    .venv/bin/python scripts/bench_raster.py                    # macOS/Linux
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from tarseem.engine import Engine
from tarseem.export import svg_to_png

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = [
    "swimlane-pipeline", "swimlane-phases", "swimlane-bug-triage", "sequence-login",
    "swimlane-document-rtl", "swimlane-vertical-release", "swimlane-nested-delivery",
    "arabic-flowchart", "architecture", "flowchart", "dependency", "er-shop",
    "state-order-lifecycle", "deployment-web-stack", "class-shop", "mindmap-roadmap",
]


def _proc_count(name: str) -> int:
    """Count running processes named ``name`` (best-effort, cross-platform)."""
    try:
        if sys.platform == "win32":
            out = subprocess.run(
                ["tasklist", "/FI", f"IMAGENAME eq {name}.exe", "/NH"],
                capture_output=True, text=True, timeout=15,
            ).stdout
            return sum(1 for ln in out.splitlines() if name in ln.lower())
        out = subprocess.run(["pgrep", "-c", name], capture_output=True, text=True, timeout=15)
        return int(out.stdout.strip() or "0")
    except Exception:  # noqa: BLE001 - bench helper; missing tool just reports -1
        return -1


def main() -> int:
    have_node = shutil.which("node") is not None
    specs: list[tuple[str, dict]] = []
    for name in SAMPLES:
        p = ROOT / "examples" / f"{name}.json"
        if p.exists():
            specs.append((name, json.loads(p.read_text(encoding="utf-8"))))
    print(f"corpus: {len(specs)} specs (node={'yes' if have_node else 'no'})")
    print(f"before: chrome={_proc_count('chrome')} node={_proc_count('node')}")

    eng = Engine()
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        t0 = time.perf_counter()
        per: list[tuple[str, float]] = []
        for name, spec in specs:
            try:
                svg = eng.render(spec).svg
            except Exception as exc:  # noqa: BLE001 - skip a spec that needs an absent dep
                print(f"  [skip] {name}: {exc}")
                continue
            t = time.perf_counter()
            svg_to_png(svg, out / f"{name}.png")
            per.append((name, (time.perf_counter() - t) * 1000.0))
        total = time.perf_counter() - t0

    rendered = len(per)
    print(f"\nrendered {rendered} PNGs in {total:.1f}s "
          f"(avg {1000 * total / rendered:.0f} ms/png)" if rendered else "nothing rendered")
    if per:
        slowest = max(per, key=lambda x: x[1])
        print(f"slowest single raster: {slowest[0]} {slowest[1]:.0f} ms (~ the cold launch)")
    print(f"after:  chrome={_proc_count('chrome')} node={_proc_count('node')}")
    print("(re-run this snapshot a few seconds later; counts should match 'before' = no orphans)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
