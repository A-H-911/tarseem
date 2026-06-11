# Executive Summary — Research & Design Mission

2026-06-11 · Mission: design (not build) a reusable, schema-driven Python diagram engine wrapping mature layout/rendering engines, with Arabic/RTL, swimlanes, controlled routing, and editable exports.

---

## The finding that shapes everything

Research across 16 candidate engines (verified against docs, issue trackers, and releases) shows **no existing engine satisfies the scope**, and the gaps are structural, not incidental:

- **Text-DSL tools** (Mermaid, PlantUML, D2): no JSON input, no horizontal swimlanes (Mermaid none — 3 open requests since 2021; PlantUML vertical-only; D2 approximations), Arabic unverified-to-broken (Mermaid parser crashes on diacritics — unresolved since 2022), no editable output, weak manual control.
- **Layout engines**: only **ELK** offers ports + compound nodes + partitioning (lanes) + orthogonal routing + crossing minimization behind a documented **JSON in/out contract**. Dagre lacks ports/compound (cluster bugs confirmed); OGDF is GPL; libavoid routes but doesn't place; yFiles/GoJS/TALA/JointJS+ are commercial.
- **Arabic** requires a shaping renderer (HarfBuzz-class) at raster time and shaping-aware *measurement* at layout time. Chromium (Playwright) is verified correct; CairoSVG is documented-incompatible; most engines size text with LTR metrics.
- **Editability** (the PowerPoint requirement) is best achieved by **writing editable formats directly** — draw.io XML (native pool/lane shapes, `writingDirection=rtl`) and native PPTX shapes via python-pptx — not by converting images.

## Recommended architecture (one sentence)

**A Python "schema compiler": unified JSON schema → validated internal model → text measured with real shaping (uharfbuzz) → geometry from ELK (pinned elkjs via subprocess) → own SVG renderer → Chromium (Playwright) for PNG/PDF/verification → the same positioned model serialized to editable draw.io XML and PPTX, plus best-effort Mermaid/PlantUML source exports.**

One layout, many writers: every export — static, editable, or source — derives from a single positioned model, so the file a user edits in PowerPoint starts identical to the published PNG.

| Role | Backend | Status |
|---|---|---|
| Layout/routing | ELK (elkjs, pinned) | primary |
| Sequence layout | custom deterministic (Python) | primary |
| Canonical render | own SVG renderer | primary |
| Raster/PDF + E2E + Arabic correctness | Playwright/Chromium | primary |
| Editable exports | own draw.io writer; python-pptx writer | first-class / adapter |
| Fallback layout | Graphviz dot | optional, degraded |
| Source exports | Mermaid/PlantUML writers | best-effort, loss-reported |
| Excluded | dagre, OGDF (GPL), GoJS ($), JointJS+/core, bpmn-js (watermark), CairoSVG, Excalidraw-as-core | documented |

## MVP vs. deferred

**MVP (Phases 2–3, per D3:B)**: 4 families — flowchart, architecture/C4, dependency, **swimlane (LTR, reference-style; A12)** — plus sequence in P3; JSON schema v0 + validation, ELK layout (swimlane path decided by Phase 0 spike), SVG/PNG, theming incl. per-lane hue system, browser gallery + E2E + visual regression, 1-OS green with 3-OS CI bootstrapped, clean Python API + CLI.
**Deferred**: full Arabic validation incl. RTL swimlane (P4), routing-hint depth + remaining families (P5), PDF + editable/source exports — drawio & PPTX in parallel per D2:C (P6), public plugin + agent surface (P7). Nested lanes and avoid-zones: best-effort, documented.

## Top risks (full register: `02-risks.md`)

1. Arabic outside browsers (R-1/R-2) — mitigated by measurement service + Chromium canonical path + font embedding/text-to-path options.
2. Swimlane fidelity via ELK partitioning (R-9) — Phase 0 spike; pre-approved fallback: own lane-grid layout with ELK sublayouts.
3. Node+Chromium dependency weight (R-10/R-20) — vendored pinned bundle, doctor command, Docker reference.
4. Editable-format fidelity ceilings (R-14/R-16) — constrained verified key subset + capability reports; ceilings documented, not hidden.
5. Scope breadth (R-27) — strict phase gates, golden-corpus-driven.

## Decision status

**All decisions D1–D12 resolved 2026-06-11** (record: `13-open-decisions.md`). Material outcomes: Node.js accepted (D1); swimlanes pulled into MVP (D3:B — accepted risk R-27↑, pressure-valved by the Phase 0 spike); drawio+PPTX writers in parallel (D2:C); Apache-2.0 single package (D8); Cairo default font (D10). Reference images provided and analyzed (`references/analysis.md`).

**No implementation started.** Next step on go-ahead: Phase 0 spikes (4 timeboxed validations) → Phase 1 baseline → build.
