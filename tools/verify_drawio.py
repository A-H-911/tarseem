"""Render-fidelity verification for the draw.io writer (dev-only; NOT packaged).

The .drawio our engine emits must render correctly in *draw.io's own engine*, not just parse
as XML. This harness loads each .drawio into the official draw.io viewer (mxGraph) inside the
same headless Chromium we already use for PNG export, and screenshots the result — so the
agent can eyeball blank shapes, rerouted edges, RTL, and bad style keys before a human review.

This is Option A of the Phase-6 verification plan: no install, draw.io's real renderer, an
image artifact the agent can actually inspect. Option B (draw.io Desktop / Docker CLI) is the
authoritative final gate.

Usage:
    python tools/verify_drawio.py out/drawio-review/*.drawio --out out/drawio-verify
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

VIEWER_JS = Path(".cache/drawio/viewer-static.min.js")
_RENDER_JS = """
(cfg) => {
  const div = document.createElement('div');
  div.className = 'mxgraph';
  div.style.background = '#ffffff';
  div.setAttribute('data-mxgraph', JSON.stringify(cfg));
  document.body.appendChild(div);
  // GraphViewer is defined by viewer-static.min.js; scan + render our div.
  if (typeof GraphViewer !== 'undefined') GraphViewer.processElements();
}
"""


def _diagram_xml(drawio_text: str) -> str:
    """The <mxfile> payload, minus our leading provenance comment (confuses the viewer)."""
    text = drawio_text.lstrip()
    if text.startswith("<!--"):
        end = text.find("-->")
        if end != -1:
            text = text[end + 3 :].lstrip()
    return text


def _cairo_font_face() -> str:
    """@font-face for 'Cairo' from the bundled OFL font, so the viewer renders draw.io's
    `fontFamily=Cairo` cells in the SAME face the SVG embeds. draw.io itself can't embed fonts
    (fonts ceiling); this makes the REVIEW reflect draw.io *with* Cairo available (as draw.io
    Desktop does once the bundled font is installed) instead of the headless browser's fallback."""
    import base64

    from tarseem.measure import default_font_path

    data = base64.b64encode(default_font_path().read_bytes()).decode("ascii")
    return f"@font-face{{font-family:'Cairo';src:url(data:font/ttf;base64,{data});}}"


def render_to_png(drawio_path: Path, out_png: Path, viewer_js: Path) -> Path:
    from playwright.sync_api import sync_playwright

    cfg = {
        "xml": _diagram_xml(drawio_path.read_text(encoding="utf-8")),
        "zoom": 1,
        "highlight": "none",
        "nav": False,
        "resize": True,
        "toolbar": None,
    }
    out_png.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(device_scale_factor=2)
            page.set_content("<!doctype html><meta charset='utf-8'><body style='margin:0'></body>")
            page.add_style_tag(content=_cairo_font_face())
            page.add_script_tag(path=str(viewer_js))
            page.evaluate(_RENDER_JS, cfg)
            page.wait_for_selector(".mxgraph svg", timeout=15000)
            page.evaluate("document.fonts.load('700 11px Cairo').then(() => document.fonts.ready)")
            page.wait_for_timeout(400)
            element = page.query_selector(".mxgraph")
            if element is None:
                raise RuntimeError("viewer produced no .mxgraph container")
            element.screenshot(path=str(out_png))
        finally:
            browser.close()
    return out_png


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render .drawio files via the draw.io viewer.")
    parser.add_argument("drawio", nargs="+", help="one or more .drawio files")
    parser.add_argument("-o", "--out", default="out/drawio-verify", help="output PNG directory")
    parser.add_argument("--viewer", default=str(VIEWER_JS), help="path to viewer-static.min.js")
    args = parser.parse_args(argv)

    viewer = Path(args.viewer)
    if not viewer.exists():
        print(f"viewer lib not found: {viewer} (download it to {VIEWER_JS})", file=sys.stderr)
        return 2
    out_dir = Path(args.out)
    rc = 0
    for raw in args.drawio:
        src = Path(raw)
        if not src.exists():
            print(f"[skip] {src} (missing)")
            continue
        png = out_dir / f"{src.stem}.png"
        try:
            render_to_png(src, png, viewer)
            print(f"[ok]   {src.name} -> {png}")
        except Exception as exc:  # dev tool: report and continue across the batch
            rc = 1
            print(f"[FAIL] {src.name}: {exc}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
