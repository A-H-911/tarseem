# tarseem-incident-flow — example external diagram type

A worked, installable example of extending Tarseem with a **new diagram type** without touching
the engine — the proof behind acceptance criterion **F9**. It adds an `incident-flow` family (a
`flowchart` clone for incident-response runbooks) by registering a `DiagramTypePlugin` on the
`tarseem.types` entry-point group.

This package is the end product of the tutorial: [`docs/extending/clone-a-type.md`](../../../docs/extending/clone-a-type.md).

## Install & use

```bash
pip install -e examples/plugins/incident-flow   # from the repo root
tarseem render examples/plugins/incident-flow/example.json -o incident.svg
```

Once installed, `incident-flow` is a first-class type: it validates, compiles, lays out via ELK,
renders to SVG/PNG/PDF, and exports to draw.io/PPTX — all through the same pipeline as the
built-ins, with **no edits under `src/tarseem`**.

## What it customises

Just the default node shape (`stadium`). Layout (ELK layered) and rendering (the generic graph
renderer) are inherited from the `DiagramTypePlugin` defaults — see `tarseem_incident_flow/__init__.py`.
