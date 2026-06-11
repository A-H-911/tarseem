# ADR-005 — Editable exports are writers from the positioned IR; capability reports, never silent drops

- Status: **Accepted**
- Date: 2026-06-11
- Deciders: Anas (owner); seeded from `04-architecture.md` §1/§6 + `08-export-strategy.md`; validated by Phase 0 Spike 4
- Invariants: **#5, #6**

## Context
Users need genuinely **editable** artifacts (draw.io, PowerPoint) without commercial or watermarked
dependencies (no bpmn-js — D5; no GoJS/TALA/JointJS+ — D6). Treating editability as a *conversion*
problem (SVG→drawio, EMF, ungroup automation) loses fidelity; treating it as a *writer* problem off the
positioned IR keeps the edited file equal to the published one (ADR-001).

## Decision
Editable formats are **writers that consume the positioned IR**, behind an `ExportWriter` contract:

- **draw.io / mxGraph XML writer**: native swimlane **pool/lane** shapes, `writingDirection=rtl`,
  **uncompressed** XML, a **documented style-key subset** only. (Spike 4 hand-built a valid pool +
  2 lanes + RTL node.)
- **PPTX writer (python-pptx)**: native PowerPoint shapes/connectors with EMU coords from the positioned
  IR; **RTL paragraphs via an lxml `<a:pPr rtl="1">` patch** (python-pptx has no API). (Spike 4: rtl flag
  round-trips.) No EMF, no SVG-ungroup automation.
- **Mermaid / PlantUML**: best-effort **lossy source** writers (ADR-001) with explicit loss reports.
- **PDF**: Chromium print-to-PDF only (D7). draw.io + PPTX writers built **in parallel** (D2:C, Phase 6).

Cross-cutting (**invariant #6**): every adapter declares `supports = {...}`; unsupported spec features
produce **machine-readable warnings** in the RenderReport / CapabilityReport — **never silent drops**.
The validation layer cross-checks spec features against the chosen pipeline before work starts.

Security: any **inbound** XML (drawio round-trip reader, Phase 6) is parsed with **`defusedxml`**
(XXE / billion-laughs), not stdlib ElementTree (Spike 4 note).

## Consequences
- (+) True editability with zero conversion loss; edited files start equal to the canonical SVG.
- (−) Fidelity ceilings are **declared, not hidden**; some features stay SVG-only and are reported.
- (−) "Opens correctly" in diagrams.net / PowerPoint needs **manual visual gates** (the headless
  GraphViewer embed is unreliable — Spike 4 caveat); CI asserts structure/round-trip, humans confirm visuals.

## Alternatives considered
- bpmn-js adapter — **rejected** (mandatory watermark, D5).
- D2/TALA commercial adapter — **rejected** (D6).
- EMF / SVG-ungroup automation for editability — **rejected** (fragile, lossy).

## References
`04-architecture.md` §1/§6 (Q4) · `08-export-strategy.md` · `docs/spikes/spike-4-report.md` ·
`13-open-decisions.md` (D2, D5, D6, D7) · `02-risks.md` (R-14…R-19)
