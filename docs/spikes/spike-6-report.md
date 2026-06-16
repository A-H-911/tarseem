# Spike 6 — mindmap ELK algorithm (mrtree vs radial)

**Status: PASS** (mindmap is viable on the pinned ELK; objective criteria met).
**Recommendation: `mrtree` as the mindmap default; `radial` as an opt-in style for
shallow/balanced maps only.** The default is an owner-sign-off recommendation, not a
self-certified fact — there is no mindmap *visual* oracle in the plan (see "Oracle" below).

Date: 2026-06-16 · Code: `spikes/spike-6-mindmap-layout/run.py` (throwaway) ·
Artifacts: `spikes/spike-6-mindmap-layout/out/` (gitignored).

## Question

Sub-stage 6 needs a non-layered layouter for mindmaps — `01-requirements.md:50` and
`06-layout-routing-strategy.md:38` both say "ELK mrtree / radial" but **pick neither**.
Can the **pinned elkjs 0.11.1** `elk.bundled.js` produce an acceptable, *deterministic*
mindmap via `mrtree` or `radial`, driven through the **production** `ElkServerProcess`
(only `elk.algorithm` differs — no protocol change) — and which should be the default?

## Method

Both providers are registered in the bundle (grep: `org.eclipse.elk.mrtree` ×8,
`org.eclipse.elk.radial` ×13), but registration ≠ usable. The spike drives the real
subprocess client (`tarseem.layout.elk._server.ElkServerProcess`) with hand-built ELK
graphs — exactly what a render would drive — on **two** inputs:

- **balanced** — root + 4 branches + 2–3 leaves each (15 nodes). The tidy case.
- **uneven** — root with 10 children + one deep chain (`C1→C1a→C1b→C1c`) + two small
  sub-trees (18 nodes). Lopsided trees are where overlap / root-detection fail.

Per-algorithm option dicts (NOT the layered-specific `_BASE_OPTIONS`, so an overlap is a
real failure, not a config artifact): `mrtree` with `elk.direction=RIGHT`; both with
`elk.spacing.nodeNode=40`.

## Criteria & results

| case | 1. runs | 2. node overlaps | 3. deterministic¹ | 4. edge sections² |
|---|---|---|---|---|
| balanced / **mrtree** | ✅ | **0** | ✅ | 14/14 routed, 18 bends |
| balanced / radial | ✅ | 0 | ✅ | 14/14 routed, 0 bends (straight spokes) |
| uneven / **mrtree** | ✅ | **0** | ✅ | 16/16 routed, 23 bends |
| uneven / radial | ✅ | **3** ❌ | ✅ | 16/16 routed, 0 bends |

¹ **Determinism is across a fresh subprocess spawn** (spawn → layout → tear down → spawn
→ layout → compare rounded-coord sha256), matching invariant 7 ("same spec ⇒ identical
output across renders"), not two `layout()` calls on one warm process. All four matched —
`mrtree`/`radial` are RNG-free here (unlike `force`/`stress`).
² Both algorithms return ELK `sections` for **every** edge → the mindmap family can reuse
the existing `_from_elk` edge path; **no custom edge router needed** (unlike sequence/lanegrid).
`mrtree` routes orthogonal-ish with bend points; `radial` returns straight centre spokes.

## Visual verification (`out/*.png`, owner judgement)

- **`balanced-mrtree.png`** — textbook left-to-right mind map: root anchored left, branches
  fan right, leaves at the outer edge; three levels cleanly legible.
- **`balanced-radial.png`** — classic root-centred "sun": root in the middle, 4 branches
  around, leaves outermost. Attractive on a *balanced* tree.
- **`uneven-mrtree.png`** — still clean on the lopsided tree: 10 children stacked, the deep
  `C1→…→C1c` chain extends rightward, sub-trees nest without collision. **0 overlaps.**
- **`uneven-radial.png`** — the deep chain `C1→C1a→C1b→C1c` **piles up** at the lower-right
  (boxes stacked on each other). Radial places nodes on concentric rings by *depth*, so a
  branch far deeper than its siblings is crushed into one angular sector → the 3 overlaps.

## Oracle (why "recommend", not "certify the default")

`12-acceptance-criteria.md` F1 requires mind map only as a *supported family* (gallery
completeness); there is **no mindmap visual target** (unlike swimlane's `references/analysis.md`).
Per this project's pattern — every Phase-6 visual call (RTL header side, badge style, …) went
to owner sign-off — the spike **certifies the objective criteria** and **recommends** the
default; the owner picks `mrtree`-vs-`radial` from the side-by-side renders.

## Conclusion

- **`mrtree` — PASS, recommended default.** Clean, deterministic, zero overlaps on *both*
  the balanced and the lopsided tree; reusable ELK edge routing; reads as a proper mind map.
- **`radial` — viable opt-in only.** Runs and is deterministic, looks best on shallow/balanced
  maps, but **overlaps nodes on uneven/deep trees** → unsafe as a general default. Offer it as
  `mindmap.style="radial"` (or theme), gated/documented for balanced maps.

## Adapter change this implies (for the build, not this spike)

Localized and small — no protocol/server change:

1. Parameterize `ElkLayout` to accept an `algorithm` + a per-algorithm option set; keep the
   layered `_BASE_OPTIONS` for graph families, add a `mrtree` option set for mindmap
   (`elk.algorithm=mrtree`, `elk.direction` from spec `direction`, `elk.mrtree.spacing.nodeNode`).
2. Dispatch `diagram_type == "mindmap"` → mrtree in `engine.py` (like the sequence/lanegrid fork).
3. `_from_elk` already consumes `sections` → mindmap edges work with **no** new router.
4. Update `ElkLayout.capabilities()["algorithms"]` to include the wired algorithm(s).
5. Compile: a mindmap profile (root detection = the node with no incoming edge; nodes are
   plain labelled boxes — no chrome) + a golden `examples/mindmap-*.json` + 3-OS baselines.

## Follow-ups / open

- **Owner sign-off:** `mrtree` default + whether to ship `radial` as an opt-in now or later.
- **`elk.direction` for mindmaps:** `RIGHT` (used here) reads best; expose via the spec
  `direction` field. RTL mindmaps → `LEFT` (consistent with the geometry-only RTL invariant).
- **Large fan-out:** the 10-wide root stacked tall but fine; revisit spacing tuning if real
  mindmaps go very wide (mrtree has packing options, untested here).
