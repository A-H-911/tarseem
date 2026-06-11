# Swimlane Reference Images — Visual Feature Analysis

Source: 3 reference images provided 2026-06-11 (D9 resolved). Drop the PNG files in this folder as
`reference-1-order-fulfillment-ltr.png`, `reference-2-document-procedure-rtl.png`, `reference-3-pipeline-shapes.png` for side-by-side acceptance gates.
Note: the style matches the output of the locally installed `horizontal-swimlane-diagram` skill (draw.io-based, RTL-capable) — working prior art that validates the draw.io-writer approach; mine it for geometry/style constants during Phase 0/2.

## Reference 1 — "Order Fulfillment" (LTR, 4 lanes)
- Full-width **title bar**: solid green, rounded corners, bold white centered text.
- 4 horizontal lanes (Customer/green, Online Store/orange, Warehouse/blue, Shipping Provider/dark gold). Per-lane theme = one hue in three strengths: solid **header pill** (white bold label), light-tinted **lane band**, medium-tint **node fill** with darker border of same hue.
- Header column on the **left**, separated by a thin vertical rule; lane bands separated by hue-colored horizontal rules.
- Steps ordered chronologically left→right across lanes; **numbered badges** ("2.", "3.", …) in node's top-left corner, colored to lane hue.
- Shapes: stadium/pill for start ("Place order") and end ("Receive"); rounded rectangles for steps.
- Edges: single green color across all lanes, **orthogonal**, arrowheads at target, clean vertical drops between lanes, one long multi-lane edge (Deliver→Receive) routed without overlapping nodes.

## Reference 2 — "إجراءات استخراج وثيقة رسمية" (RTL Arabic, 4 lanes)
- Full **mirror** of Reference 1: header column on the **right**; flow proceeds right→left (first step at far right); numbered badges in node's top-**right** corner; arrows point leftward.
- Arabic correctly shaped everywhere: title, lane labels (مقدّم الطلب، موظف الاستقبال، المراجع، جهة الإصدار), node labels (incl. diacritic-bearing مقدّم).
- Same per-lane theming and edge style as LTR version ⇒ theme is direction-independent; only geometry mirrors.

## Reference 3 — "Pipeline" (LTR, 3 lanes, shape/marker variety)
- UML **start marker** (filled black circle) and **end marker** (bullseye) inline in the first lane.
- Shape set beyond rects: **parallelogram** (Upload = data I/O), **diamond** (Validate? = decision) with **edge labels** ("ok", "bad"), **cylinder** (Save = datastore), **document/wave** (Receipt).
- **Dashed edge** with label ("async"); **back-edge loop** ("bad": diamond → up → Upload) routed orthogonally without crossing nodes.

## Engine requirements extracted (bind to FR-6 / MVP swimlane acceptance A12)
1. Title-bar element (diagram-level, themed).
2. Lane headers at flow-start side: left (LTR) / right (RTL); header pill + band + node tints derived from a single per-lane hue (theme function, not 3 manual colors).
3. Auto-numbering badges with mirrored corner placement under RTL.
4. Shape set: stadium, rounded-rect, diamond, parallelogram, cylinder, document; UML start/end markers.
5. Edge features: orthogonal routing, labels, dashed style, back-edges, long cross-lane edges avoiding nodes.
6. Full RTL mirroring = geometry only; theme/palette invariant.
7. Arabic shaping incl. diacritics in title/lane/node labels.
