# Bug-report fixes — progress

Seven issues reported against `out/*.png` renders. Methodology: minimal repro under
`tests/regressions/`, localize the layer via coordinate dumps, fix + regression test, or
document an engine limitation. Branch: `phase-5-routing`.

| # | Diagram | Status | Fix / layer | Commit |
|---|---|---|---|---|
| 1 | er-shop | ✅ done | ER connectors sharing a source side fanned to distinct corridors (elk adapter) | `51e8c6c` |
| 2 | nested | ✅ done | title extent + group-label font subset (swimlane writer) | `7e786ed` |
| 3 | arabic-rtl | ✅ done | long edge flips to alt L-orientation when default crosses another edge | lanegrid `_route_edges` |
| 4 | checkout-seq | ✅ done | messages attach to activation-bar border, not lifeline centre (sequence) | `f8d4da1` |
| 5 | incident | ✅ done | converging cross-lane edges spread to distinct entry heights | lanegrid `_route` |
| 6 | release | ✅ done | back-edge uses nearest clear corridor, not global bottom (lanegrid `_route`) | `1b81720` |
| 7 | vertical | ✅ done | proper vertical placement: flip lanes, keep landscape shapes | lanegrid `_vertical_layout` |

**All seven fixed.** Each landed with a `tests/regressions/` repro + regression test; visual
baselines were regenerated only where the change was intended (nested, sequence, er, vertical),
and the routing fixes (3/5/6) left the example baselines byte-identical (only problematic edges
were touched). Full gate green throughout.

## Routing notes (3/5/6)

The lane-grid router was extended from "avoid nodes" toward "avoid nodes AND other edges",
incrementally and conservatively:
- **6** tries the nearest clear detour corridor before the global bottom/top.
- **5** spreads edges converging on one node side onto distinct entry heights.
- **3** flips a cross-lane edge to the alternate L-orientation when its default vertical would
  cross another edge — applied only to edges that actually cross, so well-routed edges (and
  their baselines) are untouched.

These are targeted heuristics, not a general constraint solver. A long edge can still, in
dense layouts, find no crossing-free orthogonal route within the lane grid; the optional
libavoid post-router (ADR-006) remains the path for guaranteed nudged separation if a future
case needs it.
