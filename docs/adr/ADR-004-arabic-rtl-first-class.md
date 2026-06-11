# ADR-004 — Arabic/RTL first-class: measure-with-shaping before layout; never pre-shape

- Status: **Accepted**
- Date: 2026-06-11
- Deciders: Anas (owner); seeded from `04-architecture.md` §1 + `07-rtl-arabic-strategy.md`; validated by Phase 0 Spike 2
- Invariant: **#4**

## Context
Shaping happens at render time via the font's GSUB/GPOS tables; SVG stores **logical-order** Unicode.
Correctness therefore depends on (a) measuring with shaping, (b) rendering with a shaping engine, and
(c) fonts being present. Naive character-count sizing mis-sizes Arabic nodes; pre-shaping corrupts
shaping-capable renderers (double-shaping, R-5).

## Decision
- **Measure with shaping**: all label sizing via **uharfbuzz** (shaped `x_advance`, font units → px),
  performed **before** layout; the resulting boxes are node-size inputs to ELK / the lane-grid layouter.
  Pillow + libraqm is a cross-check only. (Spike 2: uharfbuzz vs Chromium ≤1.13%.)
- **Render with shaping**: canonical raster/PDF via Chromium (ADR-003). Never CairoSVG.
- **Never pre-shape into the IR**: no `arabic-reshaper`/`python-bidi` upstream of shaping renderers.
- **SVG**: per-label `direction="rtl|auto"` + `xml:lang`; default bundled **Cairo** (OFL, D10) + Noto pair
  fallback; embed subset **WOFF2** by default (`export.svg.embedFonts`). Text-as-paths is an opt-in
  portability mode.
- **RTL mirroring = geometry only**: ELK `direction=LEFT` (graph families) or lane-grid mirror (header
  side, badge corner, arrow/flow reversal) for swimlanes; **theme/palette stays invariant**.
- The measurement service must **itemize mixed-script bidi runs** and **pin the variable-font instance**
  shared by measure + render (Spike 2 caveats; Phase 4 work).

## Consequences
- (+) Verified Arabic everywhere — shaping, diacritics, mirroring — independent of the host OS fonts.
- (−) Fonts must be bundled and subset; the measurement service is real engineering (mixed bidi, VF instance).
- (−) RTL adds a geometry-mirror path to each layouter and the renderer (gated by Phase 4 / ref-2).

## Alternatives considered
- Pre-shaping pipeline (`arabic-reshaper` + bidi) into the IR — **rejected** (double-shaping corruption);
  permitted only inside a hypothetical legacy non-shaping export adapter (none planned).
- CairoSVG / Mermaid for Arabic — **rejected** (no bidi / diacritics crash, #3047).

## References
`04-architecture.md` §1 · `07-rtl-arabic-strategy.md` · `docs/spikes/spike-2-report.md` ·
`13-open-decisions.md` (D10) · `02-risks.md` (R-1…R-5)
