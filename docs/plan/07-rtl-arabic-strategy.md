# RTL & Arabic Strategy

Status: Proposed · 2026-06-11
Grounding: shaping happens at render time via the font's GSUB/GPOS tables; SVG stores logical-order Unicode. Correctness therefore depends on (a) measuring with shaping, (b) rendering with a shaping engine, (c) fonts being present. Verified statuses: Chromium=HarfBuzz ✅; CairoSVG ⛔ (documented no-bidi); resvg 🟡 (rustybuzz, no Arabic fallback shaper — complete-GSUB fonts only); Inkscape/Pango ✅; PowerPoint shapes itself ✅; Mermaid diacritics crash (#3047) ⛔.

---

## 1. Principles

1. **Measure with shaping**: all label sizing via uharfbuzz (sum `x_advance`, font units → px). Pillow+libraqm as cross-check where available (Windows needs manual `fribidi.dll` → uharfbuzz is primary; `doctor` verifies).
2. **Render with shaping**: canonical raster/PDF = Playwright/Chromium. Never CairoSVG. resvg only behind a "no Arabic present, or font GSUB-complete" guard.
3. **Never pre-shape into the IR**: `arabic-reshaper`+`python-bidi` output corrupts shaping-capable renderers (double-shaping, R-5). Pre-shaping is permitted only inside a legacy export adapter that targets a non-shaping renderer, and none is planned.
4. **Layout mirroring ≠ text direction** (orthogonal controls): `direction: RL` flips flow via ELK `direction=LEFT` (+ lane header side, port side mirroring, arrow defaults); label `direction: rtl|auto` controls bidi base direction per label.

## 2. SVG Rules (canonical artifact)

- Per-label `<text direction="rtl" xml:lang="ar">`; `unicode-bidi:embed` on mixed-run `<tspan>`s; U+200F guards for leading/trailing neutrals (punctuation placement).
- Anchoring: RTL labels use `text-anchor` consistent with mirrored alignment; alignment resolved in style cascade, not hardcoded.
- **Fonts**: default bundled dual-script family — **Cairo** or **Tajawal** (SIL OFL, Arabic+Latin in one file; final pick = Open Decision D10), Noto Sans Arabic + Noto Sans as the maximal-coverage pair, IBM Plex Sans Arabic offered for technical theme. Embedding: `@font-face` data-URI WOFF2 subset (fonttools subsetter, glyphs actually used) when `export.svg.embedFonts: true` (default).
- **Portability option**: `textAsPaths: true` → uharfbuzz shaping → fonttools `SVGPathPen` outlines (Y-flip applied), or Inkscape `--export-text-to-path` as the tooling alternative. Renders identically everywhere; loses text editability/searchability → off by default, recommended for "publish to unknown renderers".

## 3. Per-Export Behavior

| Target | Arabic mechanism | Status |
|---|---|---|
| SVG | Unicode + direction attrs + embedded fonts (option: text-as-paths) | Correct in browser-class renderers |
| PNG | Chromium screenshot of canonical SVG (deviceScaleFactor for DPI) | Verified correct |
| PDF | Chromium print-to-PDF (CDP); WeasyPrint (Pango) as alternative if HTML-report PDFs needed | Verified correct |
| HTML gallery | Browser renders; `<html dir>` per diagram metadata | Correct |
| draw.io XML | `writingDirection=rtl` style key + label text; diagrams.net renders via browser stack | Verified keys exist; round-trip test required |
| PPTX | Raw Unicode text + `<a:pPr rtl="1"/>` (lxml patch; python-pptx lacks API) + right alignment + Arabic-capable font name; PowerPoint shapes natively | Verified pattern |
| Mermaid/PlantUML source | Best-effort; Mermaid: strip/quote diacritics + warning (#3047); PlantUML: no bidi guarantee — capability report flags | Lossy by design |

## 4. Test Plan Hooks (Phase 4)

Golden Arabic suite: pure-Arabic labels; mixed Arabic+Latin+digits; diacritized text (Reference-2 includes مقدّم); long-wrapping lane titles; RL flowchart; RTL swimlane = Reference-2 rebuild (lane headers right, badges top-right, right→left flow). Assertions: Chromium screenshot baselines (pixel/SSIM), node-width ≥ measured text width, draw.io file opens with correct direction in diagrams.net, PPTX opens with RTL paragraphs in PowerPoint (manual checklist + XML assertions in CI).

## 5. Residual Risks

Windows font/measure gaps (R-3), CI fonts (R-4 — bundled fonts mitigate), PPTX fidelity ceilings (R-16), nested-bidi edge cases in mixed labels (lint warns; documented).
