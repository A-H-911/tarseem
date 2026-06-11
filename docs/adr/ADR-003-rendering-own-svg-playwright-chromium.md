# ADR-003 — Rendering: own SVG (canonical) + Playwright/Chromium for raster/PDF/verification

- Status: **Accepted**
- Date: 2026-06-11
- Deciders: Anas (owner); seeded from `04-architecture.md` §1/§7; validated by Phase 0 Spikes 2 & 3
- Invariant: **#3**

## Context
Every off-the-shelf renderer failed at least one hard requirement: 6-level styling, per-label Arabic
`direction`, font embedding, lane bands, theme portability. We also need Arabic-correct raster,
cross-platform PNG/PDF, and a visual-regression harness. Renderer shaping statuses are documented in
`07-rtl-arabic-strategy.md` (Chromium=HarfBuzz ✅; CairoSVG ⛔ no-bidi; resvg 🟡 GSUB-complete only).

## Decision
- The engine **emits SVG itself** — programmatic (not template), from the positioned IR. This SVG is the
  **canonical artifact**: shapes, arrowheads, lane bands, labels with `direction="rtl"`, embedded fonts.
- **Raster (PNG), PDF (Chromium print-to-PDF, D7), screenshots, and Arabic-correct rendering go through
  Playwright-managed Chromium only.** One dependency serves render, export, and the E2E/visual-regression test layer.
- `resvg` permitted **only** behind a guard ("no Arabic present, or font GSUB-complete") for fast Latin PNG.
- **NEVER CairoSVG** (documented: no bidi). Spike 2 measured uharfbuzz vs Chromium agreement ≤1.13%,
  and Spike 3 rendered the full swimlane shape set through this path.

## Consequences
- (+) Full control over styling/Arabic/lane geometry/theme portability; Arabic verified in a real shaper.
- (+) One tool (Chromium) covers rendering, export rasterization, and visual regression.
- (−) Chromium is a managed dependency (`engine doctor` verifies it); raster determinism requires a
  **pinned Chromium** + device-scale control + version stamping.
- (−) We own the SVG renderer (shape library, router integration, font embedding).

## Alternatives considered
- CairoSVG — **banned** (no bidi; corrupts Arabic).
- resvg as primary rasterizer — **rejected** (rustybuzz, no Arabic fallback shaper).
- Inkscape/Pango pipeline — kept only as the optional text-to-path tooling alternative.

## References
`04-architecture.md` §1/§7 · `07-rtl-arabic-strategy.md` · `08-export-strategy.md` ·
`docs/spikes/spike-2-report.md` · `docs/spikes/spike-3-report.md` · `13-open-decisions.md` (D7)
