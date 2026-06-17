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
| 2 | **incident-flow plugin + clone tutorial** — build an external "incident-flow" family from flowchart using ONLY the docs (plugin exercise #1, F9 benchmark "<1 day"); `docs/extending/clone-a-type.md` | ⏳ next (PR2) | — |
| 3 | **Agent surface** — single `generate(spec) -> artifacts + report`; JSON error contract `{code,path,message,hint}` (already in `errors.Issue`); published schema bundle for LLM tool-use; SVG-default + subprocess guard for the Chromium pool | ⏳ (PR3) | — |
| 4 | **Reference slash-command / skill integration** (F11) | ⏳ (PR4) | — |
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

## Resume checklist

1. Re-anchor: CLAUDE.md + `git log --oneline -8` + Phase 7 in `11-phased-plan.md` + `.venv` pytest.
2. A new family = a `DiagramTypePlugin` exposed on `tarseem.types`. Built-ins live in
   `tarseem/families/`; the registry (`get_plugin`/`all_plugins`) is the single dispatch authority.
3. PR2 is the F9 proof: build "incident-flow" as an **external** plugin (its own package/entry
   point) using only `docs/extending/clone-a-type.md` — no edits under `src/tarseem/`.
4. No phase ships with red CI; nothing reaches `main` without a PR; the v1.0 freeze (PR5) is gated
   on two passing plugin exercises (incident-flow + one more).
