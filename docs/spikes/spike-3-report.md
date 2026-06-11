# Spike 3 Report — Swimlane (MVP-gating): lane-grid vs ELK partitioning

Status: **PASS** · path decision: **lane-grid layouter** · 2026-06-11 · throwaway code in `spikes/spike-3-swimlane/`

## Objective (from `11-phased-plan.md` Phase 0, D3:B / `06-layout-routing-strategy.md` §4)
Rebuild the two LTR reference swimlanes and assess against §4 acceptance, then **decide the MVP swimlane layout path**: ELK partitioning (the plan's primary) vs. the pre-approved lane-grid fallback. This spike is MVP-gating — failure re-scopes the MVP, so it produces a real artifact in Tarseem's own pipeline, not a mock.

## What was built
Single throwaway script `spike3.py`:
- **Specs** for `Bug Triage` (ref-1, LTR 4 lanes) and `Pipeline` (ref-3, LTR 3 lanes), authored to match the reference images (shapes, markers, badges, edge labels, dashed, back-edges).
- **Lane-grid placement** ported from the local `horizontal-swimlane-diagram` skill: column = topological number (one step per column), lane = fixed row; geometry constants reused (lane_h 120, step 150×70, col_gap 40, …) and the default green/orange/blue/yellow hue→tints palette.
- **Tarseem's own SVG renderer** (no draw.io): title bar, lane bands + header chips + separator, six node shapes (stadium, roundrect, **diamond, parallelogram, cylinder, document**), UML start (filled circle) + end (bullseye) markers, hue-colored corner badges, embedded subset-WOFF2 Cairo (reusing the Spike-2 mechanism).
- **From-scratch orthogonal router** exploiting one-step-per-column: same-lane edges run straight at center-y; cross-lane edges go vertical-in-source-column then horizontal-at-target-row. Handles back-edges and long cross-lane edges with no node crossings.
- **ELK partitioning probe** (reuses the Spike-1 subprocess) to measure which axis `partitioning` actually controls.

Rendered via Playwright/Chromium to PNG; graded side-by-side against `docs/plan/references/reference-1-bug-triage-ltr.png` and `reference-3-pipeline-shapes.png`.

## How to run
```
./.venv/Scripts/python.exe spikes/spike-3-swimlane/spike3.py
# outputs: spikes/spike-3-swimlane/out/{bug_triage,pipeline}.{svg,png} + elk_probe.json
```

## Pinned versions
- elkjs **0.11.1** (probe) · uharfbuzz 0.55.0 · fonttools 4.63.0 · brotli 1.2.0 · playwright 1.60.0 + Chromium · Cairo VF (OFL) · Python 3.13.7 · Windows 11

## ELK partitioning probe (the decision evidence)
Bug Triage nodes, flat ELK graph, `elk.partitioning.partition = lane index`, direction RIGHT:

| node | lane | partition | x | y |
|---|---|---|---|---|
| report | rep | 0 | 12 | 23.7 |
| classify | tri | 1 | 182 | 23.7 |
| realbug | tri | 1 | 352 | 23.7 |
| close | tri | 1 | 522 | 12 |
| fix | dev | 2 | 692 | 58 |
| verify | qa | 3 | 862 | 46.3 |

**x increases monotonically with partition; y is unconstrained.** Partitions are ordered along the **flow (layer) axis** = *phases*, not lanes. ELK has no native lane (cross-axis band) concept. (The script's strict "identical-coordinate" booleans both read false because same-partition nodes share partition *order*, not an identical x — the monotonic x-by-partition above is the real signal.)

## Render grading vs §4 acceptance
| §4 criterion | Bug Triage (ref-1) | Pipeline (ref-3) |
|---|---|---|
| Lanes straight; bands + header pills + hue tints | PASS | PASS |
| Nodes contained within lane | PASS | PASS |
| Reference shape set | PASS (stadium/roundrect/diamond) | PASS (parallelogram/diamond/roundrect/cylinder/document) |
| UML start/end markers | n/a (markers off) | PASS (filled circle + bullseye) |
| Numbered badges, hue-colored, start/end exempt | PASS (2–5) | PASS (1–5) |
| Cross-lane orthogonal edges | PASS | PASS |
| **Back-edge** routed orthogonally, no node crossing | PASS ("fails" Verify→Fix) | PASS ("bad" Validate→Upload) |
| **Long cross-lane edge** avoiding nodes | PASS ("passes" Verify→Close) | PASS (Save→Receipt, up 2 lanes) |
| Dashed edge | n/a | PASS ("async") |
| Edge labels | PASS | PASS |
| **No node / lane-border overlaps** | PASS | PASS |

**Verdict: PASS.** Both references reproduced in Tarseem's own pipeline with every A12 feature.

## Decision: MVP swimlane path = **lane-grid layouter** (not ELK partitioning)
Rationale:
1. ELK partitioning controls the flow axis (phases), proven above — it structurally cannot produce lane bands.
2. The lane-grid layouter (one-step-per-column + fixed lane rows) reproduced both references deterministically, matching the enterprise reference style.
3. This is consistent with the architecture already assigning *sequence* diagrams a custom Python layouter; swimlanes join that family. ELK remains the layout engine for the graph families (flowchart / architecture / dependency), per Spike 1.
4. It is the plan's pre-approved fallback (`06 §4`) — so this is a path *selection*, not a plan deviation; R-9 is retired for MVP.

Phases (the orthogonal flow-axis grouping, FR-6.3) can still be added later as column groupings over the same grid; ELK *could* contribute phase ordering, but the lane axis stays grid-driven.

## Surprises / caveats
1. **Edge-label placement bug found & fixed mid-spike**: a 2-point edge's "midpoint" was its endpoint, clipping "ok"/"no" into the target. Fixed with a path-length midpoint (`path_midpoint`). Carry the lesson into the Phase-2 renderer: label anchoring must be path-length based.
2. **Co-terminal edge corridor**: "no" (Real bug?→Close) and "passes" (Verify→Close) share part of the Triage-row corridor — an edge-edge overlap (T-junction), **not** a node overlap, so §4 still passes. The reference separates them by routing "no" along the lane top. Phase-2 routing needs **channel assignment** for edges sharing a row/target. (Tracks R-13 label/edge collision.)
3. **Badge on non-rect shapes**: number badges sit at the node's top-left bounding-box corner, which slightly clips the parallelogram/cylinder outline. Cosmetic; Phase-2 should offset badges per shape (above the diamond apex, inside the cylinder top).
4. **Routing is topology-tuned**: the from-scratch router is correct for these reference topologies because one-step-per-column keeps corridors clear. A general swimlane (multiple steps per lane sharing a column, or dense cross-lane traffic) will need the channel router from caveat 2. Not MVP-blocking for the reference style.
5. **RTL (ref-2) not built here** — it is the Phase-4 gate by plan design. Spike 2 already proved the Arabic shaping/mirroring primitives; the lane-grid `direction="rtl"` path (header side + badge corner + flow mirror) lands in Phase 4.

## Implications for the engine (carry into Phase 2)
- Implement swimlane as a **custom lane-grid layouter** behind the `LayoutAdapter` contract (sibling to `SequenceLayout`), not via `ElkLayout`.
- Build a proper **orthogonal edge router** with channel assignment (caveat 2) and per-shape badge offsets (caveat 3); make label anchoring path-length based (caveat 1).
- The skill's `compute_layout` constants and palette are a sound Phase-2 starting point; the skill's draw.io output also de-risks the future drawio writer (Spike 4 / Phase 6).
