# Quickstart

Tarseem turns a validated JSON spec into an architecture-grade diagram through one
positioned IR and many writers (ADR-001). This guide gets you from install to a rendered
SVG/PNG and the gallery.

## Install

```bash
python -m pip install -e ".[dev]"      # editable install + test/tooling
python -m playwright install chromium  # PNG export + E2E render in Chromium
```

A Node.js runtime must be on `PATH` — graph families (flowchart / architecture / dependency)
lay out via a pinned `elkjs` bundle in a Node subprocess (ADR-002). Swimlane and sequence
families are pure Python and need no Node.

## Verify the environment

```bash
tarseem doctor          # checks Node, the pinned elkjs bundle, Chromium, and the bundled font
tarseem doctor --json   # machine-readable
```

Every check that fails prints an actionable hint.

## Render a spec

CLI:

```bash
tarseem validate examples/flowchart.json          # coded, path-precise errors (exit 1 if invalid)
tarseem render  examples/flowchart.json -o out.svg
tarseem export  examples/sequence-login.json -f svg,png -o out/ -n login
```

Python API:

```python
from tarseem import Engine

spec = {...}                                 # or json.load a spec file
result = Engine().render(spec)
result.export(["svg", "png"], "out/", name="diagram")
print(result.report.to_dict())               # crossings / overlaps / extent / timing
```

`Engine().render()` runs the full pipeline (validate → compile → measure → layout → write)
and raises `SpecValidationError` — carrying the same coded issues as `validate` — on an
invalid spec. The SVG is the canonical, deterministic artifact; PNG is rasterised from it
via Chromium.

## Build the gallery

```bash
tarseem gallery --examples examples -o build/gallery
# open build/gallery/index.html from disk — no server needed
```

The gallery renders every example into an index grid (inline-SVG thumbnails + per-sample
metrics) and detail pages (inline SVG, spec JSON, RenderReport, downloads). It is the shared
fixture for manual review, the E2E suite, and screenshot regression.

## Determinism

The same spec and the same engine versions produce byte-identical output (A3). Artifacts can
embed a content-addressed spec hash + engine versions via `result.to_svg(provenance=True)`.

## Next

- [Diagram families](families.md) — the supported families with minimal specs.
- Acceptance + verification status: `docs/spikes/phase-3-progress.md`.
