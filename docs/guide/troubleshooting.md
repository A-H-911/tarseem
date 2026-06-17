# Troubleshooting

## First: `tarseem doctor`

```bash
tarseem doctor          # checks Node, the pinned elkjs bundle, Playwright Chromium, bundled fonts
tarseem doctor --json   # machine-readable
```

It reports each missing/broken dependency with an actionable fix. Most render failures are one of
its checks failing.

## Toolchain

| Symptom | Cause | Fix |
|---|---|---|
| Graph families fail; swimlane/sequence work | Node.js not on PATH (ELK runs in a Node subprocess) | install Node LTS; re-run `tarseem doctor` |
| PNG/PDF export errors | Playwright Chromium not installed | `python -m playwright install --with-deps chromium` |
| `sync API inside asyncio loop` when rastering | calling raster rendering from inside an event loop | use `tarseem.generate(...)` — it subprocesses raster for you (see [agents.md](agents.md)) |
| `ModuleNotFoundError: tarseem` running scripts | bare `python` instead of the venv | use `.venv/Scripts/python.exe` (Windows) / `.venv/bin/python` |
| A newly-installed plugin's type isn't found | entry-point metadata is stale | re-run `pip install -e .` in the plugin package (refreshes `entry_points.txt`) |
| Arabic renders as boxes/unshaped | font/shaping toolchain | confirm `tarseem doctor` fonts check; for PPTX, **install the Cairo font** (it is not embedded) |
| Garbled non-ASCII in a Windows console | cp1252 console | the CLI forces UTF-8 output; if piping, ensure the consumer decodes UTF-8 |

## Validation error codes

`tarseem validate spec.json` (and `generate`) return coded, path-precise errors —
`{code, path, message, hint}`. `path` is a JSON Pointer into your spec.

| Code | Meaning | Fix |
|---|---|---|
| `E_VERSION` | `specVersion` is pre-1.0 | run `tarseem migrate spec.json` |
| `E_SCHEMA` | structural: wrong type / unknown property / missing required field | follow the `hint`; unknown keys may need an `x-*` vendor prefix |
| `E_PROFILE` | the diagram type forbids/requires a field (e.g. a sequence with `lanes`, a swimlane without `lanes`) | remove/add the field named in `path` |
| `E_DUP_ID` | duplicate `id` within a collection | make ids unique |
| `E_BAD_REF` | edge/group endpoint isn't a node/group id | point at an existing id |
| `E_BAD_LANE` / `E_BAD_PHASE` | node references an undeclared lane/phase | declare it under `spec.lanes` / `spec.phases` |
| `E_BAD_PORT` | edge `sourcePort`/`targetPort` not declared on the node | add it under the node's `ports` (or ER `attributes`) |
| `E_BAD_STYLEREF` | `styleRefs` names an undefined preset | define it under `spec.styles` |
| `E_OUTPUT` | a file format was requested without `out_dir` (agent surface) | pass `out_dir` (SVG is returned inline) |
| `E_RENDER` | layout/render failed downstream | run `tarseem doctor`; check the `hint` |
| `W_ORPHAN` *(warning)* | a node has no edges | connect or remove it (non-fatal) |

## Visual-regression baselines

Baselines are OS-specific (Chromium rasterises fonts per platform) and live under
`tests/baselines/<platform>/`. A missing baseline for a sample **skips** (never fails) on that
platform. Regenerate for the current OS with `scripts/regen_baselines.py`; linux/macOS baselines are
produced by the `baselines.yml` CI workflow (an explicit, reviewed action — R-21). See
[../../docs/spikes/](../spikes/) and `tests/test_visual_regression.py`.
