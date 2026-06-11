# ADR-002 — Layout: ELK subprocess for graph families; custom lane-grid for swimlane

- Status: **Accepted**
- Date: 2026-06-11
- Deciders: Anas (owner); seeded from `04-architecture.md` §1/§6, `06-layout-routing-strategy.md`; swimlane path **confirmed by Phase 0 Spike 3**
- Invariant: **#2**

## Context
Diagrams need ports, compound nodes, orthogonal routing and crossing minimization. ELK (elkjs) is
the only OSS engine offering all of these plus a JSON service contract (`03-engine-comparison.md`).
Swimlanes, however, need **cross-axis lane banding** with global flow alignment — which ELK does
not provide: Spike 3 proved `elk.partitioning` orders nodes along the **flow/layer axis** (phases),
not the lane axis (`docs/spikes/spike-3-report.md`).

## Decision
One `LayoutAdapter` contract, multiple implementations selected by family:

1. **Graph families** (flowchart, architecture/C4, dependency, state, deployment, ER, class, mindmap)
   → **ELK layered** via a **long-lived Node subprocess** hosting a **vendored, pinned elkjs** bundle
   (elkjs **0.11.1**), JSON over stdio. **ELK JSON is confined to the LayoutAdapter and never leaks**
   into the IR or any writer. (Spike 1 validated: 50-node compound + ports, warm ~30 ms.)
2. **Swimlane/process** → **custom deterministic lane-grid layouter** (one step per column = topological
   number; lanes = fixed rows), **not** ELK partitioning. This is the plan's pre-approved fallback
   (`06 §4`); Spike 3 reproduced the references with it. **R-9 retired for MVP.**
3. **Sequence** → custom deterministic layouter (lifelines = columns, messages = time-ordered rows).
4. **Fallback** → Graphviz `dot` for Node-hostile environments, at declared (degraded) fidelity.

Cross-cutting: **sizes are inputs** — text measurement (ADR-004) precedes layout for all families.
Determinism via pinned elkjs + pinned Chromium + spec-hash/engine-version stamping.

## Consequences
- (+) Best-in-class graph layout where it helps; deterministic, reference-matching swimlanes where ELK can't.
- (−) Node.js becomes a managed runtime dependency (`engine doctor` verifies it + the pinned bundle).
- (−) Two+ layouters behind one contract; the lane-grid layouter needs its own **orthogonal router with
  channel assignment** for co-terminal/long edges (Spike 3 caveat; tracks R-13).
- (−) elkjs must be **vendored + pinned**, not npm-resolved at runtime (no network at render time).

## Alternatives considered
- ELK `partitioning` for lanes — **rejected** (wrong axis; Spike 3 evidence).
- In-process V8 via mini-racer — kept open as a documented swap inside the adapter.
- Pure-Graphviz core — **rejected** (no swimlanes/partitioning).

## References
`04-architecture.md` §1/§6 (Q3,Q6) · `06-layout-routing-strategy.md` · `docs/spikes/spike-1-report.md` ·
`docs/spikes/spike-3-report.md` · `02-risks.md` (R-8, R-9, R-13)
