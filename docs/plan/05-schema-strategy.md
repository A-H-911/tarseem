# JSON Schema Strategy

Status: Proposed · 2026-06-11 · **§1–§3 frozen as-built at v1.0 by [ADR-009](../adr/ADR-009-schema-v1-freeze.md) (2026-06-17).**
Resolves FR-2 and risk R-26 (too-generic vs. too-rigid tension).

> **Superseded where it differs from what shipped (ADR-009).** This doc was written pre-build; the
> v1.0 freeze ratifies the as-built schema. Differences from the §3 sketch below: `diagramType` is
> **flat** (`swimlane`), not dotted (`swimlane.process`); `meta` is an open object; the node `kind`
> field was dropped (unread); `specVersion` must be `1.x`. The §1 model (small core + profiles +
> extensions), §2 versioning/migration, §4 validation layers, and §5 agent ergonomics all hold —
> profiles are enforced via each plugin's `schema_extension` (ADR-008/009), and migration ships as
> `tarseem migrate`. Treat ADR-009 + `schema/core.py` as authoritative over the §3 example.

---

## 1. Model: small stable core + typed profiles + namespaced extensions

- **Core** defines the universal graph vocabulary every diagram family shares: nodes, edges, containers, lanes, ports, labels, styles, themes, layout/routing hints, export options, metadata. Core is deliberately small and changes slowly.
- **Diagram profiles** (`diagramType`) constrain and extend the core per family (e.g., `sequence` adds `participants/messages` sugar that compiles to nodes/edges; `c4` adds `elementKind: system|container|component|person`). Profiles live in plugin packages, validated via `$ref` composition — never forked formats (FR-2.6).
- **Extension escape hatch**: any object may carry `x-*` vendor keys (preserved, ignored by core) and `ext: {namespace: {...}}` for typed extensions registered by plugins.
- Anti-generic guard: profiles may *require* fields and *forbid* core features they can't render (validated), so a `sequence` spec can't silently contain lanes.

## 2. Versioning

- `specVersion: "1.0"` (semver, required). JSON Schema dialect: **2020-12**.
- `$id`: `https://<org>/schemas/diagram/<version>/core.json` (+ per-profile ids).
- Compatibility policy: MINOR = additive only; MAJOR = migrations shipped (`engine migrate spec.json`); engine supports current MAJOR and reads previous MAJOR. Pre-1.0 (`0.x`) explicitly unstable during Phases 2–6.
- Outputs embed `specVersion` + spec hash + engine/elkjs/Chromium versions (NFR-6).

## 3. Top-Level Shape (illustrative)

```jsonc
{
  "specVersion": "1.0",
  "diagramType": "swimlane.process",        // registry key → profile plugin
  "meta": { "id": "order-flow", "title": {"text": "معالجة الطلب", "lang": "ar"},
            "description": "...", "tags": ["sales"], "authors": [] },
  "theme": { "ref": "corporate-rtl", "overrides": { "palette.primary": "#0B5FA5" } },
  "direction": "RL",                         // LR|RL|TB|BT — layout mirroring (FR-4.3)
  "styles": {                                // reusable presets (FR-5.3)
    "critical": { "fill": "#FDECEC", "border": {"color": "#C0392B", "width": 2, "style": "dashed"} }
  },
  "lanes": [                                 // first-class (not generic groups)
    { "id": "sales", "label": {"text": "المبيعات"}, "orientation": "horizontal",
      "style": {"fill": "#F4F8FB"}, "order": 1 }
  ],
  "phases": [ { "id": "ph1", "label": {"text": "التقديم"}, "order": 1 } ],
  "nodes": [
    { "id": "n1", "kind": "process", "lane": "sales", "phase": "ph1",
      "label": {"text": "استلام الطلب"}, "styleRefs": ["critical"],
      "size": {"minWidth": 140}, "ports": [{"id": "out", "side": "EAST"}],
      "ext": {}, "x-team": "crm" }
  ],
  "groups": [ { "id": "g1", "label": {"text": "..."}, "children": ["n1"], "collapsible": false } ],
  "edges": [
    { "id": "e1", "source": "n1", "sourcePort": "out", "target": "n2",
      "label": {"text": "مقبول", "placement": "center"},
      "routing": {"mode": "orthogonal", "priority": 5, "waypoints": [], "preferDirection": "EAST"},
      "arrow": {"target": "filled"}, "style": {} }
  ],
  "annotations": [ { "id": "note1", "kind": "note", "attachTo": "n1", "label": {"text": "..."} } ],
  "layout": { "engine": "elk", "options": {"spacing.nodeNode": 40}, "respectManualPositions": true },
  "export": { "targets": ["svg", "png", "drawio"], "svg": {"embedFonts": true, "textAsPaths": false},
              "png": {"scale": 2} }
}
```

Notes:
- **Labels are objects**, never bare strings: `{text, lang, direction(auto|ltr|rtl), font?, wrap?, maxWidth?}` — the hook for all RTL behavior (FR-4).
- **Lanes and phases are first-class** core concepts (the brief's flagship feature must not be an afterthought bolted onto groups).
- **Ports** optional; sides use ELK compass (`NORTH|SOUTH|EAST|WEST` + fixed offsets).
- **Routing hints** map 1:1 to capabilities adapters declare; unsupported hints ⇒ capability report, not silent drop.
- **Style cascade** (FR-5.2): theme → diagram `styles`+`theme.overrides` → group → lane → node/edge → label; resolution happens in the engine, so resolved styles are backend-neutral (FR-5.4).

## 4. Validation Pipeline (Layer 2)

1. **Structural**: JSON Schema validation (core + profile), precise JSON-Pointer errors.
2. **Referential**: ids unique; edge endpoints/lane refs/port refs/styleRefs resolve; group membership acyclic.
3. **Semantic lint** (warnings vs errors): orphan nodes, label overflow vs `minWidth`, RTL text in LTR-only export target, conflicting hints, unknown `x-*` (info).
4. **Capability check**: spec features ∩ chosen adapter capabilities; failures list feature, element path, and nearest supported alternative — designed for agent self-repair (R-28).

## 5. Authoring & Agent Ergonomics

- Published schema bundle → IDE autocomplete (`$schema` URL) and direct use as LLM tool-schema.
- Error objects: `{code, path, message, hint}` — machine-actionable (NFR-5).
- `engine examples <type>` emits minimal + full golden specs (also the doc fixtures).
- Defaults philosophy: a 5-line spec must render decently (theme defaults, auto layout, auto sizing); every default overridable.

## 6. Why not reuse an existing format?

Evaluated and rejected as the *authoring* schema: ELK JSON (geometry-only, no styling/semantics — used internally as the layout wire format), mxGraph XML (style-string strings, undocumented), BPMN DI (process-only, heavy), Mermaid/PlantUML DSLs (not JSON, lossy). The unified schema *compiles to* these; it must not *be* any of them. This keeps the IR stable while backends evolve (FR-1.2).
