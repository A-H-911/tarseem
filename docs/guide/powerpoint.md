# PowerPoint (PPTX) workflow

The PPTX writer turns a diagram into an editable PowerPoint slide of **native shapes** — auto
shapes, connectors, and text boxes placed from the positioned IR (08 §3, invariant 5). It is not
a picture and not an ungrouped SVG: every node is a real PowerPoint shape you can move, recolour,
and retype. Use this when a diagram needs to live inside a deck and be tweaked by hand.

## Generate a deck

```bash
tarseem export examples/swimlane-pipeline.json -f pptx -o out/ -n pipeline
# pptx: out/pipeline.pptx
```

```python
from tarseem import Engine
Engine().render(spec).export(["pptx"], "out/", name="pipeline")
```

Geometry comes straight from the IR (pixels → EMU), so the slide matches the SVG layout.

## Open it — install Cairo first (especially for Arabic)

Fonts are **not embedded** in the `.pptx`. The deck *names* `Cairo` — including the complex-script
slot that Arabic uses — so PowerPoint renders correctly **only if Cairo is installed**. Without it,
PowerPoint substitutes a default font (Latin stays legible; Arabic shaping degrades).

- Install Cairo from [Google Fonts](https://fonts.google.com/specimen/Cairo), or use the bundled
  `src/tarseem/assets/fonts/Cairo-VF.ttf`.
- Open in **Microsoft PowerPoint** for the faithful result — the web viewer and Keynote differ on
  bidi and the cube/cylinder shapes.

The `.report.json` sidecar (when present) records `fonts_embedded: none` so this is never a
surprise. Zero-install embedding is a deferred future task (a plain OPC embed made PowerPoint flag
the file for repair).

## Editing

Everything is native and editable:

- **Shapes** — rect / rounded / stadium / diamond / parallelogram / cylinder / document / cube,
  plus state pseudostates (initial dot, final bullseye). Click to select, double-click to edit text.
- **Lanes & phases** — swimlane bands, header chips, title bar, and phase bands are explicit shapes;
  move or recolour them freely.
- **Edges** — freeform connectors following the exact route, arrowhead at the target, dashes
  preserved. Curved corners are sampled into short segments (`curved_edges: partial`).
- **ER entities** — title bar + attribute rows + PK/FK pills as explicit cells (not native table
  ports).

## Arabic / RTL

RTL labels get paragraph direction (`a:pPr rtl="1"`) and the Cairo complex-script font, so with
Cairo installed PowerPoint shapes and joins Arabic correctly and lays the diagram out right-to-left
(lane headers on the right, number badges in the left corner). Mixed Arabic/Latin spacing is
owner-verified in real PowerPoint.

## What does not carry

Reported honestly in the CapabilityReport / sidecar:

- `fonts_embedded: none` — install Cairo (above).
- `gradients: none`, `theme_fidelity: partial` — flat fills/strokes/text colours; lane hues carried,
  no gradients or tints.
- `curved_edges: partial` — corners sampled, not true curves.
- `ports: partial` — ER rows are explicit cells, not native table ports.

The picture's source of truth is always the canonical SVG/PNG (`out/png/<sample>.png`).

## Determinism & provenance

Re-exporting the same spec yields a **byte-identical** `.pptx` (zip mtimes and core-property
timestamps are pinned — invariant 7). Provenance (spec hash + engine versions, no wall-clock) is in
**File ▸ Info ▸ Properties ▸ Comments**.

## Verifying a writer change

There is no headless PPTX renderer, so on-canvas appearance is checked by hand. After any change to
`src/tarseem/export/pptx.py`, run the deck review:

```bash
python tools/build_review.py examples/*.json   # decks in out/pptx/, side-by-side in out/index.html
```

then work through the per-deck **[manual PowerPoint checklist](../pptx-manual-checklist.md)** in real
PowerPoint. File any mismatch as a minimal repro + a regression test in `tests/test_export_pptx.py`.

## Next

- [Exports overview](exports.md) — all formats, the fidelity matrix, capability reports.
- [RTL & Arabic](rtl-arabic.md).
