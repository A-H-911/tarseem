# Agent & tool integration

Tarseem exposes a single function built for programmatic and LLM use: `generate(spec)`. It takes
a spec dict, returns a JSON-serializable payload, and **never raises for a bad spec** — invalid
input comes back as coded, path-precise errors an agent can repair against.

## `generate(spec, formats=("svg",), out_dir=None, name="diagram")`

```python
from tarseem import generate

out = generate(spec)                       # default: inline SVG, no files, no browser
if out["ok"]:
    svg = out["svg"]                       # the canonical diagram, inline
    metrics = out["report"]                # node/edge counts, crossings, overlaps, size
else:
    for e in out["errors"]:
        print(e["code"], e["path"], e["message"], "->", e["hint"])
```

### Success payload

| Key | Meaning |
|---|---|
| `ok` | `true` |
| `diagramType` | the resolved family |
| `svg` | canonical SVG, inline (always present) |
| `artifacts` | `{format: path}` for files written when `out_dir` is given |
| `report` | geometry metrics: `node_count`, `edge_count`, `crossings`, `overlaps`, `width`, `height`, `render_ms` |
| `capabilities` | per-format `CapabilityReport` (what each writer carried / dropped — invariant 6) |
| `warnings` | non-fatal validation warnings (coded) |
| `provenance` | content-addressed: spec hash, engine versions, theme, layout engine |
| `versions` | engine + elkjs versions |

### Error payload (the contract agents repair against)

```jsonc
{
  "ok": false,
  "errors": [
    { "code": "E_SCHEMA", "path": "/nodes/2/label", "message": "...", "hint": "...", "severity": "error" }
  ],
  "warnings": []
}
```

`{code, path, message, hint}` is the stable contract (05 §5). `path` is a JSON Pointer into the
spec, so an agent can locate and fix the offending element directly.

## SVG by default; files need a directory

SVG is pure Python and is returned inline — the common "give me the diagram" call needs no
filesystem and no browser. PNG/PDF/draw.io/PPTX are written to disk, so they require `out_dir`:

```python
out = generate(spec, formats=["svg", "png", "drawio"], out_dir="build/")
# out["artifacts"] == {"svg": "build/diagram.svg", "png": "build/diagram.png", "drawio": "build/diagram.drawio"}
```

### Async-safety: raster is subprocessed for you

PNG/PDF rendering uses a process-wide **sync** Chromium pool that cannot start inside a running
asyncio event loop. So whenever a raster format is requested, `generate` runs the whole export in
a fresh subprocess — you can call it from a sync script or from inside an async agent framework
without the "sync API inside asyncio loop" error. draw.io/PPTX are pure-Python and run in-process.

## Schema bundle for tool-use

`schema_bundle()` returns a JSON Schema (2020-12) describing a valid spec, with `diagramType`
enumerated from the **currently registered** families (built-ins + installed plugins). Use it as
an LLM tool's input schema, or as an editor `$schema` for autocomplete:

```python
from tarseem import schema_bundle
tool_input_schema = schema_bundle()
```

## CLI faces

Everything above is on the CLI too, for shell/agent harnesses:

```bash
tarseem generate spec.json -f svg,png -o build/   # -> JSON payload on stdout (exit 1 if !ok)
tarseem schema -o tarseem.schema.json             # -> the JSON-Schema bundle
```

## Extending what agents can draw

A new diagram type registered as a plugin (see [`../extending/clone-a-type.md`](../extending/clone-a-type.md))
is immediately available through `generate` and appears in `schema_bundle()` — no change to the
agent surface.
