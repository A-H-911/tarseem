# ADR-009 — Schema frozen at v1.0 (ratify as-built; require 1.x; profiles enforced)

Status: **Accepted** (2026-06-17) · Freezes FR-2 / `05-schema-strategy.md` · Phase 7 (F12)
Decision owner: project owner (explicit, 2026-06-17). Gated on two passing plugin exercises
(incident-flow + timeline) per R-26/R-29.

## Context

`05-schema-strategy.md` was written before implementation. Through Phases 2–6 the shipped schema
drifted from it: `diagramType` is **flat** (`swimlane`), not dotted profiles (`swimlane.process`);
`meta` is an open object, not a fixed `{id,title,description,…}`; ~15 keys were added (theme
corner controls; node `shape`/`badge`/`position`/`attributes`/`methods`; edge
`routing`/`priority`/`preferredDirection`/`dashed`; `layout.markers`/`mindmapStyle`/
`uniformNodeSize`/`laneOrientation`/`router`); the node `kind` field was never read; `$id` was
still `0.x`; and no migration tooling existed. F12 requires the schema frozen at v1.0 with
versioning + migration. The two-plugin extensibility guard (ADR-008, F9) is satisfied, so the
freeze is no longer premature.

## Decision

Four owner decisions (2026-06-17):

1. **Ratify as-built.** v1.0 is the schema that actually shipped — flat `diagramType`, open
   `meta`, and the Phase 2–6 keys promoted to officially documented. The doc's dotted-profile and
   structured-`meta` ideas are dropped (they would break every spec, example, plugin, and the
   registry for no user benefit). `$id` → `…/1.0/core.json`.
2. **Require 1.x.** The validator accepts `specVersion` matching `^1\.\d+$` only. A pre-1.0 spec
   raises a dedicated **`E_VERSION`** (with a `tarseem migrate` hint) rather than a cryptic pattern
   error. All committed specs (examples, tests, plugin examples, docs) were bumped to `"1.0"`.
3. **Drop the dead `kind`.** Removed from the node schema (confirmed unread — only `shape` is
   used). A stray `kind` now fails `additionalProperties` (`E_SCHEMA`); `migrate` strips it.
4. **Enforce per-family profiles.** Each plugin may declare a `schema_extension` (a JSON-Schema
   fragment) validated after the core; failures are **`E_PROFILE`** with the offending JSON-Pointer
   path. Implements the 05 §1 anti-generic guard: **swimlane requires `lanes`; sequence forbids
   `lanes`/`phases`.**

**Versioning policy** (per `05 §2`): the engine reads the current MAJOR (1.x; MINOR is additive).
`tarseem migrate` upgrades older specs — for v1.0 it sets `specVersion="1.0"` and strips `kind`.
`migrate_spec` is pure and idempotent.

## Consequences

**Gained:** a stable, documented, machine-checkable v1.0 contract. The published `schema_bundle()`
(2020-12, `diagramType` enum from the live registry) is the IDE/LLM authoring surface. Profiles
give families real guardrails. Migration gives a forward path.

**Breaking (intended):** pre-1.0 (`0.x`) specs no longer validate — they must be migrated. A
swimlane without `lanes`, or a sequence carrying `lanes`/`phases`, is now an error (none existed in
the corpus). `kind` is no longer accepted.

**Costs / deferred:** typed profiles are enforced via plugin `schema_extension` but profile
*composition by `$ref`* (the doc's full vision) is the simple-fragment form, not a resolver — richer
profile schemas are additive post-1.0. Dotted `diagramType` namespacing is not adopted.

**Unchanged:** invariants 1–8 hold. No renderer/layout/writer behavior changed — visual-regression
and determinism baselines are byte-identical (the version bump alters only provenance/`specHash`,
which lives outside the compared pixels and canonical SVG geometry). Supersedes the unimplemented
parts of `05-schema-strategy.md` §1–§3 (annotated there).
