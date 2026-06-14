# ADR-007 — draw.io swimlanes as explicit cells, not native pool/lane shapes

Status: **Accepted** (2026-06-13) · Amends invariant 5 (the draw.io writer clause only)
Supersedes the "native `swimlane` pool/lane shapes" requirement of `04-architecture.md` §5 /
ADR-005 **for the draw.io writer**. Decision owner: project owner (explicit, 2026-06-13).

## Context

Invariant 5 (CLAUDE.md) and ADR-005 specify the draw.io writer emit **native `swimlane`
pool/lane cells**. The Phase-6 render-fidelity loop (Option A — rendering our `.drawio` through
draw.io's own viewer; `tools/verify_drawio.py`) showed two limits of native swimlanes:

1. **RTL header side.** draw.io's horizontal-lane pool (`horizontal=0`) places lane headers on
   the LEFT and exposes no flag to mirror them right. For an RTL diagram the canonical SVG puts
   headers on the RIGHT (invariant 4; `references/analysis.md` §R-2). Native swimlanes therefore
   render RTL headers on the wrong side — a visible mismatch with the authoritative artifact.
2. **Phase bands.** draw.io swimlanes have no phase-band concept, so phase headers (FR-6.3) were
   dropped entirely from the native-swimlane output.

The project owner chose **visual fidelity to the canonical SVG over native editability**, for
**both RTL and LTR** (consistency: one rendering path, predictable output), accepting the loss
of draggable-swimlane semantics in the editable export.

## Decision

The draw.io writer (`src/tarseem/export/drawio.py`) draws swimlane chrome as **explicit cells
that reproduce `render/swimlane.py` geometry exactly**, not native `swimlane` cells:

- lane band = plain rect (hue fill, accent stroke); header **chip** = rounded rect positioned
  on the flow-start side (left for LTR, **right for RTL**) — mirrors `_lane_band`;
- title bar, phase header bands + dashed phase separators, the actor separator line, and
  nested-lane group gutters — all explicit cells matching the SVG;
- nodes are parented to the layer with **absolute** geometry (lanes are no longer containers);
- geometry constants in the writer are annotated **"MUST match render/swimlane.py"** and kept
  in lockstep with the SVG writer (the single source of visual truth).

## Consequences

**Gained:** the `.drawio` matches the canonical SVG — correct RTL header side, phase bands
present, title bar present. Verified through draw.io's own renderer on LTR + RTL + phase samples.

**Lost / ceilings (reported in every CapabilityReport, never silent — invariant 6):**
- Lanes are **static rects, not draggable draw.io swimlane containers**; moving a "lane" does
  not move its nodes. Flagged as an `editability-limited` warning on the `lanes` feature.
- Two visual-truth sources (SVG writer + draw.io writer) must stay synchronised; the
  "MUST match" constants are the guard. A future refactor may extract shared lane-chrome
  geometry into one module consumed by both writers.

**Unchanged:** invariants 1–4, 6, 7, 8 hold. Other writers (PPTX, etc.) are unaffected. The SVG
writer is untouched (no visual-baseline churn).
