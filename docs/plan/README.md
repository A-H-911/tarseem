# Research & Design Mission — Schema-Driven Python Diagram Engine

Deliverable set · 2026-06-11 · **Status: decisions D1–D12 resolved; plan updated (swimlane→MVP, parallel editable writers). Awaiting go for Phase 0 spikes — no implementation started.**

## Reading order

| Doc | Content (maps to required outputs 1–20) |
|---|---|
| [00-executive-summary.md](00-executive-summary.md) | Executive summary · final recommendation (1, 19) |
| [01-requirements.md](01-requirements.md) | Refined requirements: FR/NFR, constraints, assumptions (2) |
| [02-risks.md](02-risks.md) | Ambiguities, 29 risks w/ impact·likelihood·mitigation, trade-offs (3) |
| [03-engine-comparison.md](03-engine-comparison.md) | 16-candidate research + fit matrix + verdicts + sources (4, 6) |
| [04-architecture.md](04-architecture.md) | Recommended architecture, component model, adapter contracts, extension model, answers to the 10 questions (5, 6, 7) |
| [05-schema-strategy.md](05-schema-strategy.md) | JSON schema strategy: core+profiles+extensions, versioning, validation (8) |
| [06-layout-routing-strategy.md](06-layout-routing-strategy.md) | ELK integration, hint mapping, swimlane plan + fallback (9) |
| [07-rtl-arabic-strategy.md](07-rtl-arabic-strategy.md) | RTL/Arabic strategy end-to-end (10) |
| [08-export-strategy.md](08-export-strategy.md) | Rendering/export tiers + editable-output strategy (11, 12) |
| [09-testing-gallery-strategy.md](09-testing-gallery-strategy.md) | Test pyramid + browser gallery (13) |
| [10-documentation-plan.md](10-documentation-plan.md) | Documentation structure (14) |
| [11-phased-plan.md](11-phased-plan.md) | Phases 0–7 with goals/scope/deliverables/validation/risks/exit (15) |
| [12-acceptance-criteria.md](12-acceptance-criteria.md) | MVP + full-version acceptance criteria (16, 17) |
| [13-open-decisions.md](13-open-decisions.md) | Decision record D1–D12 — all resolved 2026-06-11 (18) |
| [references/analysis.md](references/analysis.md) | Swimlane reference images: extracted visual requirements (binds A12/F3) |

## Recommendation in one line

Python schema-compiler over **ELK** (layout) + **own SVG renderer** + **Playwright/Chromium** (raster/PDF/verification/Arabic) + **own draw.io & PPTX writers** (editable) + Graphviz fallback + Mermaid/PlantUML best-effort source exports — one positioned model, many writers.

## ✅ Approval checkpoint (required output 20)

1. ~~Decide D1–D12~~ ✅ Resolved 2026-06-11; plan replanned for D3:B and D2:C.
2. ~~Provide swimlane reference images~~ ✅ Provided + analyzed (`references/analysis.md`); drop the PNG files into `references/` for side-by-side gates.
3. **Remaining: explicit go/no-go for Phase 0 spikes** (4 timeboxed validations — elkjs round-trip, Arabic pipeline, swimlane references via ELK partitioning, editable-format probes). Implementation of the engine proper starts only after spike results + Phase 1 baseline.
