# Documentation Plan

Status: Proposed · 2026-06-11 · Tooling: mkdocs-material (proposed), schema reference auto-generated from JSON Schema, examples pulled from the gallery corpus (single source of truth — no drifting snippets).

---

## Structure

```
docs/
├─ index.md                      # purpose, positioning, quickstart (5-line spec → SVG)
├─ concepts/
│  ├─ architecture.md            # layer model, pipeline diagram, adapter boundaries
│  ├─ design-decisions/          # ADRs (numbered, immutable): ADR-001 compile-not-transpile,
│  │                             # ADR-002 ELK primary, ADR-003 own SVG renderer,
│  │                             # ADR-004 Playwright canonical raster, ADR-005 editable=writers, …
│  └─ output-roles.md            # publish / refine / regenerate / verify
├─ schema/
│  ├─ overview.md                # core + profiles + extensions model
│  ├─ reference/                 # GENERATED per-object field docs
│  ├─ versioning.md              # compat policy, migration guide
│  └─ authoring-guide.md         # human + AI-agent authoring, error-code catalog
├─ diagram-types/<type>.md       # per family: capabilities, profile fields, examples, limitations
├─ styling/
│  ├─ themes.md                  # cascade, presets, portability rules
│  └─ fonts.md                   # bundled fonts, embedding, fallback chain
├─ rtl-arabic.md                 # the full strategy as user guide + troubleshooting
├─ exports/
│  ├─ overview.md                # tier table, fidelity matrix
│  ├─ editable-outputs.md        # drawio + pptx workflows incl. PowerPoint steps
│  └─ source-exports.md          # lossiness contracts
├─ gallery.md                    # building/serving, adding samples
├─ extending/
│  ├─ new-diagram-type.md        # plugin walkthrough (clone-a-type tutorial)
│  ├─ new-adapter.md             # layout/render/export adapter contracts
│  └─ agent-integration.md       # slash-command/skill patterns, tool-schema usage (P7)
├─ testing.md                    # running suites, baseline regeneration policy
├─ operations/
│  ├─ installation.md            # per-OS, extras, doctor, offline/CI installs
│  └─ troubleshooting.md         # font issues, Node/Playwright issues, known limits
├─ limitations.md                # honest list: nested lanes, avoid-zones, export ceilings (R-13/16/19)
└─ roadmap.md                    # phase status vs 11-phased-plan.md
```

Audience mapping: developers → concepts/extending/testing; architects → index/concepts/limitations; AI agents → schema/authoring-guide + error catalog + machine-readable schema bundle; maintainers → ADRs/testing/operations; spec authors → schema/diagram-types/styling/rtl.

Doc quality gates: every merged feature updates its page (CI link-check + example-render check); ADR required for any backend or schema-core change.
