# CLAUDE.md — Tarseem (ترسيم)

Schema-driven Python diagram engine: validated JSON specs → architecture-grade diagrams. Wrapper/orchestration over mature engines — never a from-scratch monolith.

## Project state

- Design mission **complete and approved** (all decisions D1–D12 resolved 2026-06-11). The plan in `docs/plan/` is the contract — read `docs/plan/README.md` first, then `04-architecture.md`, `11-phased-plan.md`, `12-acceptance-criteria.md`, `13-open-decisions.md`.
- **Current phase: Phase 0 spikes** (4 timeboxed validations, defined in `docs/plan/11-phased-plan.md`). No engine scaffolding until spikes pass + Phase 1 baseline is tagged.
- Kickoff instructions: `docs/prompts/initial-prompt.md`.

## Architecture invariants (violations require a new ADR in docs/adr/)

1. **One positioned IR, many writers**: spec → validate → logical IR → measure text → layout → positioned IR → {SVG, PNG, PDF, drawio, PPTX, Mermaid/PlantUML} writers. No writer computes its own layout.
2. **Layout = ELK** via vendored, **pinned** elkjs bundle in a long-lived Node subprocess (JSON over stdio). ELK JSON never leaks outside the layout adapter. Sequence diagrams use a custom deterministic Python layouter, not ELK. Graphviz `dot` = optional degraded fallback only.
3. **Rendering**: own programmatic SVG renderer (canonical artifact). Raster/PDF/verification via Playwright-managed Chromium only.
4. **Arabic/RTL is first-class**:
   - NEVER use CairoSVG anywhere (documented: no bidi support).
   - NEVER pre-shape Arabic text into the IR (no arabic-reshaper upstream of shaping renderers — double-shaping corrupts).
   - All text measurement via **uharfbuzz** (shaped advances) before layout; Pillow+raqm only as cross-check.
   - SVG: per-label `direction="rtl"`, `xml:lang`; default font **Cairo** (bundled, OFL) + Noto pair fallback; embed subset WOFF2 by default.
   - RTL mirroring (direction: RL) = geometry only: ELK `direction=LEFT`, lane headers flip to right, number badges flip corner, arrows reverse. Theme stays invariant.
   - PPTX RTL: `<a:pPr rtl="1"/>` via lxml patch (python-pptx has no API for it).
5. **Editable exports are writers, not conversions**: own mxGraph/.drawio XML writer (**amended by ADR-007**: explicit cells matching the SVG — incl. RTL right-side headers + phase bands — not native `swimlane` shapes; `writingDirection=rtl`, uncompressed XML, documented style-key subset only) + python-pptx native shapes/connectors (EMU coords from positioned IR). No EMF, no SVG-ungroup automation.
6. **Capability reports, never silent drops**: every adapter declares `supports`; unsupported spec features produce machine-readable warnings in RenderReport/CapabilityReport.
7. **Determinism**: pinned elkjs + Chromium versions; same spec ⇒ identical output; artifacts embed spec hash + engine versions; visual-regression baseline changes only via explicit PR.
8. **Extension model**: diagram types are plugins (schema extension + compiler + layout/render profiles) registered via entry points. Built-ins use the same mechanism.

## Hard constraints

- Python ≥ 3.10. License: **Apache-2.0**. No GPL deps in required path (OGDF excluded). No bpmn-js (mandatory watermark). No GoJS/TALA/JointJS+ (commercial). Kroki = optional extra, off by default. No network calls at render time.
- MVP scope (per D3:B): **4 families** — flowchart, architecture/C4, dependency, **swimlane (LTR, reference style)** — plus sequence in Phase 3. MVP acceptance = A1–A12 in `docs/plan/12-acceptance-criteria.md`. Swimlane visual target = `docs/plan/references/analysis.md`.
- Performance: ≤100 nodes ≤2 s warm render; ≤300 nodes supported.

## Conventions

- Conventional commits. Small, reviewable changes. ADRs numbered in `docs/adr/` (ADR-001…005 to be seeded from `docs/plan/04-architecture.md` during Phase 1).
- Tests: pytest; schema/unit/adapter-contract/render-golden/E2E layers per `docs/plan/09-testing-gallery-strategy.md`. Every feature lands with a golden sample in `examples/` rendered in the gallery. No phase starts with red CI.
- Spike code lives in `spikes/` (throwaway, excluded from packaging); spike reports in `docs/spikes/spike-N-report.md` with screenshots + PASS/FAIL vs criteria.
- `engine doctor` must keep verifying: Node runtime, pinned elkjs bundle, Playwright Chromium, bundled fonts.

## Repo layout (target)

```
docs/{plan, adr, prompts, spikes}   # plan = approved design (read-only reference)
spikes/                             # Phase 0 throwaway code
src/tarseem/                        # engine (from Phase 2): schema/ validation/ model/ plugins/ layout/ themes/ render/ export/ gallery/ cli/
examples/                           # golden spec corpus
tests/
```
