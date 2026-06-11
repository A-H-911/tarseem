# Swimlane Reference Images — Visual Feature Analysis

Source: reference images provided 2026-06-11 (D9 resolved). **Reconciled 2026-06-11** against the actual
files on disk — the originally-drafted "Order Fulfillment" diagram was not among the supplied images; the
analysis below describes the images that exist. They are outputs of the locally installed
`horizontal-swimlane-diagram` skill (draw.io-based, RTL-capable) — working prior art that validates the
draw.io-writer approach; mine its `scripts/generate.py` geometry/style constants during Phase 0/2.

Canonical files (bound by the Spike 3 / A12 / F3 acceptance gates):

| File | Diagram | Role |
|---|---|---|
| `reference-1-bug-triage-ltr.png` | Bug Triage (LTR, 4 lanes) | LTR workhorse — back-edge + long cross-lane edges + labels |
| `reference-2-document-procedure-rtl.png` | إجراءات استخراج وثيقة (RTL Arabic, 3 lanes) | RTL mirroring + Arabic shaping incl. diacritics |
| `reference-3-pipeline-shapes.png` | Pipeline (LTR, 3 lanes) | full shape set + UML markers + dashed/back-edge |
| `reference-supp-corporate-theme-ltr.png` | Corporate theme (LTR, 3 lanes) | **supplementary** — theme-portability demo |
| `reference-supp-monochrome-theme-ltr.png` | Monochrome theme (LTR, 3 lanes) | **supplementary** — same geometry, swapped palette |

The two `*-supp-*` images are **not** acceptance gates; they exist to demonstrate that per-lane theming is a
palette function over invariant geometry (binds F4 theme-portability, not A12).

## Reference 1 — "Bug Triage" (LTR, 4 lanes) — `reference-1-bug-triage-ltr.png`
- Full-width **title bar**: solid green, rounded corners, bold white centered text ("Bug Triage").
- 4 horizontal lanes: Reporter (green), Triage Engineer (orange), Developer (blue), QA (dark gold). Per-lane
  theme = one hue in three strengths: solid **header pill** (white bold label), light-tinted **lane band**,
  medium-tint **node fill** with darker border of same hue.
- Header column on the **left**, separated by a thin vertical rule; lane bands separated by horizontal rules.
- Steps ordered chronologically left→right across lanes; **numbered badges** ("2.", "3.", "4.", "5.") in the
  node's top-left corner, colored to lane hue. The start node ("Bug report") carries no badge.
- Shapes: **stadium/pill** for start ("Bug report") and terminal ("Close"); **diamonds** for decisions
  ("Real bug?", "Verify"); rounded rectangles for steps ("Classify", "Fix").
- Edges: single green color across all lanes, **orthogonal**, arrowheads at target. Edge labels:
  "no" (long top cross-lane edge Real bug?→Close), "yes" (Real bug?→Fix), "fails" (Verify→Fix **back-edge**),
  "passes" (long Verify→Close edge up two lanes). The long edges route without overlapping nodes.

## Reference 2 — "إجراءات استخراج وثيقة" (RTL Arabic, 3 lanes) — `reference-2-document-procedure-rtl.png`
- Full-width green **title bar**, white bold centered Arabic ("إجراءات استخراج وثيقة").
- 3 horizontal lanes with headers on the **right**: مقدّم الطلب (green), الاستقبال (orange), المراجعة (blue).
  Header column right-aligned, separated by a vertical rule; same hue→tints scheme as LTR.
- Flow proceeds **right→left**: تعبئة الطلب (stadium, far right, top lane) → استقبال (rounded-rect, badge "2."
  top-**right** corner) → مراجعة (rounded-rect, badge "3." top-right) → استلام (stadium, top lane, left).
- Arrows point **leftward**; edges orthogonal, green.
- Arabic correctly **shaped** everywhere incl. the diacritic-bearing **مقدّم** (lane label مقدّم الطلب).
- Same per-lane theming and edge style as the LTR references ⇒ theme is direction-independent; only geometry
  mirrors (header side, badge corner, flow/arrow direction).

## Reference 3 — "Pipeline" (LTR, 3 lanes, shape/marker variety) — `reference-3-pipeline-shapes.png`
- Full-width green **title bar** ("Pipeline").
- 3 lanes: User (green), System (orange), Storage (blue); headers left.
- UML **start marker** (filled black circle) before "Upload" and UML **end marker** (bullseye) after "Receipt",
  both inline in the first lane.
- Shape set beyond rects: **parallelogram** ("Upload" = data I/O, badge "1."), **diamond** ("Validate?"
  = decision, badge "2.") with **edge labels** ("ok", "bad"), rounded-rect ("Process", badge "3."),
  **cylinder** ("Save" = datastore, badge "4."), **document/wave** ("Receipt", badge "5.").
- Edge features: orthogonal green routing; **back-edge loop** ("bad": Validate? → up → Upload) routed without
  crossing nodes; **dashed edge** with label ("async", Process→Save); long cross-lane edge (Save→Receipt up two
  lanes) avoiding nodes.

## Supplementary — Theme portability — `reference-supp-corporate-theme-ltr.png`, `reference-supp-monochrome-theme-ltr.png`
- Identical geometry and content (3 lanes Sales/Ops/Support; Lead→Onboard→Assist; badge "2." on Onboard) drawn
  under two different base themes: "Corporate" (bright-blue title bar, blue/gray lane palette) and "Monochrome"
  (near-black title bar, full grayscale). Demonstrates that lane geometry, badges, shapes and routing are
  palette-independent — the theme is a swappable function, not baked into the layout. Binds **F4** (themes
  portable across writers), not the MVP swimlane gate.

## Engine requirements extracted (bind to FR-6 / MVP swimlane acceptance A12, full-target F3/F4)
1. Title-bar element (diagram-level, themed).
2. Lane headers at flow-start side: left (LTR) / right (RTL); header pill + band + node tints derived from a
   single per-lane hue (theme function, not 3 manual colors).
3. Auto-numbering badges with mirrored corner placement under RTL; start/terminal nodes may be badge-exempt.
4. Shape set: stadium, rounded-rect, diamond, parallelogram, cylinder, document; UML start/end markers.
5. Edge features: orthogonal routing, labels, dashed style, back-edges, long cross-lane edges avoiding nodes.
6. Full RTL mirroring = geometry only (header side, badge corner, flow/arrow direction); theme/palette invariant.
7. Arabic shaping incl. diacritics in title/lane/node labels.
8. Theme portability: palette is a swappable function over invariant geometry (supplementary refs; binds F4).
