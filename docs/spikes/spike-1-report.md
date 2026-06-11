# Spike 1 Report — elkjs round-trip (Python ↔ long-lived Node subprocess)

Status: **PASS** · 2026-06-11 · throwaway code in `spikes/spike-1-elk/`

## Objective (from `11-phased-plan.md` Phase 0 / `06-layout-routing-strategy.md` §1)
Prove the core layout integration pattern before any engine scaffolding:
- A **long-lived Node subprocess** hosting a **pinned** elkjs bundle, driven from Python over **JSON-stdio**.
- Lay out a **50-node compound graph with ports** (the features off-the-shelf engines lacked).
- Measure **cold** (first call after spawn) and **warm** (process reused) latency vs the NFR-2 budget.

## What was built
| File | Role |
|---|---|
| `package.json` | pins `elkjs@0.11.1` (only dependency) |
| `elk_server.js` | long-lived server: newline-delimited JSON requests `{id, graph}` on stdin → `{id, ok, graph}` on stdout; requests serialized via a promise chain; diagnostics to stderr only |
| `elk_client.py` | `ElkServer` — spawns `node elk_server.js` once, synchronous `layout(graph)` per call, matches response `id`, drains stderr on a background thread |
| `gen_graph.py` | deterministic compound graph: 5 containers × 10 leaves = **50 leaves**, each leaf with WEST in-port + EAST out-port (`FIXED_ORDER`); intra-container chains + 4 cross-hierarchy edges (root-declared, `INCLUDE_CHILDREN`) |
| `bench.py` | runs 1 cold + 30 warm layouts, validates every leaf has x/y and every edge a routed section, writes `out/results.json` + `out/laid_out_sample.json` |

Design note: required `elkjs/lib/elk.bundled.js` (main-thread, worker inlined) rather than the default Web-Worker entry — fewer moving parts in a dedicated subprocess; we provide ordering ourselves.

## How to run
```
cd spikes/spike-1-elk
npm install --no-audit --no-fund     # installs elkjs@0.11.1
python bench.py                      # prints metrics; writes out/*.json
```

## Pinned versions (this run)
- elkjs **0.11.1** · Node **v26.3.0** · npm 11.16.0 · Python **3.13.7** · Windows 11 Pro (26200)

## Measurements
```
leaf_nodes 50 · ports 100 · edges 49 · edges_routed 49 · validation_issues 0
root_size 5624 × 114
cold_ms  187.1
warm_ms  n=30  min 15.37  median 30.62  p95 32.45  max 47.41  mean 29.0
```
Structural spot-check of `out/laid_out_sample.json`:
- Containers `c0..c4` each sized **1080×90** by ELK from child extents (c0 at 12,12) — compound nesting works.
- Leaf `n0_0` at (28,30), 70×40; ports `n0_0.in` on **WEST** (x=−8), `n0_0.out` on **EAST** (x=70) — `FIXED_ORDER` honored.
- Cross-hierarchy edge `e_x_1` carries a routed `section` with start/end points — `INCLUDE_CHILDREN` edges route across containers.

## PASS/FAIL vs criteria
| Criterion (from spike plan) | Result |
|---|---|
| Subprocess stays alive across N calls | **PASS** — 31 layouts served by one process; clean shutdown on stdin close |
| 50-node compound graph **with ports** returns valid positions + routed edges | **PASS** — 50/50 leaves positioned, 100 ports side-correct, 49/49 edges routed, 0 issues |
| Warm latency within NFR-2 (≤100 nodes ≤2 s warm) | **PASS** — warm median 30.6 ms, p95 32.5 ms (~60× margin); cold 187 ms within the 50–200 ms expectation |

**Verdict: PASS.** The ELK-via-subprocess pattern is validated for the primary layout path.

## Surprises / caveats
1. **Warm latency ~30 ms, not the 5–20 ms loosely cited in `06 §1`.** Benign — this graph is deliberately port-heavy (100 `FIXED_ORDER` ports) with orthogonal routing + hierarchy; a flatter graph would be faster, and 30 ms is ~60× under budget. Flagged so the Phase-2 perf baseline measures *realistic* swimlane graphs, not just this stress path.
2. **Degenerate topology.** The test graph is essentially one long chain (root_size 5624×114, one node per layer). Intentional — it maximally exercises ports + compound + cross-hierarchy routing for a round-trip spike, but it is **not** a realistic diagram shape. Realistic multi-lane layouts are Spike 3's job.
3. **No screenshot.** This spike is latency/structural; evidence is the JSON metrics + `out/laid_out_sample.json`. Visual artifacts begin in Spike 2 (Arabic SVG→PNG) and Spike 3 (swimlane render).
4. **Node v26** (newer than the LTS the plan assumed) ran elkjs 0.11.1 with no issues; elkjs is pure JS, so engine version is low-risk. Pin recorded above for determinism.

## Implications for the engine (carry into Phase 1/2)
- The `ElkServer` request/response contract (id-matched JSON lines, stderr-isolated, serialized) is a sound seed for the real `ElkLayout` adapter; keep ELK JSON confined to that adapter per invariant #2.
- Decide subprocess **lifecycle/health** (restart on crash, `doctor` probe) in Phase 2 — out of scope here.
- elkjs bundle should be **vendored + pinned** (not npm-resolved at runtime) for the shipped engine; this spike used npm install for convenience.
