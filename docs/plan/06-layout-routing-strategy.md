# Layout & Routing Strategy

Status: Proposed · 2026-06-11 · Backend: ELK (elkjs 0.11.x pinned) primary; details verified in research (see `03-engine-comparison.md` sources).

---

## 1. Integration Pattern

- **Long-lived Node subprocess** hosting a vendored, pinned elkjs bundle; JSON over stdin/stdout (newline-delimited request/response with ids). Pattern proven by `capellambse-context-diagrams`; Mermaid/D2/draw.io all embed ELK the same conceptual way.
- Cold start ~50–200 ms, warm calls ~5–20 ms — amortized by process reuse (NFR-2).
- Wire format = **ELK JSON** exactly as documented (children/ports/edges/sections/layoutOptions). Our adapter translates IR→ELK and ELK→positioned IR; no other component sees ELK JSON.
- Alternatives kept open: `mini-racer` (in-process V8) if subprocess management proves painful; documented in adapter so swap is local.
- **Sizes are inputs**: ELK does not measure text. The measurement service (uharfbuzz; `07-rtl-arabic-strategy.md`) computes label boxes → node min sizes before layout. This ordering is mandatory for Arabic correctness (R-2).

## 2. Hint Mapping (schema → ELK)

| Schema hint | ELK option |
|---|---|
| `direction: LR/RL/TB/BT` | `elk.direction: RIGHT/LEFT/DOWN/UP` (RL mirroring = FR-4.3) |
| `routing.mode: orthogonal/polyline/curved` | `elk.edgeRouting: ORTHOGONAL/POLYLINE/SPLINES` |
| `ports[].side`, fixed offsets, order | `elk.port.side`, `portConstraints: FIXED_ORDER/FIXED_POS` |
| lane membership | `elk.partitioning.activate` + `elk.partitioning.partition` per node |
| nesting (groups/containers) | `children` + `elk.hierarchyHandling: INCLUDE_CHILDREN` |
| `edge.priority` | `elk.layered.priority.*` |
| spacing/alignment | `elk.spacing.*`, `elk.layered.spacing.*` |
| crossing minimization | `elk.layered.crossingMinimization.strategy` (default LAYER_SWEEP) |
| `respectManualPositions` | `FixedLayout` passthrough or `elk.position` + interactive strategies |
| `waypoints` (manual) | post-layout override on edge sections (engine-side splice) |
| `avoidZones` | no ELK equivalent → best-effort post-pass / libavoid (Full) |

## 3. Family → Layouter Routing

| Family | Layouter |
|---|---|
| flowchart, architecture/C4, dependency, state, deployment | ELK layered |
| swimlane/process | ELK layered + partitioning (lanes), phases as second axis — see §4 |
| ER, class | ELK layered + ports (per-row anchors for ER) |
| mindmap | ELK mrtree / radial |
| sequence | **custom deterministic layouter** (lifelines = ordered columns; messages = time-ordered rows; activations/fragments as rect overlays). Graph engines are the wrong tool; owning this is low-risk (R-12) |
| manual/fixed | FixedLayout (+ future routing-only pass) |

## 4. Swimlanes (flagship; R-9 mitigation; **MVP per D3:B**)

Visual target locked by `references/analysis.md` (title bar, header pills at flow-start side, hue→tints lane theming, numbered badges, reference shape set, back-edges). Prior art: the local `horizontal-swimlane-diagram` skill produces this exact style as draw.io files — reuse its geometry/style constants where applicable.
Primary approach: lanes = ELK partitions along the axis perpendicular to flow; lane bands drawn by the renderer from positioned-node extents (max/min per partition) with configured lane padding/headers. Phases = orthogonal grid lines computed from node `phase` membership.
Validation spike (Phase 0, MVP-gating): rebuild the 3 reference diagrams through this path; acceptance = lanes straight, nodes contained, cross-lane edges orthogonal (incl. the bad-loop back-edge and the multi-lane Deliver→Receive edge), no node/lane-border overlaps.
**Fallback (pre-approved)**: own lane-grid layout — fixed lane bands; ELK lays out *within* each lane independently; cross-lane edges routed orthogonally between fixed anchors. More code, fully deterministic, matches enterprise slide style closely.
Nested lanes: best-effort (declared limitation; AM-6).

## 5. Crossing Minimization & Residual Limits

- ELK layered minimization on by default; hierarchical edges cause known avoidable crossings (#503/#401, R-8) → keep compiled hierarchy shallow (flatten visual-only groups before layout; redraw their frames from child extents after).
- Post-layout QA pass counts crossings/overlaps into the RenderReport (regression-trackable metric).
- If Phase 5 quality is insufficient: evaluate **libavoid** (LGPL, routing-only, pins/ports, crossing penalties) as a post-placement re-router behind the same LayoutAdapter contract. Build/bindings friction documented (no PyPI; SWIG/pybind effort) — that cost is *not* in MVP.

## 6. Fallback: Graphviz dot

For Node-free environments: `dot` via `graphviz` PyPI. Capability deltas (declared, validated): compass-ports only, no partitioning (lanes via rank hacks rejected — swimlanes unsupported on this backend), `splines=ortho` approximate. `rankdir=RL` supported. Fallback is a degraded mode, not feature-parity.
