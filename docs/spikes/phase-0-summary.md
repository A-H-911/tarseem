# Phase 0 — Discovery & Validation Summary

Date: 2026-06-11 · Status: **all four spikes complete** · Recommendation: **GO for Phase 1**

Phase 0 de-risked the four make-or-break assumptions before any engine scaffolding. All spike code is throwaway under `spikes/`; per-spike reports are in `docs/spikes/spike-{1..4}-report.md`.

## Per-spike verdicts
| # | Spike | Verdict | Headline evidence |
|---|---|---|---|
| 1 | elkjs round-trip (Python ↔ long-lived Node subprocess) | **PASS** | 50-node compound graph, 100 FIXED_ORDER ports, 49/49 edges routed; warm median **30.6 ms** (~60× under the 2 s NFR-2 budget); cold 187 ms |
| 2 | Arabic pipeline (uharfbuzz → SVG → Chromium) | **PASS** | hb advance vs Chromium `getComputedTextLength()` agree to **≤1.13%**; joined forms + **مقدّم** shadda render; embedded subset-WOFF2, no system font |
| 3 | Swimlane (**MVP-gating**) | **PASS** | ref-1 + ref-3 reproduced in Tarseem's own renderer (all A12 features); ELK partitioning proven to be *flow-axis (phases), not lanes* |
| 4 | Editable probes (drawio + PPTX) | **PASS** (automated) | native-swimlane RTL `.drawio` structurally valid; PPTX `rtl="1"` round-trips. Visual app-open = documented manual gate |

## Key decision — MVP swimlane layout path: **lane-grid layouter**
ELK `partitioning` orders nodes along the **flow/layer axis** (phases), confirmed numerically in Spike 3 — it cannot band the cross-axis (lanes). The **lane-grid** approach (one step per column = topological number; lanes = fixed rows; orthogonal router exploiting one-step-per-column) reproduced both LTR references deterministically.

This is the plan's **pre-approved fallback** (`06-layout-routing-strategy.md` §4), so it is a *path selection, not a plan deviation*. Consequences:
- Swimlane becomes a **custom `LayoutAdapter`** (sibling to `SequenceLayout`), not an `ElkLayout` profile. **R-9 retired for MVP.**
- ELK remains the layout engine for the graph families (flowchart / architecture-C4 / dependency), validated in Spike 1.
- Phases (FR-6.3) layer on top as column groupings over the same grid.

## Plan deviations / corrections
1. **Reference images reconciled (2026-06-11).** The supplied screenshots did not match the prose in `references/analysis.md` (no "Order Fulfillment"; Arabic had 3 lanes not 4). With approval, the 3 reference-grade images were renamed to canonical names and `analysis.md` rewritten to match reality; 2 theme-demo images kept as supplementary (F4, not A12). Acceptance bindings now point at real pixels.
2. **No architecture-invariant changes.** No ADR required. The swimlane path uses the documented fallback.

## Engineering notes carried into later phases
- **Phase 2 (renderer/layout):** build a real **orthogonal router with channel assignment** (co-terminal edges share a corridor — Spike 3 caveat 2, R-13); **per-shape badge offsets** (diamond/cylinder/parallelogram); **path-length label anchoring** (label bug found+fixed in Spike 3). Port the skill's `compute_layout` constants + palette. Measurement service must **itemize mixed-script bidi runs** and **pin the variable-font instance** shared by measure + render (Spike 2 caveats).
- **Phase 2 (ELK adapter):** seed from Spike 1's `ElkServer` contract (id-matched JSON lines, stderr-isolated, serialized); decide subprocess **lifecycle/health** + `doctor` probe; **vendor + pin** the elkjs bundle (not npm-resolved at runtime).
- **Phase 4 (RTL):** ref-2 (RTL Arabic swimlane) is the gate; Spike 2 proved the shaping/mirroring primitives, Spike 3 the lane-grid — combine for `direction="rtl"` (header side + badge corner + flow mirror).
- **Phase 6 (editable):** native-swimlane drawio + PPTX-RTL-via-lxml confirmed; use **`defusedxml`** for the inbound drawio reader; bake **manual visual gates** (diagrams.net + PowerPoint open) into the checklist — the headless GraphViewer embed is unreliable (Spike 4 caveat 1).

## Consolidated pinned versions (record for determinism)
- **elkjs 0.11.1** · Node v26.3.0 · npm 11.16.0
- Python 3.13.7 · **uharfbuzz 0.55.0** · **fonttools 4.63.0** · **brotli 1.2.0** · **playwright 1.60.0** (+ Chromium) · **python-pptx 1.0.2** · **lxml 6.1.1** · pillow 12.2.0
- Font: **Cairo** variable TTF (OFL) bundled at `spikes/assets/fonts/Cairo-VF.ttf`
- OS: Windows 11 Pro (26200). Cross-OS (Linux/macOS) parity deferred to the Phase 3/4 CI matrix.

## Cross-platform caveat (honest)
All spikes ran on **Windows only**. Arabic shaping parity and visual baselines on Linux/macOS are **not yet proven** — that is explicitly the 3-OS CI matrix work in Phases 3–4. The bundled font removes the largest cross-OS variable.

## Go / No-Go
**GO for Phase 1.** All four assumptions validated; the one MVP-gating risk (swimlane fidelity, R-9) is retired via the lane-grid path. No blocking surprises; all open items are normal forward engineering captured above.

**Do not scaffold the engine package until Phase 1 is approved** (per kickoff Step 3). Phase 1 = freeze requirements, seed ADR-001…005 from `04-architecture.md`, lock MVP scope, bootstrap repo packaging + CI skeleton, tag `baseline-1.0`.
