# RTL & Arabic

Tarseem treats Arabic and right-to-left layout as first-class, not an afterthought. This
guide covers how text direction, shaping, mirroring, fonts, and the export options fit
together. The design rationale lives in `docs/plan/07-rtl-arabic-strategy.md`.

## Four principles

1. **Measure with shaping.** Label sizes come from uharfbuzz shaped advances *before*
   layout, so boxes fit the rendered Arabic (joining + ligatures), not a naïve character
   count.
2. **Render with shaping.** The canonical raster/PDF path is Playwright-managed Chromium,
   which shapes via HarfBuzz. **CairoSVG is never used** (it has no bidi support).
3. **Never pre-shape into the IR.** Text is stored as logical-order Unicode. Tarseem does
   not run `arabic-reshaper` / `python-bidi` upstream of a shaping renderer — that would
   double-shape and corrupt the output. Shaping happens once, at render.
4. **Layout mirroring ≠ text direction.** Two orthogonal controls:
   - `direction` (diagram-level, `LR`/`RL`/`TB`/`BT`) mirrors *geometry*.
   - `label.direction` (`auto`/`ltr`/`rtl`) sets a label's bidi base direction.

## Label direction

Each `label` may set `direction`:

| Value | Meaning |
|---|---|
| `auto` (or omitted) | Auto-detect: any Arabic/Hebrew character ⇒ RTL base, else LTR |
| `rtl` | Force RTL base direction |
| `ltr` | Force LTR base direction |

Auto-detection means you usually do not annotate anything — Arabic strings just render
RTL. Mixed runs (Arabic + Latin + digits) are ordered by the Unicode Bidi Algorithm at
render time; the Latin/numeric runs become LTR islands inside the RTL base. Set `lang`
(e.g. `"ar"`) to hint the renderer's script/justification; detected Arabic is tagged `ar`
automatically. See `examples/arabic-mixed.json`.

## RL mirroring (geometry only)

Setting `direction: "RL"` mirrors **geometry only** — the theme/palette is invariant
(`docs/plan/references/analysis.md` §Reference-2). What flips:

- **Flow**: graph families lay out right→left (ELK `direction=LEFT`); arrows reverse.
- **Swimlane lane headers** move to the **right**; the actor separator runs down the right.
- **Auto-number badges** move to the node's **top-right** corner.
- The title bar, lane bands, shapes, and colours are unchanged.

Examples: `examples/arabic-flowchart.json` (RL flowchart),
`examples/arabic-architecture.json` (RL architecture with a cylinder datastore), and the
swimlane rebuild of Reference-2, `examples/swimlane-document-rtl.json`.

## Themes are direction-independent

The three built-in themes (`default`, `corporate`, `monochrome`) are pure palette/title
functions over invariant geometry, so the same theme drives LTR and RTL diagrams
identically. Select one with `theme.ref` (or `theme.name`):

```json
{ "theme": { "ref": "corporate" } }
```

## Fonts

The bundled default font is **Cairo** (SIL OFL) — a dual-script family carrying full
Arabic (joining + diacritics) and Latin in one file. The renderer embeds a WOFF2 subset of
exactly the glyphs a diagram uses, so output is self-contained and identical anywhere
without a system font.

## Export options (`export.svg`)

| Option | Default | Effect |
|---|---|---|
| `embedFonts` | `true` | Embed the used-glyph WOFF2 subset as a data-URI. `false` drops it and falls back to the named font stack (smaller file; consumer needs an Arabic font). |
| `textAsPaths` | `false` | Convert every `<text>` to shaped glyph **outlines**. Renders identically on any SVG consumer — including renderers with no bidi/HarfBuzz — at the cost of text selectability. Recommended when publishing to unknown renderers. |

```json
{ "export": { "svg": { "textAsPaths": true } } }
```

## Verifying the toolchain

`tarseem doctor` checks the bundled Cairo font and Arabic shaping (uharfbuzz). Where
`Pillow` + `libraqm` is available it also runs as a measurement cross-check; on platforms
without libraqm (commonly Windows) uharfbuzz is the single source of truth and the
cross-check is reported as unavailable rather than failing.

## Known limitation

Long lane titles do not yet wrap inside the fixed-width header column — keep lane labels
short, or widen via layout options. Automatic label wrapping is planned for a later phase
and is surfaced as a capability note rather than silently clipped.
