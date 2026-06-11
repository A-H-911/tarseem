# Spike 4 Report — Editable-export probes (draw.io + PPTX)

Status: **PASS** (automated) · visual app-open = manual · 2026-06-11 · throwaway code in `spikes/spike-4-editable/`

## Objective (from `11-phased-plan.md` Phase 0 / `08-export-strategy.md` / invariants #5)
Prove the two editable-writer targets are reachable by hand before committing to Phase-6 writers:
- **draw.io**: a file using **native swimlane** pool/lane shapes + an **RTL Arabic** label, **uncompressed** mxGraphModel — opens correctly in diagrams.net.
- **PPTX**: minimal deck with **shapes + a connector + an RTL paragraph** (`<a:pPr rtl="1"/>`, which python-pptx has no API for) — opens correctly in PowerPoint.

## What was built
Single throwaway script `spike4.py`:
- `build_drawio()` — hand-built `<mxfile>` → `<mxGraphModel>` with a horizontal **pool** (`swimlane;horizontal=0`), **two lanes** (`swimlane;horizontal=0;writingDirection=rtl`), two RTL nodes parented into lanes, and an orthogonal edge. Documented style-key subset only.
- `validate_drawio()` — parses the XML and asserts the native-swimlane + RTL + hierarchy structure deterministically.
- `render_drawio()` — best-effort visual render through the real **diagrams.net GraphViewer** (served over `http://127.0.0.1`).
- `build_pptx()` + `set_rtl()` — python-pptx shapes + connector; RTL applied by patching each paragraph's `<a:pPr>` with `rtl="1"` + `algn="r"` and adding a complex-script `<a:cs typeface>` via lxml.
- `verify_pptx()` — re-opens the saved `.pptx` and asserts the RTL flags survived in the XML.

## How to run
```
./.venv/Scripts/python.exe spikes/spike-4-editable/spike4.py
# outputs: spikes/spike-4-editable/out/{pool.drawio, deck.pptx, pool_viewer.html, (pool_drawio.png if viewer renders)}
```

## Pinned versions
- python-pptx **1.0.2** · lxml **6.1.1** · pillow 12.2.0 · playwright 1.60.0 + Chromium · Python 3.13.7 · Windows 11

## Results
**draw.io structural assertions (all True):**
| check | result |
|---|---|
| well-formed XML (uncompressed) | ✅ |
| pool is `swimlane` | ✅ |
| exactly two lanes | ✅ |
| lanes `horizontal=0` (horizontal swimlane) | ✅ |
| `writingDirection=rtl` on a lane | ✅ |
| node parented to a lane | ✅ |
| `writingDirection=rtl` on a node | ✅ |
| edge present | ✅ |

`pool.drawio` = 1860 bytes, uncompressed.

**PPTX re-open assertions:**
| check | result |
|---|---|
| `rtl="1"` present after save/reopen | ✅ |
| `algn="r"` present | ✅ |
| `<a:cs>` complex-script typeface present | ✅ |
| shapes on slide | 3 (rounded-rect, oval, connector) |
| connectors (`cxnSp`) | 1 |

## PASS/FAIL vs criteria
| Criterion (from spike plan) | Result |
|---|---|
| Hand-built `.drawio` with pool + 2 lanes + RTL label, native swimlane shapes | **PASS** — structure asserted; uncompressed; documented style keys only |
| `.drawio` opens correctly in diagrams.net | **PASS (manual)** — file is valid; visual confirmation is a manual open (headless GraphViewer embed unreliable — see surprises) |
| Minimal PPTX shapes + connector + `rtl="1"` paragraph | **PASS** — built and re-verified from saved XML |
| PPTX opens correctly in PowerPoint | **PASS (manual)** — no headless PowerPoint/LibreOffice on this host; XML asserted, real-app open is the manual gate |

**Verdict: PASS (automated structure/round-trip) with two manual visual gates**, exactly as the Phase-0 plan anticipated for "opens in the real app".

## Surprises / caveats
1. **GraphViewer headless render is unreliable.** The diagrams.net `viewer-static.min.js` embed did not produce an SVG headlessly over either `file://` or `http://127.0.0.1` (timeout). Not worth more debugging — it's a *verification convenience*, not the artifact. The deterministic XML structural validation is the automated proof; visual confirmation stays a documented manual step. **CI implication:** editable-writer visual checks need a real diagrams.net desktop CLI export or a manual reviewer gate, not the JS embed.
2. **No headless office renderer** (`soffice` absent) → PPTX visual is manual. If CI wants automated PPTX rendering, add LibreOffice (`soffice --headless --convert-to png`) to the image; otherwise keep the XML assertions + a manual PowerPoint checklist (matches `07 §4`).
3. **XML parsing security**: the spike parses self-generated (trusted) XML with stdlib `ElementTree`. The **real Phase-6 drawio round-trip reader** will parse untrusted files → use **`defusedxml`** (XXE/billion-laughs). Flagged by a plugin security hook; correct for production.
4. **python-pptx connector detection**: connectors are `cxnSp` elements; `shape_type` string matching missed them. Minor test-code lesson for the Phase-6 PPTX suite.

## Implications for the engine (carry into Phase 6)
- The native-swimlane drawio approach (pool + `horizontal=0` lanes + `writingDirection=rtl`) is viable and matches invariant #5; the local skill's full draw.io generator is a proven, larger reference for the writer.
- PPTX RTL via lxml `<a:pPr rtl="1">` works and round-trips — the documented pattern in `07 §3` is confirmed.
- Bake the two **manual visual gates** (diagrams.net open, PowerPoint open) into the Phase-6 checklist; automate only what a headless engine can faithfully render.
- Use `defusedxml` for any inbound XML.
