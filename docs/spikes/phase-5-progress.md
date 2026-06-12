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
| 4 | Swimlane polish | ⬜ **next** | vertical-lane hardening; nested lanes best-effort + documented limits |
| 5 | New families | ⬜ **next** | `state`, `deployment`/infra, `ER`-with-ports — each with a golden sample + gallery card + per-OS baselines |

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
