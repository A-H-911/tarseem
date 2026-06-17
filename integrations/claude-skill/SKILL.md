---
name: tarseem-diagram
description: Generate architecture-grade diagrams (flowchart, swimlane/process, sequence, architecture/C4, ER, class, state, deployment, dependency, mind map — LTR or RTL/Arabic) by authoring a Tarseem JSON spec and rendering it with the `tarseem` CLI. Use when asked to draw, build, render, or export a diagram to SVG/PNG/PDF/draw.io/PPTX, or to turn a described process/architecture into a picture.
---

# Tarseem diagram skill

A reference integration of the Tarseem **agent surface** (`tarseem generate` / `tarseem schema`).
It turns a diagram request into a validated JSON spec, renders it, and reads back a machine
contract you can self-repair against. Tarseem must be installed (`pip install -e .` from its repo,
or `pip install tarseem`); verify with `tarseem doctor`.

## Workflow

1. **Learn the schema.** Run `tarseem schema`. It returns a JSON Schema (2020-12); the
   `properties.diagramType.enum` lists every diagram family currently available (built-ins +
   installed plugins). Pick the family that fits the request.

2. **Author a spec** (JSON) against that schema. Essentials:
   - `specVersion` (e.g. `"0.1"`) and `diagramType` are required.
   - **Labels are objects, never bare strings:** `{"text": "Place order"}`; add `"lang": "ar"`
     for Arabic. Set top-level `"direction": "RL"` for right-to-left/Arabic layouts.
   - `nodes` have `id` + `label` (+ optional `shape`); `edges` have `source` + `target`
     (+ optional `label`). Swimlanes add `lanes` (and nodes carry `lane`); sequence/ER/class have
     their own sugar — see `tarseem examples` and the `examples/` corpus.

3. **Render.** Default to SVG (no browser needed):
   ```bash
   tarseem generate spec.json                        # JSON payload; "svg" is inline
   tarseem generate spec.json -f svg,png -o out/      # also write files (raster needs -o)
   ```

4. **Read the result** (JSON on stdout). On success: `ok: true`, with inline `svg`, written
   `artifacts`, a geometry `report`, and per-format `capabilities` (what each export carried).
   On failure: `ok: false` with `errors`, each `{code, path, message, hint}` — **`path` is a JSON
   Pointer into your spec**. Fix the element at `path` as the `hint` says and re-run. Repeat until
   `ok: true`. (`warnings` are non-fatal — surface them but don't block.)

5. **Deliver** the artifact path(s) from `artifacts`, or the inline `svg`.

## Self-repair example

Request "swimlane: Sales places an order, Warehouse ships it." First spec omits `specVersion`:

```json
{ "diagramType": "swimlane", "lanes": [{"id":"s","label":{"text":"Sales"}}], "nodes": [], "edges": [] }
```

`tarseem generate` returns:

```json
{ "ok": false, "errors": [
  { "code": "E_SCHEMA", "path": "/", "message": "'specVersion' is a required property",
    "hint": "add specVersion, e.g. \"0.1\"" } ] }
```

Add `"specVersion": "0.1"`, flesh out nodes/edges, re-run → `{ "ok": true, "svg": "<svg …>", … }`.

## Tips

- Start minimal — a 5-line spec renders with sensible theme/layout defaults — then refine.
- Need a diagram type that isn't in the enum? It can be added as a plugin without changing the
  engine; see `docs/extending/clone-a-type.md`.
- For editable hand-off, export `drawio` (diagrams.net) or `pptx` (PowerPoint): `-f drawio,pptx -o out/`.
