# ADR-008 — Diagram types are entry-point plugins (built-ins dogfood the public API)

Status: **Accepted** (2026-06-17) · Realises invariant 8 · Phase 7 (Extensibility)
Decision owner: project owner (explicit, 2026-06-17). Builds on ADR-002 (layout adapters).

## Context

Invariant 8 (CLAUDE.md) states: *"diagram types are plugins (schema extension + compiler +
layout/render profiles) registered via entry points. Built-ins use the same mechanism."*
Through Phases 2–6 this was deferred: the 10 built-in families were dispatched by **hardcoded
`diagramType` comparisons** scattered across the pipeline —

- `model/compile.py`: a `_DEFAULT_SHAPE` dict + an `is_class` check;
- `engine.py`: `_SWIMLANE_TYPES` / `_SEQUENCE_TYPES` sets choosing the layouter;
- `render/svg.py`: an if/elif on `diagram_type` choosing the renderer;
- `export/drawio.py`, `export/pptx.py`: `== "sequence"` chrome checks;
- `export/metadata.py`: `diagram_type` → layout-engine provenance label.

`pyproject.toml` already reserved an empty `[project.entry-points."tarseem.types"]` group with
the note *"dogfood the public plugin API"*. Acceptance criterion **F9** requires a new diagram
type to be added via plugin **without core changes**, proven twice (incl. the clone tutorial).
The hardcoded dispatch made that impossible: a new family required editing ≥3 core files.

The owner chose (2026-06-17) the **full entry-point dogfood** over a lighter "built-ins register
in-process" variant: built-ins must load through the identical entry-point mechanism third
parties use, so the public API is exercised by the engine's own families on every run.

## Decision

A diagram family is a declarative **`DiagramTypePlugin`** (`tarseem/families/base.py`): a frozen
dataclass describing the family's `default_shape`, `member_compartments`, `layouter_factory`
(`None` ⇒ ELK), `svg_renderer` (`None` ⇒ generic), `export_chrome`, `layout_engine_name`, and an
optional `schema_extension`. No subclassing; cloning a family is a few lines of data.

A single **registry** (`tarseem/families/__init__.py`) discovers plugins via the
`tarseem.types` entry-point group. The 10 built-ins are declared there in `pyproject.toml`
exactly like an external plugin would be, e.g. `flowchart = "tarseem.families.flowchart:PLUGIN"`.
Every pipeline stage resolves a `diagramType` through `get_plugin(type_id)` — the hardcoded
dicts/sets/if-else chains above are gone. Authors import the contract from the friendly public
alias `tarseem.plugins`.

Two checks that read **structural IR features** (not the type string) are deliberately **kept**
as-is: swimlane band chrome keyed off `diagram.lanes` (ADR-007), and ER rows / class members /
state pseudostates keyed off `node.rows` / `node.members` / `node.shape`. These are properties of
the positioned IR, not family routing.

A **bundled-module fallback** (`pkgutil` scan of `tarseem/families/`) `setdefault`-registers any
built-in missing from the entry-point metadata, so an editable checkout whose `*.dist-info`
predates a new declaration still works. Entry-point plugins always win. Unknown `diagramType`
strings resolve to a default plugin (generic renderer + ELK + `rect`) — preserving the pre-registry
behavior where a typo rendered as a generic graph rather than crashing.

## Consequences

**Gained:** a third party adds a diagram type with **zero core edits** — declare a
`DiagramTypePlugin`, expose it on `tarseem.types`. The engine's own families prove the path
(F9). Family behavior is now described in one place per family, not smeared across six modules.

**Behavior-preserving:** the refactor is pure dispatch indirection. The full suite — including the
determinism and 3-OS visual-regression baselines — stays **byte-identical** (verified green at
landing); no `examples/` golden changed, no baseline regen.

**Costs / ceilings:**
- The ELK adapter still selects the `mrtree`/`radial` algorithm for mindmaps by `diagram_type`
  internally (`layout/elk/__init__.py`). This is an ELK-internal detail, not family routing, and
  does **not** block an external clone (which reuses ELK-layered + the generic renderer). Exposing
  custom ELK options through the plugin is a future extension, not required for F9.
- `EDGE_WIDTH_DEFAULT` (a per-family styling table in `geometry.py`) is left as a shared constant;
  it is styling data, not dispatch. May migrate onto the plugin later.
- `schema_extension` is part of the contract but not yet enforced by validation (the core accepts
  any registered `diagramType`); typed-profile composition (05 §1) lands with the schema-freeze work.

**Unchanged:** invariants 1–7 hold. ADR-007 (drawio swimlane cells) and the shared `geometry.py`
are untouched.
