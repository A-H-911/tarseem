# Phase 7 — Extensibility & Agent Readiness — progress

Governing docs: `docs/plan/11-phased-plan.md` (Phase 7), `docs/plan/12-acceptance-criteria.md`
(F9–F12), `docs/plan/05-schema-strategy.md` (schema freeze). Exit: full F1–F12 audit table with
evidence links + v1.0 schema freeze (gated on **two** passing plugin exercises).

Delivery shape (owner, 2026-06-17): **staged PRs per sub-task**, each green before the next.
Plugin depth (owner, 2026-06-17): **full entry-point dogfood** — built-ins register through the
same `tarseem.types` entry-point group third parties use (ADR-008).

## Sub-stages

| # | Sub-stage | Status | Where |
|---|---|---|---|
| 1 | **Plugin registry + dogfood** — `DiagramTypePlugin` contract; `tarseem.types` entry-point registry; 10 built-ins converted to plugins + declared as entry points; 6 hardcoded dispatch sites → registry lookups; public alias `tarseem.plugins`; ADR-008 | ✅ done (PR1) | `families/`, `plugins/__init__.py`, `pyproject.toml`, `docs/adr/ADR-008-*.md` |
| 2 | **incident-flow plugin + clone tutorial** — external "incident-flow" family built from flowchart via the docs (plugin exercise #1, F9 benchmark); `docs/extending/clone-a-type.md` + installable `examples/plugins/incident-flow/` | ✅ done (PR2) | `docs/extending/clone-a-type.md`, `examples/plugins/incident-flow/` |
| 3 | **Agent surface** — single `generate(spec) -> artifacts + report`; JSON error contract `{code,path,message,hint}`; published schema bundle for LLM tool-use; SVG-default + raster-subprocess guard for the Chromium pool | ✅ done (PR3) | `agent.py`, `schema/__init__.py`, `cli/__init__.py` |
| 4 | **Reference slash-command / skill integration** (F11) | ✅ done (PR4) | `integrations/claude-skill/SKILL.md` |
| 4b | **Plugin exercise #2** — `timeline`: external family with a custom `layouter_factory` (pure-Python single-axis layout, RTL-aware), stressing the *layout* extension point (second freeze gate) | ✅ done | `examples/plugins/timeline/` |
| 5 | **Schema v1.0 freeze proposal + `migrate` command** — diff shipped schema vs `05-schema-strategy.md`; list breaking decisions; build `engine migrate`; freeze only after the two plugin exercises pass (F12) | ⏳ (PR5, gated) | — |

## PR1 — Plugin registry + entry-point dogfood (2026-06-17)

Realises **invariant 8** and unblocks **F9**. The hardcoded `diagramType` dispatch that grew
through Phases 2–6 is replaced by one registry; built-ins and third-party families now load
through the identical `tarseem.types` entry-point mechanism (ADR-008).

- **Contract** (`families/base.py`): `DiagramTypePlugin` — a frozen, declarative descriptor
  (`default_shape`, `member_compartments`, `layouter_factory`, `svg_renderer`, `export_chrome`,
  `layout_engine_name`, `schema_extension`). Cloning a family is data, not subclassing.
- **Registry** (`families/__init__.py`): entry-point-first discovery (group `tarseem.types`) +
  a `pkgutil` bundled fallback so stale editable installs still work; unknown `diagramType` →
  generic-ELK default (preserves the pre-registry behavior, no crash).
- **10 built-ins** as `families/<name>.py` each exporting `PLUGIN`, declared as entry points in
  `pyproject.toml`. Public author alias: `tarseem.plugins`.
- **6 dispatch sites converted** to `get_plugin(...)`: `model/compile.py` (default shape +
  member compartments), `engine.py` (layouter), `render/svg.py` (renderer; generic body
  extracted to `render_generic_svg`), `export/drawio.py` + `export/pptx.py` (sequence chrome +
  margin), `export/metadata.py` (layout-engine label). Structural checks kept (`diagram.lanes`,
  `node.rows`/`node.members`/`node.shape`) — they are IR properties, not family routing.
- **Behavior-preserving, verified.** Full suite byte-identical to the pre-refactor green baseline
  (same dot/skip pattern; determinism + 3-OS visual-regression baselines unchanged — no golden
  or baseline regen). ruff + mypy clean. New: `tests/test_plugin_registry.py` (7) — entry-point
  dogfood, descriptor correctness, unknown-type fallback, and registry-driven compilation.
- **Known internal coupling (documented in ADR-008, not blocking F9):** the ELK adapter still
  picks `mrtree`/`radial` for mindmaps by `diagram_type` internally; `EDGE_WIDTH_DEFAULT` stays a
  shared styling constant; `schema_extension` is declared but not yet enforced (lands with PR5).

## PR2 — incident-flow external plugin + clone-a-type tutorial (2026-06-17)

**Plugin exercise #1 (F9), the first of the two the v1.0 freeze is gated on.** Proves a third
party adds a diagram type with zero engine edits.

- **Tutorial** `docs/extending/clone-a-type.md`: the `DiagramTypePlugin` contract table, the
  5-line clone, entry-point packaging, the editable-reinstall gotcha, and a `grep` to prove the
  core is untouched.
- **Worked external package** `examples/plugins/incident-flow/` — its **own distribution**
  (`tarseem-incident-flow`, separate `pyproject.toml`, depends on `tarseem`), registering
  `incident-flow` on the `tarseem.types` group. Lives *under* `examples/` but in a subdirectory,
  so the gallery/baseline machinery (which globs `examples/*.json` non-recursively) never sees it.
  The only customisation is `default_shape="stadium"`; ELK layout + the generic renderer are
  inherited.
- **Verified end-to-end:** installed editable → discovered via entry points → renders through the
  full pipeline (shapeless `detect` node became a stadium = the plugin's default drove compile;
  explicit `diamond` on `triage` preserved) → exports svg + drawio with a CapabilityReport.
- **CI** installs the example plugin (`pip install -e examples/plugins/incident-flow --no-deps`)
  so the F9 tests run on the matrix; `--cov=tarseem` does not measure the external package.
- **F9 guard test** `test_engine_core_never_names_the_external_type`: greps `src/tarseem/**.py`
  for the literal `incident-flow` and asserts none — caught two core docstrings naming the example
  (now neutralised to a generic `my-flow` placeholder).
- **PR1 tests relaxed:** `all_plugins()` assertions moved from `== BUILTINS` to `BUILTINS <= …`
  (external plugins may now be installed). Tests: `tests/test_external_plugin_incident_flow.py` (4).

## PR3 — agent surface: generate() + JSON errors + schema bundle (2026-06-17)

Lands **F11** (agent-ready: pure-function generate API, JSON errors, published schema bundle).
The slash-command/skill reference (PR4) wraps this.

- **`tarseem.generate(spec, formats=("svg",), out_dir=None, name=...)`** (`agent.py`) — one call,
  JSON in / JSON-serializable out, **never raises for a bad spec**: invalid input returns
  `{"ok": false, "errors": [{code, path, message, hint, severity}], "warnings": [...]}` (the 05 §5
  contract, reusing `errors.Issue`). Success returns `{ok, diagramType, svg (inline), artifacts,
  report, capabilities, warnings, provenance, versions}`.
- **SVG-default + raster-subprocess guard.** SVG/draw.io/PPTX are pure-Python and run in-process;
  PNG/PDF (the Chromium pool) are **always** run in a fresh `python -m tarseem.agent` subprocess,
  so the sync Playwright pool never collides with a caller's asyncio loop (the documented agent
  constraint). File formats require `out_dir`; SVG is inline. The subprocess speaks the same JSON
  payload on stdout (ASCII-escaped for Windows cp1252 safety).
- **`tarseem.schema_bundle()`** (`schema/__init__.py`) — the core JSON Schema (2020-12) with
  `diagramType` enriched by the **live registry** (built-ins + installed plugins) as an `enum`,
  for LLM tool-use / IDE `$schema`. The internal validation schema stays permissive; the bundle is
  a publishing view.
- **CLI** (`cli/__init__.py`): `tarseem generate <spec> [-f …] [-o …]` (JSON payload, exit 1 if
  `!ok`) and `tarseem schema [-o …]` (emit the bundle). Public API: `from tarseem import generate,
  schema_bundle`. Guide: `docs/guide/agents.md`.
- Tests: `tests/test_agent_surface.py` (11) — inline-SVG shape, JSON-serializable payload, the
  error contract, `E_OUTPUT` without `out_dir`, in-process draw.io export, raster-via-subprocess
  PNG, bundle enum, and both CLI commands. Full suite green; ruff + mypy clean.

## PR4 — reference skill integration (2026-06-17)

Completes the **F11** deliverable list (… + reference slash-command/skill integration).

- **`integrations/claude-skill/SKILL.md`** — a copy-pasteable agent skill that drives the agent
  surface: discover the schema (`tarseem schema`), author a spec, render (`tarseem generate`), and
  **self-repair** against the JSON contract (read each error's `path` JSON-Pointer + `hint`, fix,
  retry). Trigger-rich frontmatter description; worked self-repair example inline. Pointer added to
  `docs/guide/agents.md`.
- **Integration test** `tests/test_skill_integration.py` (4): frontmatter present; a **rot guard**
  asserting every `tarseem <sub>` the skill names is a real CLI subcommand (and that `schema` +
  `generate` are referenced); the prescribed flow rendered end-to-end through the real CLI; and the
  documented self-repair loop (invalid → coded error with path+hint → corrected → `ok`). ruff clean.

## Exercise #2 — timeline external plugin: custom layouter (2026-06-17)

**Second freeze-gate plugin exercise (F9), stressing a different axis than incident-flow.** With
both exercises passing, the v1.0 freeze (PR5) is now unblocked (R-26/R-29: two real plugins).

- `examples/plugins/timeline/` — its own distribution (`tarseem-timeline`) registering `timeline`
  on `tarseem.types`. It supplies a custom **`layouter_factory`** (`TimelineLayout`): a pure-Python
  single-axis layouter that consumes the measured `LogicalGraph` and returns a `PositionedDiagram`
  — replacing ELK entirely, the same contract swimlane/sequence satisfy, but from outside the core.
  Rendering inherited (generic renderer).
- **RTL-aware (invariant 4 holds for external layout):** `direction:"RL"` mirrors events
  right-to-left (geometry only); verified the first event lands rightmost.
- **Verified:** installed → discovered via entry points → LTR places events with strictly
  increasing x on a shared centre line → RTL mirrors → renders → works through `generate()` with
  `provenance.layoutEngine == "timeline"`.
- **CI** now installs both example plugins. **F9 guard** `test_engine_core_never_names_the_timeline_type`
  asserts `src/tarseem` never contains the string `timeline`. Tests:
  `tests/test_external_plugin_timeline.py` (5).
- **Two extension points now proven externally:** incident-flow (compile/`default_shape`) +
  timeline (layout/`layouter_factory`). The remaining declared plugin field not yet exercised by an
  external is `svg_renderer` (the built-in er/class/sequence use it); noted for PR5's audit.

## Resume checklist

1. Re-anchor: CLAUDE.md + `git log --oneline -8` + Phase 7 in `11-phased-plan.md` + `.venv` pytest.
2. A new family = a `DiagramTypePlugin` exposed on `tarseem.types`. Built-ins live in
   `tarseem/families/`; the registry (`get_plugin`/`all_plugins`) is the single dispatch authority.
3. PR2 is the F9 proof: build "incident-flow" as an **external** plugin (its own package/entry
   point) using only `docs/extending/clone-a-type.md` — no edits under `src/tarseem/`.
4. No phase ships with red CI; nothing reaches `main` without a PR; the v1.0 freeze (PR5) is gated
   on two passing plugin exercises (incident-flow + one more).
