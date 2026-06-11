# Spike 2 Report — Arabic pipeline (uharfbuzz measure → SVG → Chromium PNG)

Status: **PASS** · 2026-06-11 · throwaway code in `spikes/spike-2-arabic/`

## Objective (from `11-phased-plan.md` Phase 0 / `07-rtl-arabic-strategy.md`)
De-risk the Arabic chain that killed every off-the-shelf renderer:
- Measure label sizes with **shaping** (uharfbuzz `x_advance`) **before** layout (sizes are ELK inputs).
- Render canonical **SVG** with per-label `direction="rtl"`, `xml:lang="ar"`, and an **embedded subset-WOFF2 Cairo** font (no system font reliance).
- Rasterize via **Playwright/Chromium**; verify shaping (joined forms + diacritics) and node sizing.

## What was built
Single throwaway script `spike2.py` (+ bundled `spikes/assets/fonts/Cairo-VF.ttf`, OFL):
1. `measure()` — uharfbuzz: `Buffer.add_str` → `guess_segment_properties()` (auto-detects RTL + Arabic) → `hb.shape` → sum `x_advance` (font units → px via `units_per_em`).
2. `woff2_datauri()` — fontTools `Subsetter` (default retains layout features → Arabic joining GSUB preserved) → WOFF2 → base64.
3. `build_svg()` — each label = padded node rect (solid) + measured-width box (dashed) + `<text direction="rtl" xml:lang="ar" text-anchor="middle">` in **logical-order** Unicode (never pre-shaped); font embedded as `@font-face` data-URI under a unique family `CairoSpike`.
4. Chromium render → PNG, **and** `getComputedTextLength()` per label as a renderer-side cross-check.

Test labels: pure Arabic, diacritized (**مقدّم**), the RTL title إجراءات استخراج وثيقة, three lane/node labels, and a mixed Arabic+Latin+Arabic-Indic-digits line (حالة API ٢٠٢٤).

## How to run
```
# from repo root, after venv + `playwright install chromium`
./.venv/Scripts/python.exe spikes/spike-2-arabic/spike2.py
# outputs: spikes/spike-2-arabic/out/{spike2.svg,spike2.html,spike2.png,measurements.json}
```

## Pinned versions (this run)
- uharfbuzz **0.55.0** · fonttools **4.63.0** · brotli **1.2.0** · playwright **1.60.0** + bundled Chromium
- Cairo variable TTF from google/fonts (OFL, `Cairo[slnt,wght].ttf`, 599 KB) · Python 3.13.7 · Windows 11

## Measurements — uharfbuzz vs Chromium (same embedded font)
| label | chars | glyphs | dir | hb_px | chrome_px | diff% |
|---|---|---|---|---|---|---|
| title (إجراءات استخراج وثيقة) | 21 | 21 | rtl | 267.03 | 268.84 | 0.68 |
| lane_diacritic (مقدّم الطلب) | 11 | 11 | rtl | 111.74 | 112.41 | 0.60 |
| node_fill (تعبئة الطلب) | 11 | 11 | rtl | 103.53 | 104.20 | 0.65 |
| node_recv (استقبال) | 7 | 7 | rtl | 72.25 | 72.25 | 0.00 |
| node_review (مراجعة) | 6 | 6 | rtl | 65.56 | 65.56 | 0.00 |
| mixed (حالة API ٢٠٢٤) | 13 | 13 | rtl | 117.72 | 119.05 | 1.13 |

**Worst |diff| = 1.13%**; subset WOFF2 = 26,100 bytes.

## Visual verification (`out/spike2.png`)
- **Joined cursive forms** everywhere (contextual init/medial/final substitution working) — not isolated letters.
- **Shadda** ّ correctly stacked on the د of **مقدّم** (GPOS mark positioning intact through subsetting).
- **RTL + bidi** correct, incl. the mixed line: حالة (R) · API (Latin) · ٢٠٢٤ (Arabic-Indic) in proper visual order.
- The dashed uharfbuzz-measured box hugs the rendered glyph extent; text sits inside the padded node with margin ⇒ **node width ≥ shaped advance** holds in practice, not just in theory.

## PASS/FAIL vs criteria
| Criterion (from spike plan) | Result |
|---|---|
| Arabic **shaped** (joined forms, not isolated) | **PASS** — visual cursive joining + GSUB retained through subset |
| Diacritic-bearing **مقدّم** renders | **PASS** — shadda correctly positioned |
| Node width ≥ measured shaped advance | **PASS** — node = hb_width + 36px; Chromium width within 1.13% of hb_width |
| Embedded WOFF2 renders in Chromium with **no system font** | **PASS** — unique family `CairoSpike`, font not installed on Windows; renders correctly |
| Measurement matches renderer shaping | **PASS (bonus)** — hb vs `getComputedTextLength()` worst 1.13%, two exact |

**Verdict: PASS.** The "measure-with-shaping → SVG with direction attrs + embedded font → Chromium" chain is validated; the <1.13% agreement justifies using uharfbuzz advances as ELK node-size inputs.

## Surprises / caveats
1. **`n_glyphs == n_chars`** for all words — expected: Arabic joining is 1:1 contextual substitution, not ligature collapse (no lam-alef in the corpus). Not a shaping failure; the width agreement + visual joining are the real proof.
2. **Mixed-script measurement** worked here because `guess_segment_properties` + a single shape call sufficed for these strings, but **true mixed bidi runs** (multiple script segments needing reordering) will require itemization in the real measurement service. Flagged for Phase 4 — out of MVP-gating scope.
3. **Windows-only run.** Linux/macOS shaping parity (R-3/R-4) is deferred to the 3-OS CI matrix (Phase 3/4). The **bundled** font removes the system-font variable, which is the main cross-OS risk mitigation.
4. **Variable font default instance.** Measured at Cairo VF's default coords; Chromium rendered `font-weight:400`. The ~1% deltas are consistent with sub-pixel/default-instance rounding. When the engine pins a specific weight, measure + render must use the *same* instance — note for Phase 4.

## Implications for the engine (carry into Phase 2/4)
- uharfbuzz is a sound primary measurement backend; keep Pillow+raqm only as the documented cross-check.
- Measurement service must itemize mixed-script/bidi runs (caveat 2) and pin the VF instance shared by measure + render (caveat 4).
- Subset-WOFF2 data-URI embedding is cheap (26 KB for this corpus) and is a good default for `export.svg.embedFonts`.
- Never pre-shape into the IR held: logical-order Unicode + `direction="rtl"` rendered correctly; the invariant stands.
