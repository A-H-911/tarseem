# Phase 7 — Full Acceptance Audit (F1–F12)

Status: 2026-06-17 · Exit artifact for Phase 7. Criteria are from
[`plan/12-acceptance-criteria.md`](plan/12-acceptance-criteria.md) "Full Target Acceptance". Each
row gives the verdict and the evidence (code / tests / CI / ADRs / PRs). Verdicts are honest: two
criteria are **not** fully met and are called out rather than rubber-stamped.

| # | Criterion | Verdict | Evidence |
|---|---|---|---|
| **F1** | All major families: flowchart, sequence, architecture/C4, deployment, state, ER, class, **activity**, mind map, swimlane, dependency | **PARTIAL — 10/11** | 10 families shipped & registered: `src/tarseem/families/*`, `examples/*.json`, gallery. **`activity` is NOT implemented.** It can now be added as a plugin with no core change (see F9) — tracked as the one remaining F1 gap. |
| **F2** | Arabic + RTL: shaping, mixed-script, RL mirroring, lane headers, exports — pixel-stable on 3 OS | **MET** | `tests/test_arabic_rtl.py`; Arabic goldens `examples/arabic-*.json`, `examples/swimlane-document-rtl.json`; per-OS baselines `tests/baselines/{win32,linux,darwin}`; CI matrix renders them. RTL also proven through the external `timeline` layouter. |
| **F3** | Swimlanes: horizontal + vertical lanes, phases, per-lane styling, cross-lane orthogonal flows, RTL variant, nested (best-effort) | **MET** | `tests/test_a12_swimlane.py`, `test_swimlane_vertical.py`, `test_swimlane_nested.py`, `test_phases.py`; ADR-007; `examples/swimlane-*.json`. |
| **F4** | Styling: full 6-level cascade; themes portable across SVG/drawio/PPTX (within ceilings) | **MET** | `tests/test_a5_styling.py`, `themes/cascade.py`; cross-writer fidelity in `tests/test_export_drawio.py`, `test_export_pptx.py` (CapabilityReports). |
| **F5** | Routing: orthogonal + curved, ports, waypoints, priorities; crossing counts within thresholds | **MET** | `tests/test_routing_hints.py`, `test_routing_benchmark.py`, `test_render_report.py`; optional libavoid rerouter `test_libavoid_router.py` (ADR-006). |
| **F6** | Cross-platform: full suite green on Windows, macOS, Linux | **MET** | `.github/workflows/ci.yml` 3-OS × py3.10/3.12; all Phase-7 PRs (#14–#18) merged green on the full matrix. |
| **F7** | Exports: SVG/PNG/PDF/HTML first-class; drawio + PPTX editable (Mermaid/PlantUML deferred) | **MET** | `export/{png,pdf,drawio,pptx}.py`; HTML = the gallery (`gallery/`); `tests/test_export_*.py`; draw.io Option-B CI gate `drawio-roundtrip.yml`. Mermaid/PlantUML explicitly deferred (the criterion permits it). |
| **F8** | Browser verification: gallery + E2E + screenshot regression operational and gating | **MET** | `tests/test_e2e_gallery.py`, `test_gallery.py`, `test_visual_regression.py`; gallery built in CI; baselines gate every matrix OS. |
| **F9** | Extensibility: new diagram type via plugin without core changes, proven twice incl. clone tutorial | **MET** | ADR-008; `tarseem.families` registry + entry-point dogfood (`tests/test_plugin_registry.py`); tutorial `docs/extending/clone-a-type.md`; **two external plugins** — `incident-flow` (compile/`default_shape`, `tests/test_external_plugin_incident_flow.py`) + `timeline` (custom `layouter_factory`, `tests/test_external_plugin_timeline.py`); each guarded by a "core never names the type" test. PRs #14, #15, #18. |
| **F10** | Documentation complete per `10-documentation-plan.md`, incl. limitations + troubleshooting | **SUBSTANTIALLY MET (not re-audited)** | Guides `docs/guide/{quickstart,families,rtl-arabic,exports,powerpoint,agents}.md`; `docs/extending/clone-a-type.md`; ADR-001…009; per-phase progress in `docs/spikes/`; `tests/test_docs.py`. **Not re-audited line-by-line against `10-documentation-plan.md` this phase** — flagged for a doc-completeness pass. |
| **F11** | Agent-ready: pure-function generate API, JSON errors, published schema bundle, reference skill | **MET** | `tarseem.generate` (`agent.py`) with the `{code,path,message,hint}` contract; `schema_bundle()`; CLI `generate`/`schema`; reference skill `integrations/claude-skill/SKILL.md`; guide `docs/guide/agents.md`. `tests/test_agent_surface.py`, `test_skill_integration.py`. PRs #16, #17. |
| **F12** | Schema v1.0 frozen with versioning + migration tooling | **MET** | ADR-009; `schema/core.py` (`$id` 1.0, `specVersion ^1\.\d+$`, `kind` dropped); profile enforcement in `validation/__init__.py` (`E_PROFILE`); `migrate.py` + CLI `migrate`; `tests/test_schema_freeze.py`. This PR. |

## Summary

- **10 of 12 fully met.** Phase-7 deliverables (F9, F11, F12) are complete and tested.
- **F1 — partial:** the `activity` family is unimplemented (10/11). With the v1.0 plugin API, it is
  now addable as an external plugin without touching the engine — the natural way to close it.
- **F10 — substantially met but not re-audited** against `10-documentation-plan.md` this phase; a
  dedicated doc-completeness pass is the honest closeout.

These two are the remaining work before declaring full acceptance / tagging v1.0; neither is a
Phase-7 (extensibility/agent/freeze) deliverable.
