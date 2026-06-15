# Spike 5 Report — Searchable/selectable Arabic in the PDF export

Status: **DEFERRED** (owner decision 2026-06-15) · construction validated, Acrobat ceiling confirmed · throwaway code in `spikes/spike-5-pdf-searchable/`

## Objective
The committed PDF writer (`8098cc1`, mirrors `png.py`) is a faithful **visual** render, but Chromium
prints shaped Arabic as **Type3 visual-order glyphs with no logical Unicode**, so Arabic does not
copy or search. Goal: add an invisible logical-text layer ("OCR sandwich") so Arabic is
searchable/selectable, without disturbing the picture, determinism, or the no-GPL constraint
(PyMuPDF excluded; `pikepdf`/`pdfminer.six` are BSD/MPL and were spike-only — never added to
`pyproject.toml`).

## What was built (`spike5.py`)
A single throwaway script:
- `render_and_measure()` — render the example, measure each label's box from the `<text>` SVG in
  Chromium, and print the **visual** PDF from the **textAsPaths** SVG (same layout, text → outlines,
  so Chromium emits no competing text layer).
- `build_searchable_pdf()` — the validated overlay:
  - a self-contained empty-glyph **Type3 font + ToUnicode CMap** (logical codepoints), drawn
    **render-mode-3** (invisible), `Tz`-scaled to each label box;
  - a **Tagged PDF** structure (`/MarkInfo`, `StructTreeRoot → Document → /Span` per label with
    `/ActualText` + `/K` MCID, `ParentTree` linkage), plus inline `/ActualText`;
  - **CTM fix** — wrap the base content in `q … Q` before appending the overlay (`_isolate_then_append`),
    else it inherits Chromium's leftover flip+scale and lands **mirrored in a corner**;
  - **determinism** — pikepdf `deterministic_id` + drop Chromium's wall-clock docinfo dates.
- `build_debug_visible()` — same placement but **visible red** text; used to discover the CTM mirror
  bug and verify the `q … Q` fix (rendered via the Read tool).
- `validate()` — asserts determinism (two runs byte-identical), tagged structure, no live date, and
  runs the **poppler** oracle (`pdftotext`) when present.

## Result
**Works:** the PDF text becomes **selectable** in Acrobat and **single-word Ctrl+F search** works;
visual render untouched, deterministic, self-contained (no embedded font).

**The wall — multi-word phrase search:** four glyph layouts were built and owner-tested in real
Acrobat; none gave reliable multi-word phrase search:

| Construction | Acrobat result |
|---|---|
| logical order, single run per label (this script) | **best** — selectable + single-word search; multi-word matches first word only |
| visual-order reversal (evenly spread) | worse — "no spacing between words" |
| per-word real positions | regressed to nothing |
| per-glyph real positions, visual order | letter-by-letter / reversed |

**Why:** Acrobat indexes the **shown-glyph ToUnicode** (not `/ActualText`, which it ignores for
find/select even when tagged) and reconstructs RTL with its own bidi/word-segmentation that rejects a
synthetic per-label text layer. poppler's bidi mode *does* reconstruct every phrase — but **poppler
disagrees with Acrobat and there is no headless Acrobat oracle**, so each attempt costs a manual
round-trip. `pypdf`/`pdfminer` ignore `/ActualText` entirely; only poppler honors **inline**
`/ActualText`.

## Decision
Deferred. Keep the visual-only PDF as Phase-6's deliverable. If revisited, the likely remaining lever
is reproducing the shaper's true per-glyph positions/advances (uharfbuzz) instead of DOM-measured
boxes, validated iteratively in Acrobat — high effort, uncertain payoff.

## How to run
```
./.venv/Scripts/python.exe spikes/spike-5-pdf-searchable/spike5.py
# outputs: spikes/spike-5-pdf-searchable/out/arabic-flowchart-{searchable,debug-visible}.pdf
# optional: pip install pikepdf ; poppler's pdftotext on PATH enables the oracle
```

## Pinned versions
- pikepdf **10.8.0** (spike-only) · pdfminer.six (oracle cross-check, spike-only) · poppler `pdftotext` 4.00
- playwright 1.60.0 + Chromium · Python 3.13.7 · Windows 11
