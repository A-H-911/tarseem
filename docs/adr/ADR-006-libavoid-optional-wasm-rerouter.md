# ADR-006: libavoid as an optional, experimental WASM post-placement re-router

Status: Accepted (2026-06-12) · Supersedes nothing · Extends ADR-002 (layout adapters)

## Context

`06-layout-routing-strategy.md` §5 contemplated evaluating **libavoid** (Adaptagrams'
routing-only library) as a post-placement re-router behind the LayoutAdapter contract, *if*
Phase 5 routing quality proved insufficient. The Phase 5 benchmark corpus showed routing
quality is already strong (overlaps 0 everywhere; crossings 0 on all but two samples — a
single back-edge and a deliberately dense dependency web). libavoid was nonetheless
requested as an explicit, experimental feature.

We evaluated it empirically against the live, vendored engine before committing:

| Scenario | ELK / naive | libavoid |
|---|---|---|
| Auto-layout (dependency web, 14 edges) | **2** crossings (ELK) | 10–13 crossings |
| Fixed layout, obstacle routing (identical positions) | 10 through-node (naive) | **2** through-node |

**Finding.** As a re-router over ELK's *auto-placement*, libavoid is strictly worse — ELK's
layered algorithm co-optimizes placement and routing, leaving nothing to improve. Its real,
demonstrated value is **obstacle avoidance on non-negotiable fixed positions**, where it cuts
edges-through-boxes ~80% (10→2) at the cost of more edge-edge crossings.

## Decision

Vendor **libavoid-js 0.5.0-beta.5** (Emscripten/WASM port) and expose it as an **optional,
experimental, opt-in** post-placement re-router. It is **never** the default.

- **Why WASM, not C++ bindings.** We already run a pinned elkjs bundle in a Node subprocess.
  The WASM build runs in that same model: vendored + version-pinned like elkjs, byte-identical
  across OS (invariant 7 holds), no host C++ toolchain, no `pip install` breakage.
- **License (hard constraint).** libavoid-js is **LGPL-2.1-or-later**. The Apache-2.0 core
  forbids copyleft in the *required* path, so libavoid is an **optional extra, off by default**
  (same posture as Kroki). The LGPL WASM module is only loaded when the user explicitly sets
  `layout.router: "libavoid"`. The default render path never touches it.
- **Contract.** It implements the same boundary as ELK: a logical graph + positioned diagram
  in, a re-routed positioned diagram out. libavoid's object model lives only inside the
  `layout/libavoid` adapter + its WASM server; nothing it returns leaks Adaptagrams types.
- **Experimental + pinned.** Pinned to 0.5.0-beta.x and documented as experimental. The
  benchmark gate (`test_routing_benchmark`) runs the **default** router, so this feature can
  never silently regress shipped quality.

## Consequences

- New vendored artifact: `src/tarseem/_vendor/libavoid-js/` (WASM + Node glue + LICENSE).
- `engine doctor` reports the vendored WASM/glue as an optional component.
- Best for hand-placed / imported fixed layouts needing obstacle-aware routing. Documented as
  *worse than ELK for auto-layout*; the opt-in is a deliberate, informed choice.
- If a future need outgrows beta libavoid-js, the adapter boundary keeps replacement local.
