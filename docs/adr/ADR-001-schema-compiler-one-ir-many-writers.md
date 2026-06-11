# ADR-001 — Schema-compiler architecture: one positioned IR, many writers

- Status: **Accepted**
- Date: 2026-06-11
- Deciders: Anas (owner); seeded from `docs/plan/04-architecture.md` §1–2 during Phase 1
- Invariant: **#1**

## Context
Tarseem must turn validated JSON specs into architecture-grade diagrams spanning flowchart,
architecture/C4, dependency and **swimlane** families (sequence next), with first-class
Arabic/RTL and genuinely **editable** exports (draw.io, PPTX). Two architectures were evaluated
(`04-architecture.md` §1, `03-engine-comparison.md`):

- **A. DSL transpiler** — compile specs to Mermaid/PlantUML/D2 text and let those render.
  Rejected as core: no swimlanes (Mermaid/D2) or horizontal lanes (PlantUML), broken/unverified
  Arabic (R-6), no ports/manual positions, styling ceilings, no editable output.
- **B. Schema compiler** — the engine owns an internal model and delegates only geometry.

## Decision
Adopt the **schema compiler**. The pipeline is:

```
spec → schema validation → semantic validation → logical IR
     → text measurement → layout → POSITIONED IR (single source of truth)
     → writers: SVG (canonical) · PNG/PDF · draw.io · PPTX · Mermaid/PlantUML (lossy) · gallery · JSON sidecar
```

- The **positioned IR is the single source of truth**; every target is a cheap serialization of it.
- **No writer computes its own layout.** Editability becomes a *writer* problem, not a conversion problem.
- DSL outputs (Mermaid/PlantUML) are retained **only** as best-effort source-export adapters.
- Two IR states: *logical IR* (post-compile) and *positioned IR* (post-layout).

## Consequences
- (+) One layout serializes to every target; editable files start pixel-equal to the published SVG.
- (+) Full control over styling, Arabic shaping, lane geometry, theme portability.
- (−) We own more surface: IR dataclasses, per-type compilers, the SVG renderer, and each writer.
- (−) The positioned-IR contract must stay stable; changes ripple to all writers (mitigated by adapter contracts, ADR-005).

## Alternatives considered
- DSL transpiler as the core engine — **rejected** (capability + Arabic + editability ceilings).

## References
`04-architecture.md` §1–2 · `00-executive-summary.md` · `03-engine-comparison.md` · `02-risks.md` (R-6)
