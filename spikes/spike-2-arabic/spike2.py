"""Spike 2: Arabic pipeline (throwaway).

uharfbuzz shaped measurement -> SVG (per-label direction="rtl", xml:lang="ar",
embedded subset-WOFF2 Cairo as data-URI) -> Chromium (Playwright) PNG.

Strong verification: for every label we compare the uharfbuzz advance to Chromium's
getComputedTextLength() for the *same* embedded font. Small deviation proves our
pre-layout measurement matches the renderer's shaping -- the correctness claim that
makes "measure before layout" safe for Arabic.
"""
from __future__ import annotations

import base64
import io
import json
from pathlib import Path

import uharfbuzz as hb
from fontTools import subset
from fontTools.ttLib import TTFont
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
FONT = HERE.parent / "assets" / "fonts" / "Cairo-VF.ttf"
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)

FAMILY = "CairoSpike"  # unique name: proves the embedded font is used, not a system font
LABEL_SIZE = 22
TITLE_SIZE = 30
PAD_X = 18

# (key, text, font_size) -- pure Arabic, diacritized (مقدّم), lane title, mixed script+digits
LABELS = [
    ("title", "إجراءات استخراج وثيقة", TITLE_SIZE),
    ("lane_diacritic", "مقدّم الطلب", LABEL_SIZE),
    ("node_fill", "تعبئة الطلب", LABEL_SIZE),
    ("node_recv", "استقبال", LABEL_SIZE),
    ("node_review", "مراجعة", LABEL_SIZE),
    ("mixed", "حالة API ٢٠٢٤", LABEL_SIZE),
]

_blob = hb.Blob.from_file_path(str(FONT))
_face = hb.Face(_blob)
_upem = _face.upem


def measure(text: str, size_px: int) -> dict:
    font = hb.Font(_face)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()  # sets direction (rtl for Arabic) + script + language
    hb.shape(font, buf)
    infos = buf.glyph_infos
    advance_units = sum(p.x_advance for p in buf.glyph_positions)
    return {
        "text": text,
        "size": size_px,
        "n_chars": len(text),
        "n_glyphs": len(infos),
        "direction": str(buf.direction),
        "script": str(buf.script),
        "glyph_ids": [g.codepoint for g in infos],
        "hb_width_px": round(advance_units / _upem * size_px, 2),
    }


def woff2_datauri(all_text: str) -> tuple[str, int]:
    chars = {c for c in all_text if not c.isspace()}
    ttf = TTFont(str(FONT))
    ss = subset.Subsetter()  # default retains layout features -> Arabic joining preserved
    ss.populate(unicodes=[ord(c) for c in chars])
    ss.subset(ttf)
    ttf.flavor = "woff2"
    b = io.BytesIO()
    ttf.save(b)
    data = b.getvalue()
    return base64.b64encode(data).decode("ascii"), len(data)


def build_svg(rows: list[dict], b64: str) -> str:
    gap, y = 26, 26
    placed = []
    for i, r in enumerate(rows):
        node_w = r["hb_width_px"] + 2 * PAD_X
        node_h = r["size"] * 1.9
        placed.append((i, r, node_w, node_h, y))
        y += node_h + gap
    svg_w = max(p[2] for p in placed) + 80
    svg_h = y + 10
    cx = svg_w / 2

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_w:.0f}" height="{svg_h:.0f}" '
        f'viewBox="0 0 {svg_w:.0f} {svg_h:.0f}">',
        "<style>",
        f"@font-face{{font-family:'{FAMILY}';font-weight:400;"
        f"src:url(data:font/woff2;base64,{b64}) format('woff2');}}",
        f"text{{font-family:'{FAMILY}';font-weight:400;}}",
        "</style>",
        f'<rect x="0" y="0" width="{svg_w:.0f}" height="{svg_h:.0f}" fill="#ffffff"/>',
    ]
    for i, r, nw, nh, ny in placed:
        node_x = cx - nw / 2
        meas_x = cx - r["hb_width_px"] / 2
        ty = ny + nh / 2
        # padded node (solid) + measured-width box (dashed) -> overflow is visible if shaping mismatches
        parts.append(
            f'<rect x="{node_x:.1f}" y="{ny:.1f}" width="{nw:.1f}" height="{nh:.1f}" rx="8" '
            f'fill="#eaf4ee" stroke="#2e8b57" stroke-width="1.5"/>'
        )
        parts.append(
            f'<rect x="{meas_x:.1f}" y="{ny:.1f}" width="{r["hb_width_px"]:.1f}" height="{nh:.1f}" '
            f'fill="none" stroke="#cc4444" stroke-width="1" stroke-dasharray="4 3"/>'
        )
        parts.append(
            f'<text id="t{i}" x="{cx:.1f}" y="{ty:.1f}" font-size="{r["size"]}" '
            f'direction="rtl" xml:lang="ar" text-anchor="middle" '
            f'dominant-baseline="central" fill="#14281d">{_xml(r["text"])}</text>'
        )
    parts.append("</svg>")
    return "\n".join(parts)


def _xml(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main() -> int:
    rows = [dict(key=k, **measure(t, s)) for (k, t, s) in LABELS]
    all_text = "".join(r["text"] for r in rows)
    b64, woff2_bytes = woff2_datauri(all_text)
    svg = build_svg(rows, b64)
    (OUT / "spike2.svg").write_text(svg, encoding="utf-8")
    html = f"<!doctype html><html><head><meta charset='utf-8'></head><body style='margin:0'>{svg}</body></html>"
    html_path = OUT / "spike2.html"
    html_path.write_text(html, encoding="utf-8")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(device_scale_factor=2)
        page.goto(html_path.as_uri())
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(250)
        lengths = page.evaluate(
            "Array.from(document.querySelectorAll('text')).map(t => t.getComputedTextLength())"
        )
        page.query_selector("svg").screenshot(path=str(OUT / "spike2.png"))
        browser.close()

    for r, clen in zip(rows, lengths):
        r["chromium_width_px"] = round(clen, 2)
        r["diff_pct"] = round((clen - r["hb_width_px"]) / r["hb_width_px"] * 100, 2)

    report = {"family": FAMILY, "woff2_bytes": woff2_bytes, "labels": rows}
    (OUT / "measurements.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"woff2 subset: {woff2_bytes} bytes")
    print(f"{'key':16} {'chars':>5} {'glyphs':>6} {'dir':>4} {'hb_px':>8} {'chrome_px':>9} {'diff%':>6}")
    worst = 0.0
    for r in rows:
        worst = max(worst, abs(r["diff_pct"]))
        print(
            f"{r['key']:16} {r['n_chars']:5} {r['n_glyphs']:6} {r['direction']:>4} "
            f"{r['hb_width_px']:8.2f} {r['chromium_width_px']:9.2f} {r['diff_pct']:6.2f}"
        )
    print(f"worst |diff| = {worst:.2f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
