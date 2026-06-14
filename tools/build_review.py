"""Build the review bundle: every diagram in every format, organized per format type.

Layout under the output dir (default `out/`):

    index.html                 one page — every diagram across every format, side by side
    README.md                  describes this structure
    svg/<name>.svg             engine canonical render (the source of truth)
    png/<name>.png             engine render rasterized (the visual reference)
    drawio/<name>.drawio       editable draw.io file
    drawio/<name>.png          how draw.io itself renders it (embedded Cairo)
    drawio/<name>.drawio.report.json
    pptx/<name>.pptx           native PowerPoint deck
    pptx/<name>.pptx.report.json

PPTX has no headless renderer, so it shows as a download tile (open in PowerPoint).

Usage:
    python tools/build_review.py examples/*.json
    python tools/build_review.py examples/*.json -o out
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
from tarseem.export import svg_to_png  # noqa: E402

_FORMATS = ("svg", "png", "drawio", "pptx")


def _safe(fn, label: str) -> str | None:
    """Run a write step; on a locked file (PowerPoint open) or render error, skip + report."""
    try:
        fn()
        return None
    except PermissionError:
        print(f"[locked] {label} (file open elsewhere — skipped)")
        return "locked"
    except Exception as exc:  # render is best-effort for the bundle
        print(f"[warn]  {label}: {exc}")
        return str(exc)


def _build_one(spec_path: Path, out: Path, engine: Engine) -> dict:
    name = spec_path.stem
    result = engine.render(json.loads(spec_path.read_text(encoding="utf-8")))
    entry: dict = {"name": name, "type": result.diagram.diagram_type, "drawio_png": False}
    svg_text = result.to_svg(provenance=True)

    _safe(lambda: (out / "svg" / f"{name}.svg").write_text(svg_text, encoding="utf-8"), f"{name}.svg")
    _safe(lambda: svg_to_png(svg_text, out / "png" / f"{name}.png"), f"{name}.png")

    if _safe(lambda: result.export(["drawio"], out / "drawio", name=name), f"{name}.drawio") is None:
        if _safe(
            lambda: render_to_png(
                out / "drawio" / f"{name}.drawio", out / "drawio" / f"{name}.png",
                Path(VIEWER_JS), inject_font=False,
            ),
            f"{name}.drawio.png",
        ) is None:
            entry["drawio_png"] = True
    _safe(lambda: result.export(["pptx"], out / "pptx", name=name), f"{name}.pptx")

    rep = result.reports
    entry["drawio_lossy"] = bool(rep.get("drawio") and rep["drawio"].lossy)
    entry["pptx_lossy"] = bool(rep.get("pptx") and rep["pptx"].lossy)
    return entry


def _tile(name: str, fmt: str, entry: dict) -> str:
    if fmt == "png":
        return (f'<figure><figcaption>engine (source of truth)</figcaption>'
                f'<img src="png/{name}.png" loading="lazy" alt="{name} engine">'
                f'<nav><a href="svg/{name}.svg">svg</a></nav></figure>')
    if fmt == "drawio":
        img = (f'<img src="drawio/{name}.png" loading="lazy" alt="{name} draw.io">'
               if entry["drawio_png"] else '<div class="na">no render</div>')
        rep = (f' · <a href="drawio/{name}.drawio.report.json">report ⚠</a>'
               if entry["drawio_lossy"] else "")
        return (f'<figure><figcaption>draw.io</figcaption>{img}'
                f'<nav><a href="drawio/{name}.drawio">open .drawio</a>{rep}</nav></figure>')
    # pptx — no preview; download tile
    rep = (f' · <a href="pptx/{name}.pptx.report.json">report ⚠</a>'
           if entry["pptx_lossy"] else "")
    return (f'<figure><figcaption>PowerPoint</figcaption>'
            f'<a class="dl" href="pptx/{name}.pptx">⬇ open {name}.pptx</a>'
            f'<nav>open in PowerPoint{rep}</nav></figure>')


def _index_html(entries: list[dict]) -> str:
    cards = "".join(
        f'<section class="card"><h2>{e["name"]} <span class="tag">{e["type"]}</span></h2>'
        f'<div class="grid">{_tile(e["name"], "png", e)}{_tile(e["name"], "drawio", e)}'
        f'{_tile(e["name"], "pptx", e)}</div></section>'
        for e in entries
    )
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tarseem — review (all diagrams × all formats)</title>
<style>
:root {{ color-scheme: dark; }}
body {{ margin:0; font:15px/1.5 system-ui,sans-serif; background:#11151c; color:#e6edf3; }}
header {{ padding:18px 26px; border-bottom:1px solid #232b36; position:sticky; top:0;
  background:#11151cdd; backdrop-filter:blur(6px); }}
header h1 {{ margin:0; font-size:18px; }} header p {{ margin:4px 0 0; color:#8b97a7; }}
main {{ padding:22px; display:grid; gap:22px; }}
.card {{ background:#161b23; border:1px solid #232b36; border-radius:12px; padding:16px 18px; }}
.card h2 {{ margin:0 0 12px; font-size:16px; }}
.tag {{ font-size:11px; color:#8b97a7; border:1px solid #2c3644; border-radius:999px;
  padding:2px 9px; margin-left:6px; }}
.grid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:14px; }}
figure {{ margin:0; }} figcaption {{ font-size:12px; color:#8b97a7; margin-bottom:6px; }}
img {{ width:100%; height:auto; background:#fff; border-radius:8px; display:block; }}
.na, .dl {{ display:grid; place-items:center; height:150px; border:1px dashed #2c3644;
  border-radius:8px; color:#8b97a7; text-decoration:none; }}
.dl {{ color:#5aa0ff; font-weight:600; }} .dl:hover {{ background:#1b2230; }}
nav {{ margin-top:8px; font-size:13px; color:#8b97a7; }}
nav a {{ color:#5aa0ff; text-decoration:none; }} nav a:hover {{ text-decoration:underline; }}
@media (max-width:900px) {{ .grid {{ grid-template-columns:1fr; }} }}
</style></head><body>
<header><h1>Tarseem — review</h1>
<p>Every diagram across every format. Engine (SVG→PNG) is the source of truth; draw.io and PPTX
are compared against it.</p></header>
<main>{cards}</main></body></html>"""


_README = """# `out/` — review bundle (generated, gitignored)

All generated; regenerate with `python tools/build_review.py examples/*.json`. The engine SVG is
the source of truth; other formats are compared against it.

## Structure — one folder per format

| Path | Format |
|------|--------|
| `index.html` | **open this** — every diagram across every format, side by side |
| `svg/<name>.svg` | engine canonical render (source of truth) |
| `png/<name>.png` | engine render rasterized (visual reference) |
| `drawio/<name>.drawio` | editable draw.io file (open in diagrams.net) |
| `drawio/<name>.png` | how draw.io itself renders it |
| `drawio/<name>.drawio.report.json` | draw.io CapabilityReport (only when lossy) |
| `pptx/<name>.pptx` | native PowerPoint deck (open in Microsoft PowerPoint) |
| `pptx/<name>.pptx.report.json` | PPTX CapabilityReport (only when lossy) |

PPTX has no headless renderer, so `index.html` shows it as a download tile — open the `.pptx`
in PowerPoint (see `docs/pptx-manual-checklist.md`).

Close any open `.pptx`/`.drawio` before regenerating, or the rebuild logs `[locked]` and skips it.
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the per-format review bundle.")
    parser.add_argument("specs", nargs="+", help="spec .json files")
    parser.add_argument("-o", "--out", default="out", help="output dir (default: out)")
    args = parser.parse_args(argv)
    out = Path(args.out)
    for fmt in _FORMATS:
        (out / fmt).mkdir(parents=True, exist_ok=True)
    engine = Engine()
    entries: list[dict] = []
    for raw in args.specs:
        path = Path(raw)
        if not path.exists():
            print(f"[skip] {path}")
            continue
        try:
            entries.append(_build_one(path, out, engine))
            print(f"[ok]   {path.name}")
        except Exception as exc:
            print(f"[FAIL] {path.name}: {exc}")
    (out / "index.html").write_text(_index_html(entries), encoding="utf-8")
    (out / "README.md").write_text(_README, encoding="utf-8")
    print(f"\nreview bundle: {out / 'index.html'}  ({len(entries)} diagrams)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
