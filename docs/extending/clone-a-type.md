# Clone a diagram type (extend Tarseem without touching the core)

Tarseem diagram types are **plugins**. A new family is a small `DiagramTypePlugin` descriptor
exposed on the `tarseem.types` entry-point group — the *same* mechanism the built-in families use
(ADR-008). Nothing in the engine hard-codes a family name; every stage resolves the `diagramType`
through the registry. So you can add a type from your own package with **no edits to
`src/tarseem`** (acceptance criterion F9).

This guide clones the built-in `flowchart` into a new `incident-flow` type for incident-response
runbooks. The finished, installable result lives at
[`examples/plugins/incident-flow/`](../../examples/plugins/incident-flow/) — the benchmark is
"build it in well under a day."

## 1. The contract

`tarseem.plugins.DiagramTypePlugin` (frozen dataclass) describes one family. Every field except
`type_id` is optional — omit a field to inherit the default:

| Field | Default | Drives | Stage |
|---|---|---|---|
| `type_id` | — (required) | the `diagramType` string this plugin claims | all |
| `default_shape` | `"rect"` | node shape when a node omits `shape` | compile |
| `member_compartments` | `False` | read `attributes`/`methods` as UML compartments (vs ER rows) | compile |
| `layouter_factory` | `None` ⇒ **ELK** | a zero-arg factory → one-shot `.layout(graph)` (e.g. lane-grid) | layout |
| `svg_renderer` | `None` ⇒ **generic** | a `(PositionedDiagram) -> str` renderer | render |
| `export_chrome` | `None` | extra drawio/PPTX chrome (`"sequence"` ⇒ lifelines) | export |
| `layout_engine_name` | `"elk"` | provenance label for the layout stage | metadata |
| `schema_extension` | `None` | reserved: a JSON-Schema fragment a typed profile adds | validate |

The defaults *are* the flowchart pipeline: ELK layered layout + the generic graph renderer. So a
clone that only changes cosmetics is a few lines.

## 2. Write the plugin

A new package — call it `tarseem_incident_flow` — with one module:

```python
# tarseem_incident_flow/__init__.py
from tarseem.plugins import DiagramTypePlugin

PLUGIN = DiagramTypePlugin(
    type_id="incident-flow",
    default_shape="stadium",   # incident states as terminators; everything else inherited
)
```

That is the whole behavioral change: incident states default to stadium shapes instead of the
flowchart's rounded rectangles. Authors who need more — a bespoke layouter or renderer — supply
`layouter_factory` / `svg_renderer` callables here; the built-in `swimlane` and `sequence`
families are exactly this pattern.

## 3. Register it via an entry point

The registry discovers plugins from the `tarseem.types` entry-point group. Declare yours in the
package's `pyproject.toml`:

```toml
[project]
name = "tarseem-incident-flow"
dependencies = ["tarseem"]

[project.entry-points."tarseem.types"]
incident-flow = "tarseem_incident_flow:PLUGIN"

[tool.hatch.build.targets.wheel]
packages = ["tarseem_incident_flow"]
```

Install it (editable while developing):

```bash
pip install -e .          # inside your plugin package
```

> **Editable-install note.** Entry points are baked into a distribution's metadata at install
> time. After adding or changing an entry point you must re-run `pip install -e .` so the
> `*.dist-info/entry_points.txt` is refreshed; otherwise the registry won't see the change.

## 4. Author a spec and render

Your type is now first-class — it validates, compiles, lays out via ELK, renders to SVG/PNG/PDF,
and exports to draw.io/PPTX through the same pipeline as the built-ins:

```jsonc
{
  "specVersion": "1.0",
  "diagramType": "incident-flow",
  "meta": { "title": "Incident Response" },
  "nodes": [
    { "id": "detect", "label": { "text": "Detect" } },
    { "id": "triage", "shape": "diamond", "label": { "text": "Sev 1?" } },
    { "id": "mitigate", "label": { "text": "Mitigate" } }
  ],
  "edges": [
    { "id": "e1", "source": "detect", "target": "triage" },
    { "id": "e2", "source": "triage", "target": "mitigate", "label": { "text": "no" } }
  ]
}
```

```bash
tarseem render incident.json -o incident.svg     # CLI
```

```python
from tarseem import Engine                        # Python API
Engine().render(spec).export(["svg", "png"], "out/")
```

`detect` (no explicit `shape`) renders as a stadium — proof the registry consulted *your*
plugin's `default_shape`, not the engine's `rect` fallback.

## 5. Verify the "no core edits" property

The contract is that the engine never learned the string `"incident-flow"`. You can prove it:

```bash
grep -r "incident-flow" src/tarseem/      # no matches — the core is untouched
```

An unregistered `diagramType` (a typo, or a plugin you forgot to install) does not crash: it
falls back to a generic ELK graph. Install the plugin and the same spec renders as your type.

## What you did not have to touch

No edits to the schema, compiler, layout dispatcher, SVG renderer, draw.io/PPTX writers, or the
CLI. The plugin descriptor + one entry-point line is the entire surface. That is the extension
model invariant 8 promises — and the engine's own ten families prove it by loading through this
exact mechanism.

## Going further

- **Custom layout/render:** pass `layouter_factory` / `svg_renderer` callables (see
  `tarseem/families/swimlane.py`, `sequence.py`).
- **Typed validation:** `schema_extension` is reserved for JSON-Schema profile composition
  (05 §1); today the core accepts any registered `diagramType`.
- **Agent use:** a registered type is renderable through the agent surface (`generate(spec)`) and
  appears in the published schema bundle — see the agent-readiness docs.
