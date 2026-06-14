"""Build a single, clean sign-off bundle for diagram review (answers "which folder?").

For each spec it writes, into ONE folder (`out/review/` by default):
  <name>.engine.svg / <name>.engine.png   canonical engine render (the source of truth)
  <name>.drawio                            editable file — open in diagrams.net
  <name>.drawio.png                        how draw.io renders that file (Option-A viewer)
  <name>.report.json                       fidelity / CapabilityReport
plus index.html — engine vs draw.io side-by-side for every diagram, with download links.

`out/` is gitignored scratch; `examples/` is the committed spec corpus. THIS bundle
(`out/review/index.html`) is the thing to open for visual sign-off.

Usage:
    python tools/build_review.py examples/swimlane-pipeline.json examples/er-shop.json
    python tools/build_review.py examples/*.json -o out/review
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verify_drawio import VIEWER_JS, render_to_png  # noqa: E402

from tarseem import Engine  # noqa: E402

# Every built-in family now has a draw.io writer (sequence draws lifelines + activations).
_DRAWIO_FAMILIES_SKIP: set[str] = set()


def _build_one(spec_path: Path, out_dir: Path, engine: Engine) -> dict:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    name = spec_path.stem
    result = engine.render(spec)
    entry: dict = {"name": name, "type": result.diagram.diagram_type, "drawio": False}

    (out_dir / f"{name}.engine.svg").write_text(result.to_svg(provenance=True), encoding="utf-8")
    from tarseem.export import svg_to_png

    svg_to_png(result.to_svg(provenance=True), out_dir / f"{name}.engine.png")

    if result.diagram.diagram_type not in _DRAWIO_FAMILIES_SKIP:
        result.export(["drawio"], out_dir, name=name)
        drawio_path = out_dir / f"{name}.drawio"
        try:
            render_to_png(drawio_path, out_dir / f"{name}.drawio.png", Path(VIEWER_JS))
            entry["drawio"] = True
        except Exception as exc:  # render is best-effort for the bundle
            entry["drawio_error"] = str(exc)
        report = result.reports.get("drawio")
        if report is not None:
            (out_dir / f"{name}.report.json").write_text(
                json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
            )
            entry["lossy"] = report.lossy
    return entry


def _index_html(entries: list[dict]) -> str:
    cards = []
    for e in entries:
        name = e["name"]
        drawio_col = (
            f'<figure><figcaption>draw.io</figcaption>'
            f'<img src="{name}.drawio.png" loading="lazy" alt="{name} draw.io"></figure>'
            if e.get("drawio")
            else '<figure class="na"><figcaption>draw.io</figcaption>'
            '<div class="na-box">engine-only family</div></figure>'
        )
        links = [f'<a href="{name}.engine.svg">engine.svg</a>']
        if e.get("drawio"):
            links.append(f'<a href="{name}.drawio">open .drawio</a>')
        if "lossy" in e:
            links.append(f'<a href="{name}.report.json">report{" ⚠" if e["lossy"] else ""}</a>')
        cards.append(
            f'<section class="card"><h2>{name} <span class="tag">{e["type"]}</span></h2>'
            f'<div class="pair"><figure><figcaption>engine (canonical)</figcaption>'
            f'<img src="{name}.engine.png" loading="lazy" alt="{name} engine"></figure>'
            f'{drawio_col}</div><nav>{" · ".join(links)}</nav></section>'
        )
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tarseem — diagram review</title>
<style>
:root {{ color-scheme: dark; }}
body {{ margin:0; font:15px/1.5 system-ui,sans-serif; background:#11151c; color:#e6edf3; }}
header {{ padding:20px 28px; border-bottom:1px solid #232b36; position:sticky; top:0;
  background:#11151cdd; backdrop-filter:blur(6px); }}
header h1 {{ margin:0; font-size:18px; }} header p {{ margin:4px 0 0; color:#8b97a7; }}
main {{ padding:24px; display:grid; gap:24px; }}
.card {{ background:#161b23; border:1px solid #232b36; border-radius:12px; padding:18px 20px; }}
.card h2 {{ margin:0 0 14px; font-size:16px; }}
.tag {{ font-size:11px; color:#8b97a7; border:1px solid #2c3644; border-radius:999px;
  padding:2px 9px; margin-left:6px; vertical-align:middle; }}
.pair {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
figure {{ margin:0; }} figcaption {{ font-size:12px; color:#8b97a7; margin-bottom:6px; }}
img {{ width:100%; height:auto; background:#fff; border-radius:8px; display:block; }}
.na-box {{ display:grid; place-items:center; height:140px; color:#5c6675;
  border:1px dashed #2c3644; border-radius:8px; }}
nav {{ margin-top:12px; font-size:13px; }}
nav a {{ color:#5aa0ff; text-decoration:none; }} nav a:hover {{ text-decoration:underline; }}
@media (max-width:820px) {{ .pair {{ grid-template-columns:1fr; }} }}
</style></head><body>
<header><h1>Tarseem — diagram review</h1>
<p>Engine (canonical) vs draw.io, per diagram.
Open any <code>.drawio</code> in diagrams.net.</p></header>
<main>{"".join(cards)}</main></body></html>"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the diagram review bundle.")
    parser.add_argument("specs", nargs="+", help="spec .json files")
    parser.add_argument("-o", "--out", default="out/review", help="output dir")
    args = parser.parse_args(argv)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    engine = Engine()
    entries: list[dict] = []
    for raw in args.specs:
        path = Path(raw)
        if not path.exists():
            print(f"[skip] {path}")
            continue
        try:
            entries.append(_build_one(path, out_dir, engine))
            print(f"[ok]   {path.name}")
        except Exception as exc:
            print(f"[FAIL] {path.name}: {exc}")
    (out_dir / "index.html").write_text(_index_html(entries), encoding="utf-8")
    print(f"\nreview bundle: {out_dir / 'index.html'}  ({len(entries)} diagrams)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
