# tarseem-timeline — example external diagram type (custom layouter)

The **second** worked plugin example (F9, freeze gate). Where
[`incident-flow`](../incident-flow/) only changes a default node shape, `timeline` exercises a
*different* extension point: it supplies its own **`layouter_factory`** — a pure-Python single-axis
layouter — instead of ELK, with no edits to `src/tarseem`.

```bash
pip install -e examples/plugins/timeline      # from the repo root
tarseem render examples/plugins/timeline/example.json -o timeline.svg
```

Events are placed left-to-right along one axis; `"direction": "RL"` mirrors them right-to-left for
Arabic/RTL (geometry only — invariant 4). Rendering is inherited from the generic graph renderer.
See `tarseem_timeline/__init__.py` and the tutorial [`docs/extending/clone-a-type.md`](../../../docs/extending/clone-a-type.md).
