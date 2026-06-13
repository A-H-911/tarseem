# Phase 5 — Advanced Layout, Routing Depth & Remaining Families — progress

Governing docs: `docs/plan/11-phased-plan.md` (Phase 5), `docs/plan/06-layout-routing-strategy.md`
(§2 hint map, §5 libavoid). Branch: **`phase-5-routing`** (4 commits ahead of `main`, not yet
pushed / no PR). Exit criteria: F5 routing demonstrable **+ new families in the gallery**.

## Sub-stages

| # | Sub-stage | Status | Where |
|---|---|---|---|
| 1 | Routing hints | ✅ done | see below |
| 2 | Benchmark corpus + CI threshold gate | ✅ done | `tests/test_routing_benchmark.py`, `tests/benchmarks/` |
| 3 | libavoid evaluation → build | ✅ done (experimental, opt-in) | `ADR-006`, `src/tarseem/layout/libavoid/` |
| 4 | Swimlane polish | ✅ done | vertical lanes (`f06c29e`) + nested lanes (`370a157`) |
| 5 | New families | ✅ done | state + deployment (`56fd8f2`), ER-with-ports (`ca09990`); win32 baselines (`7347e5f`) |

**Phase 5 complete** (all 5 sub-stages). Branch `phase-5-routing` not yet pushed / no PR.
Remaining ops: linux + macOS baselines for the 5 new goldens via the `regen-baselines`
branch / `workflow_dispatch` (`.github/workflows/baselines.yml`) — the visual suite skips
those samples per-platform until committed, so CI stays green meanwhile.

## Done — detail

**1. Routing hints** (threaded schema → compile → IR → ELK adapter; defaults inert):
- `edge.routing.waypoints` — post-layout splice over ELK's polyline; **survives re-render** (round-trip test).
- `edge.priority` → `elk.layered.priority.straightness` (white-box test).
- `edge.preferredDirection` (UP/DOWN/LEFT/RIGHT) → dedicated `FIXED_SIDE` source port (probe-proven).
- node `position` + `layout.respectManualPositions` → ELK INTERACTIVE strategies. **Honoured as a
  strong ordering hint, not exact-pixel pinning** (ELK normalizes spacing — documented).
- Tests: `tests/test_routing_hints.py` (11).

**2. Benchmark gate**: overlaps must be 0 (hard); crossings ≤ a per-sample budget = today's measured
count (a ratchet — routing can improve but never silently regress). Runs under pytest = the 3-OS CI
gate. Baseline: overlaps 0 everywhere; crossings 0 except `swimlane-bug-triage` (1) and
`bench-dependency-web` (2).

**3. libavoid** (`ADR-006`): vendored `libavoid-js@0.5.0-beta.5` (WASM) as an **off-by-default,
opt-in, experimental** post-placement re-router (`layout.router: "libavoid"`). LGPL-2.1 → optional
extra only; default path stays ELK/Apache-2.0. Empirical finding: **worse than ELK for auto-layout**
(it can't beat ELK's integrated placement+routing); its niche is **obstacle avoidance on fixed
positions** (cut edges-through-boxes ~80%, 10→2 vs naive). `.gitignore` has an exception so the
`dist/` WASM ships in the wheel. `engine doctor` reports it (optional/informational).

**4. Swimlane polish** — both halves done as low-risk **post-passes** over the untouched
horizontal layout (so flat/horizontal output stays byte-identical → no baseline churn):
- **Vertical lanes** (`layout.laneOrientation: "vertical"`): lanes become columns, flow runs
  top→bottom. A uniform coordinate transpose `T(x,y) = (m + y−lanes_top, vtop + x−m)` with
  width↔height swap; routing + topo order carry over. Renderer chrome is orientation-aware
  (title stays on top, header pills move to column tops). Limits (AM-6): portrait node
  aspect, phases not drawn, TB flow only. Example `swimlane-vertical-release.json`.
- **Nested lanes** (`lane.parent`): the parent becomes an outer header gutter spanning its
  children (a single x-translate). Limits (AM-6): one level, nodes attach to leaf lanes,
  horizontal-only. Example `swimlane-nested-delivery.json`. Dropped the orphan per-lane
  `orientation` schema key.
- Tests: `tests/test_swimlane_vertical.py` (11) + `tests/test_swimlane_nested.py` (7).

**5. New families** — three families added; the two cheap ones share the ELK graph path
(only new shape vocab), ER adds a table writer + per-row port anchoring:
- **state**: rounded-box states; `initial` (filled dot) / `final` (bullseye) pseudostate
  markers sized as fixed squares. **deployment**: 3D `cube` node (top+right depth faces) as
  the default shape; datastores as cylinders. Both route through ELK unchanged.
- **ER**: entity = attribute table. A node's `attributes` compile to `EntityRow`s whose
  vertical geometry is stamped once in measure (shared by the table writer and the layout
  adapter). Edges carry `sourcePort`/`targetPort` (an attribute id); ELK places the entities
  and the adapter replaces the ported edge's route with an orthogonal connector anchored to
  the exact row on each facing side. Dedicated `render/er.py` table writer (PK/FK key tags).
  Validation accepts attribute ids as port targets.
- Examples: `state-order-lifecycle`, `deployment-web-stack`, `er-shop`. Tests:
  `test_family_state_deployment.py` (8) + `test_family_er.py` (8). Benchmark budgets:
  deployment 1, er-shop 1 (both topology-inherent, overlaps 0).

## Bans / invariants honoured

- libavoid (LGPL) is **optional + off by default**; required path stays Apache-2.0/ELK-only.
- ELK JSON and Adaptagrams' object model each stay **inside their adapter**; only routed points cross out.
- WASM is byte-identical across OS → determinism (invariant 7) holds; pinned like elkjs.

## Resume checklist (sub-stages 4–5)

1. Re-anchor: CLAUDE.md + `git log --oneline -8` + Phase 5 in `11-phased-plan.md` + run `.venv` pytest.
2. New families dispatch in `src/tarseem/engine.py` (family → layouter), default shapes in
   `src/tarseem/model/compile.py` `_DEFAULT_SHAPE`. `state`/`deployment` are ELK-layered (cheap);
   `ER` needs ports (schema already has `ports`/`sourcePort`/`targetPort`).
3. Every family lands with a golden `examples/*.json`, a gallery card, and per-OS baselines
   (regen via `.github/workflows/baselines.yml`; see `docs/spikes/phase-4-progress.md`).
4. No phase ships with red CI; gate stays green; nothing reaches `main` without a PR.
