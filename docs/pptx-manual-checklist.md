# PPTX export — manual PowerPoint checklist

The PPTX writer (`src/tarseem/export/pptx.py`) emits **native** PowerPoint shapes from the
positioned IR (08 §3, invariant 5): no embedded image, no SVG ungroup. Automated tests cover
structure/determinism/RTL, but **glyph shaping and on-canvas appearance can only be judged in real
PowerPoint** — there is no headless PPTX renderer in CI. Run this checklist after any change to the
writer.

Generate the bundle **with the project venv** (bare `python` won't find `tarseem`):
`.venv\Scripts\python.exe tools/build_review.py examples/*.json` on Windows, or
`.venv/bin/python tools/build_review.py examples/*.json` on macOS/Linux. The script expands the
glob itself, so the `examples/*.json` form works in PowerShell/cmd too. Decks land in
`out/pptx/*.pptx` (and `out/index.html` links them per diagram alongside every other format). Open each `.pptx` in
**Microsoft PowerPoint** (not only the web/Keynote — bidi + cube/can shapes differ).
See `out/README.md` for the full `out/` layout.

## Per-deck checks

For every `out/pptx/<sample>.pptx`:

- [ ] **Native, editable** — click a node; it selects as a shape (not a picture). Double-click edits text.
- [ ] **Shapes** match the engine SVG: rect/roundrect/stadium/diamond/parallelogram/cylinder(can)/document/cube.
- [ ] **Fills + borders** match the lane/shape colours; border widths look right (swimlane 2px, ER/sequence 1.5px).
- [ ] **Text** is centered, legible, the right colour; font is Cairo (or PowerPoint's substitute — see fonts note).
- [ ] **Edges** are connectors following the exact route, with an arrowhead at the target; dashed edges are dashed.
- [ ] **Edge labels** sit on/above the line with a readable (tight) white halo.

## Family-specific

- [ ] **swimlane-*** — title bar, lane bands + header chips (no stray black borders), phase bands, separators.
- [ ] **swimlane-document-rtl / arabic-*** — Arabic is shaped + joined correctly and reads right-to-left;
      lane headers on the **right**, number badges in the **left** corner.
- [ ] **swimlane-vertical-release** — lanes are columns; headers across the top.
- [ ] **er-shop** — entity = title bar + attribute rows + separators + gold/blue PK/FK pills.
- [ ] **sequence-login** — centered title, participant heads, dashed lifelines, activation bars, labels above lines.
- [ ] **state-order-lifecycle** — initial = solid dot, final = bullseye (ring + inner dot); not plain boxes.
- [ ] **deployment-web-stack** — cubes + cylinders read as 3-D; labels centered on the cube front face.

## Cross-cutting

- [ ] **Badges** are small filled corner circles with the number, white text.
- [ ] **Determinism** — re-exporting the same spec yields a byte-identical `.pptx` (tested; spot-check if curious).
- [ ] **Provenance** — File ▸ Info ▸ Properties shows the spec hash / engine versions in Comments; no real date.

## Fonts (install Cairo)

PPTX cells **name** `Cairo` (incl. the complex-script `a:cs` slot, so Arabic uses it). Fonts are
**not embedded** in the `.pptx` — so **Cairo must be installed** for correct rendering, especially
Arabic. **Verified:** with Cairo installed, PowerPoint renders Latin + Arabic correctly; without
it, PowerPoint substitutes a default font.

Install Cairo from Google Fonts (<https://fonts.google.com/specimen/Cairo>) or instance the bundled
`src/tarseem/assets/fonts/Cairo-VF.ttf`. The `.report.json` sidecar records `fonts_embedded: none`.

Zero-install font **embedding is deferred** (see the future task in `docs/spikes/phase-6-progress.md`):
a plain OPC embed made PowerPoint flag the file for repair; it likely needs PowerPoint's font
obfuscation and must be done as an iterative loop with a PowerPoint to validate against.

## Reporting issues

For any mismatch, note the **deck + element**, compare against `out/png/<sample>.png`
(the canonical SVG = source of truth), and file it the same way as the draw.io review rounds:
minimal repro, fix in `pptx.py`, regression test in `tests/test_export_pptx.py`.
