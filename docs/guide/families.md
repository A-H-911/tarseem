# Diagram families

The MVP supports four diagram families plus sequence. Every family ships a golden example in
`examples/` and a rendered page in the gallery — these double as the documentation fixtures
(A9). Each family is selected by the spec's `diagramType`.

| Family | `diagramType` | Layouter | Node needed | Example |
|---|---|---|---|---|
| Flowchart | `flowchart` | ELK | yes | `examples/flowchart.json` |
| Architecture / C4 | `architecture` | ELK | yes | `examples/architecture.json` |
| Dependency | `dependency` | ELK | yes | `examples/dependency.json` |
| Swimlane | `swimlane` | lane-grid (pure Python) | no | `examples/swimlane-bug-triage.json`, `swimlane-pipeline.json`, `swimlane-phases.json`, `swimlane-vertical-release.json`, `swimlane-nested-delivery.json` |
| Sequence | `sequence` | sequence (pure Python) | no | `examples/sequence-login.json` |
| State | `state` | ELK | yes | `examples/state-order-lifecycle.json` |
| Deployment | `deployment` | ELK | yes | `examples/deployment-web-stack.json` |
| ER | `er` | ELK + per-row ports | yes | `examples/er-shop.json` |

All families share the same spec vocabulary (`nodes` / `edges` / `label` / `style` …) and the
same positioned IR; only the layouter and a few family-specific fields differ.

## Flowchart / Architecture / Dependency (graph families)

Nodes and edges laid out by ELK. `direction` controls flow (`TB`/`BT`/`LR`/`RL`). Shapes are
set per node (`stadium`, `roundrect`, `diamond`, `cylinder`, `parallelogram`, `document`,
`rect`); edges support `label` and `dashed`.

```json
{
  "specVersion": "0.1",
  "diagramType": "flowchart",
  "direction": "TB",
  "nodes": [
    {"id": "start", "shape": "stadium", "label": {"text": "Start"}},
    {"id": "check", "shape": "diamond", "label": {"text": "OK?"}}
  ],
  "edges": [{"source": "start", "target": "check", "label": {"text": "go"}}]
}
```

Architecture/C4 and dependency use the same shape — they differ in conventions and styling
(named style presets via `styles` + `styleRefs`), not in mechanics.

## Swimlane

Horizontal lanes with a title bar, header pills, per-lane hue tints, and auto-number badges.
Built by the pure-Python lane-grid layouter (one step per column = its topological number;
lanes are fixed rows), not ELK — ELK partitioning groups along the flow axis, not lanes.

Key fields: top-level `lanes`, each node's `lane`; `badge: false` exempts a node (start/
terminal) from numbering; `layout.markers: true` adds UML start/end markers.

```json
{
  "specVersion": "0.1", "diagramType": "swimlane", "direction": "LR",
  "meta": {"title": "Bug Triage"},
  "lanes": [{"id": "rep", "label": {"text": "Reporter"}},
            {"id": "tri", "label": {"text": "Triage"}}],
  "nodes": [
    {"id": "report", "lane": "rep", "shape": "stadium", "badge": false, "label": {"text": "Bug report"}},
    {"id": "classify", "lane": "tri", "shape": "roundrect", "label": {"text": "Classify"}}
  ],
  "edges": [{"source": "report", "target": "classify"}]
}
```

### Phase columns (FR-6.3)

Declare top-level `phases` and set each node's `phase` to group flow columns under a header
band (with a separator dropping through the lanes). See `examples/swimlane-phases.json`.

### Vertical lanes (FR-6.1)

Set `layout.laneOrientation: "vertical"` to lay lanes out as **columns** with flow running
top-to-bottom (instead of the default horizontal rows). The title bar stays on top and the
lane header pills move to the top of each column. The vertical variant is a deterministic
coordinate transpose of the horizontal layout, so topological ordering and obstacle-avoiding
routing carry over unchanged. See `examples/swimlane-vertical-release.json`.

Documented limitations (AM-6) of the vertical variant:

- **Node boxes are portrait-oriented** — a wide step becomes a tall one (the transpose swaps
  width and height). Best suited to short labels; long labels may need a wider lane.
- **Phase columns are not drawn** in vertical orientation; `phases` are ignored when
  `laneOrientation` is `"vertical"`.
- Only top-to-bottom flow is supported (no vertical RTL / bottom-to-top mirroring yet).

### Nested lanes (best-effort, AM-6)

Give a lane a `parent` (the id of another lane) to nest it inside a group. The parent lane
becomes an **outer header gutter** spanning its children; the children are the actual flow
rows. See `examples/swimlane-nested-delivery.json`.

```json
"lanes": [
  {"id": "eng", "label": {"text": "Engineering"}},
  {"id": "fe", "label": {"text": "Frontend"}, "parent": "eng"},
  {"id": "be", "label": {"text": "Backend"}, "parent": "eng"},
  {"id": "qa", "label": {"text": "QA"}}
]
```

Documented limitations (AM-6) of nested lanes:

- **One level only.** A parent's children must be leaf lanes; deeper nesting is not drawn.
- **Nodes attach to leaf lanes**, never to a parent group.
- Nesting is **horizontal-only** — it is ignored when `laneOrientation` is `"vertical"`.

### Layout options

Swimlane spacing and the phase-separator look are tunable per diagram under `layout` (all
optional; defaults equal the built-in constants, so omitting them changes nothing):

| Option | Type | Default | Effect |
|---|---|---|---|
| `sidePadding` | number | 24 | symmetric gap between the actor separator and the first shape, and between the last shape and the lane border |
| `columnGap` | number | 56 | horizontal gap between step columns |
| `phaseSeparator.style` | `"dashed"` \| `"solid"` | `"dashed"` | phase separator line style |
| `phaseSeparator.color` | string | `#B0BEC5` | phase separator colour |
| `phaseSeparator.width` | number | 1.5 | phase separator stroke width |
| `markers` | boolean | false | UML start/end markers |
| `laneOrientation` | `"horizontal"` \| `"vertical"` | `"horizontal"` | lane axis: rows (flow L→R) or columns (flow top→bottom) — see [Vertical lanes](#vertical-lanes-fr-61) |

```json
{
  "layout": {
    "sidePadding": 32,
    "columnGap": 72,
    "phaseSeparator": { "style": "solid", "color": "#90A4AE", "width": 2 }
  }
}
```

See `examples/swimlane-tuned.json`.

## Sequence

Participants are lifelines (ordered columns), messages are time-ordered rows, activation bars
fall out of call/return nesting, and a message whose `source == target` renders as a
self-message bracket. Built by the pure-Python deterministic sequence layouter.

Convention: participants are `nodes` (in left-to-right order), messages are `edges` (in time
order); a `dashed: true` edge is a **return** (open arrowhead), a solid edge is a sync call
(filled arrowhead) that opens an activation on its target.

```json
{
  "specVersion": "0.1", "diagramType": "sequence", "meta": {"title": "Login"},
  "nodes": [{"id": "ui", "label": {"text": "Browser"}},
            {"id": "api", "label": {"text": "API"}}],
  "edges": [
    {"id": "m1", "source": "ui", "target": "api", "label": {"text": "POST /login"}},
    {"id": "m2", "source": "api", "target": "ui", "label": {"text": "200"}, "dashed": true}
  ]
}
```

## State

A UML-style state machine, laid out by ELK. States are rounded boxes; transitions are
labelled edges. Two pseudostate marker shapes are available:

- `shape: "initial"` — the start pseudostate (a solid filled dot, fixed size, empty label).
- `shape: "final"` — the end pseudostate (a ring around a filled dot).

```json
{
  "specVersion": "0.1", "diagramType": "state", "direction": "LR",
  "nodes": [{"id": "start", "shape": "initial", "label": {"text": ""}},
            {"id": "pending", "label": {"text": "Pending"}},
            {"id": "done", "shape": "final", "label": {"text": ""}}],
  "edges": [{"id": "e1", "source": "start", "target": "pending"},
            {"id": "e2", "source": "pending", "target": "done", "label": {"text": "finish"}}]
}
```

See `examples/state-order-lifecycle.json`.

## Deployment

An infrastructure / deployment topology, laid out by ELK. Nodes default to `shape: "cube"`
(a 3D box for devices, hosts, or containers); datastores read well as `cylinder`, and any
other shape from the graph set is available. Edges are communication paths.

```json
{
  "specVersion": "0.1", "diagramType": "deployment", "direction": "TB",
  "nodes": [{"id": "lb", "label": {"text": "Load Balancer"}},
            {"id": "db", "shape": "cylinder", "label": {"text": "PostgreSQL"}}],
  "edges": [{"id": "e1", "source": "lb", "target": "db"}]
}
```

See `examples/deployment-web-stack.json`.

## ER (entity-relationship)

Each entity is a node with an `attributes` array; it renders as a **table** — a title row
plus one row per attribute, with an optional `key` of `"PK"` or `"FK"` shown as a tag.
Relationships are `edges`; set `sourcePort` / `targetPort` to an attribute `id` to anchor the
connector to that exact row (typically an FK row pointing at the referenced PK row). Entities
are placed by ELK; the per-row connectors attach on the facing sides.

```json
{
  "specVersion": "0.1", "diagramType": "er", "direction": "LR",
  "nodes": [
    {"id": "customer", "label": {"text": "Customer"}, "attributes": [
      {"id": "id", "label": {"text": "id"}, "key": "PK"},
      {"id": "email", "label": {"text": "email"}}]},
    {"id": "order", "label": {"text": "Order"}, "attributes": [
      {"id": "id", "label": {"text": "id"}, "key": "PK"},
      {"id": "customer_id", "label": {"text": "customer_id"}, "key": "FK"}]}
  ],
  "edges": [{"id": "r1", "source": "order", "target": "customer",
             "sourcePort": "customer_id", "targetPort": "id", "label": {"text": "N:1"}}]
}
```

Cardinality is conveyed with the edge `label` (e.g. `"N:1"`). See `examples/er-shop.json`.

## Capability reports, never silent drops

Unsupported spec features produce machine-readable warnings in the validation/capability
report rather than being silently ignored (invariant 6). Run `tarseem validate <spec>` to see
coded errors and warnings before rendering.
