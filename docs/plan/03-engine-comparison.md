# Candidate Engine Research & Comparison Matrix

Status: Research-backed · 2026-06-11
Ratings: ✅ strong fit · 🟡 partial fit · 🔻 weak fit · ❓ unknown/requires validation · ⛔ not suitable
Every non-obvious claim below was verified against documentation, issue trackers, or release pages (June 2026); sources at bottom. Capability legend used throughout: NATIVE / WORKAROUND / ADAPTER / UNSUPPORTED / UNVERIFIED.

---

## 1. Master Matrix (vs. project requirements)

| Requirement | Mermaid | PlantUML | Graphviz | D2 | ELK/elkjs | Dagre | draw.io (XML+CLI) | Excalidraw | bpmn-js | Cytoscape.js | JointJS | GoJS | Kroki | Playwright pipeline | python-pptx |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Maturity / maintenance | ✅ v11.15, MIT | ✅ v1.2026.6, solo-maint. | ✅ 30 yr, EPL-2.0 | ✅ v0.7.x, MPL-2 | ✅ 0.11.1 (3/2026), EPL-2 | 🟡 revived 3.0, MIT | ✅ format stable ~2012 | ✅ v0.18, MIT | ✅ Camunda | ✅ MIT | ✅ MPL-2 core | ✅ commercial | ✅ v0.29, MIT | ✅ Microsoft, Apache-2 | ✅ v1.0, MIT |
| Cross-platform | ✅ (Node) | 🟡 (Java; new native bins) | ✅ | ✅ (Go bin) | ✅ (Node) | ✅ (Node) | 🟡 (Electron; Xvfb in CI) | ✅ | ✅ (Node) | ✅ | ✅ | ✅ | ✅ (Docker) | ✅ (manages own browsers, no Xvfb) | ✅ |
| Python integration | 🟡 community libs/subproc | 🟡 subproc/HTTP | ✅ graphviz/pygraphviz | 🟡 subproc | 🟡 Node subproc (proven: capellambse) | 🟡 subproc | ✅ we emit XML directly | 🟡 emit JSON | 🟡 emit BPMN XML | 🟡 browser only | 🟡 browser only | 🟡 | ✅ kroki PyPI/HTTP | ✅ official Python API | ✅ native |
| JSON-driven (no DSL) | ⛔ DSL only | 🔻 DSL (+JSON preproc) | ⛔ DOT only | ⛔ DSL only | ✅ **ELK JSON in/out** | 🟡 graphlib JSON | ✅ XML is data | ✅ JSON scene | ✅ XML is data | ✅ JSON elements | ✅ JSON | ✅ JSON | 🟡 DSL envelope | n/a | n/a |
| Diagram coverage | 🟡 wide but no swimlane/activity/component | ✅ broadest UML+C4 | 🔻 generic graphs | 🟡 good general | n/a (layout only) | n/a | ✅ anything (we draw) | 🔻 sketch style | 🔻 BPMN only | 🔻 networks | 🟡 | ✅ | ✅ aggregates | n/a | n/a |
| Layout control | 🔻 none manual; ELK opt-in | 🔻 limited | ✅ pos!, ports, ortho | 🟡 (TALA=paid) | ✅ full options model | 🔻 | 🔻 (no auto-layout headless) | ⛔ manual | 🟡 DI coords required | 🟡 via elk ext | 🟡 | ✅ | inherits | n/a | ⛔ (no layout) |
| Edge routing / crossings | 🟡 | 🟡 (dot) | ✅ dot best-in-class DAG; ortho approx | 🟡 | ✅ orthogonal+splines, crossing min., junction pts | 🔻 polyline only | 🔻 | ⛔ | 🟡 | 🟡 | 🟡 | ✅ | inherits | n/a | 🔻 straight/elbow |
| Ports/anchors | ⛔ | 🔻 | 🟡 compass | 🔻 | ✅ first-class + constraints | ⛔ | ✅ (fixed points) | ⛔ | ✅ | 🟡 | ✅ | ✅ | inherits | n/a | 🟡 connection pts |
| Swimlanes | ⛔ (open reqs #551/#2028/#6608) | 🟡 vertical-only activity lanes | 🔻 rank hacks | 🔻 grid approx (#236/#328) | ✅ partitioning (geometry; bands drawn by caller) | ⛔ | ✅ **native pool/lane shapes** | ⛔ | ✅ native BPMN pools/lanes | ⛔ | 🟡 (+$ in JointJS+) | ✅ ($) | via PUML | n/a | 🟡 we draw rects |
| RTL/Arabic text | 🔻 diacritics crash #3047; browser-shaped otherwise | ❓ JVM-dependent, no bidi docs; layout LTR-only | 🟡 NATIVE with pango build (platform-varying) | ❓ browser-shaped SVG only | n/a (geometry) | n/a | ✅ writingDirection=rtl + browser shaping | 🟡 browser only | ❓ | ❓ | ❓ | ❓ | inherits | ✅ **Chromium HarfBuzz verified** | ✅ PowerPoint shapes itself; rtl="1" XML patch |
| RTL layout mirroring | ✅ `RL` | ⛔ none | ✅ rankdir=RL | ✅ direction:left (global) | ✅ direction=LEFT | 🟡 | ✅ | manual | ❓ | 🟡 | 🟡 | ✅ | inherits | n/a | manual |
| Styling depth | 🟡 themes+classDef | ✅ skinparam deep | ✅ attrs, no themes | ✅ globs+themes | n/a | n/a | ✅ full style strings | 🟡 | 🔻 | ✅ CSS-like | ✅ | ✅ | inherits | ✅ full CSS | 🟡 |
| Export formats | SVG/PNG/PDF | SVG/PNG/PDF/EPS/TikZ/TXT | SVG/PNG/PDF/JSON/plain | SVG/PNG/TXT | JSON | JSON | SVG/PNG/PDF/VSDX | PNG/SVG | SVG/PNG/PDF | PNG/SVG | SVG | SVG | SVG/PNG | PNG/PDF (+our SVG) | PPTX |
| Editable output | ⛔ | ⛔ | ⛔ | ⛔ | n/a | n/a | ✅ **is the editable format** | ✅ own format | ✅ BPMN XML standard | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ | ✅ **native PPTX shapes** |
| Browser gallery use | ✅ | 🔻 | 🔻 | ✅ | n/a | n/a | 🟡 embed viewer | ✅ | ✅ | ✅ | ✅ | ✅ | 🟡 | ✅ the mechanism itself | n/a |
| Licensing fit | ✅ MIT | 🟡 GPL (multi) | ✅ | ✅ MPL-2 (TALA $) | ✅ EPL-2 | ✅ MIT | ✅ format use OK | ✅ MIT | ⛔ **mandatory watermark** | ✅ MIT | 🟡 core MPL / + $ | ⛔ $3,995/dev | ✅ MIT | ✅ | ✅ MIT |
| Agent-generated specs | 🟡 strict parser | 🟡 | 🟡 | 🟡 good errors | ✅ via our JSON schema | 🟡 | ✅ via our JSON schema | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 | ✅ | n/a | n/a |
| Operational complexity | M (Node+puppeteer) | M-H (Java+Graphviz) | L | L (one binary) | M (Node subproc) | M | H in CI (Xvfb) | M (browser export) | M | M | M | M | M (Docker) | M (managed) | L |

## 2. Architecture-Consequence Findings

1. **Layout is the scarce capability.** Only ELK combines: layered+orthogonal routing, first-class ports, compound nodes, partitioning (lane columns/rows), crossing minimization, and a documented **JSON in → JSON out** contract usable as a service boundary. Dagre lacks ports/compound/ortho (cluster bugs verified); Graphviz has great `dot` but workaround-level ports/lanes and text-based I/O; OGDF is GPL (excluded); libavoid routes but doesn't place (future enhancer); yFiles/Tom Sawyer commercial-only.
2. **Text-DSL engines cannot be the core.** Mermaid/PlantUML/D2 accept only their DSLs (lossy targets, not sources), lack swimlanes (Mermaid, D2) or horizontal lanes (PlantUML vertical-only), and have unverified-to-broken Arabic. They remain valuable as **best-effort source-export adapters** (regeneration interop) — exactly the brief's "Mermaid/PlantUML source where practical".
3. **Arabic forces a browser-class renderer somewhere in the pipeline.** Chromium (via Playwright) ships HarfBuzz+ICU — full shaping+bidi, verified. CairoSVG documented as not supporting bidi (banned). resvg/rustybuzz lacks Arabic fallback shaping (fonts must have complete GSUB; optional fast path only). Inkscape (Pango) is correct but adds a GPL binary dep — optional.
4. **Editability is achieved by *writing formats*, not by converting images.** Because our pipeline owns positioned geometry (post-ELK IR), we can emit: (a) draw.io mxGraph XML with native `swimlane` pool/lane shapes, `writingDirection=rtl`, exact geometry — opens in diagrams.net fully editable; (b) native PPTX shapes/connectors via python-pptx (EMU coordinates from the same IR) — fully editable in PowerPoint, which performs its own Arabic shaping. No EMF, no SVG-ungroup dependency (kept only as a documented manual option).
5. **The wrapper must own text measurement.** ELK does not measure text; engines that do measure assume LTR. uharfbuzz advances (+ Pillow/raqm cross-check) are the only reliable Arabic-aware sizing path. This single capability is what makes correct Arabic node sizing possible anywhere.
6. **Kroki is an aggregator, not a foundation** — useful optional backend for PlantUML/Mermaid rendering without local Java/Node, but no IR, bundled version coupling, network dependency.
7. **bpmn-js** is the best swimlane *semantic* model (BPMN 2.0 DI standard) but the bpmn.io license requires a visible watermark — disqualifying for polished enterprise output; optional adapter at most.
8. **GoJS (US$3,995/dev), TALA (commercial), JointJS+ (commercial), OGDF (GPL)** — excluded from required path on licensing; capability notes retained for completeness.

## 3. Verdicts

| Role | Selection | Rationale |
|---|---|---|
| **Primary layout** | **ELK via elkjs** (pinned bundle, long-lived Node subprocess, ELK JSON contract) | Only OSS engine with ports+partitioning+ortho routing+JSON contract; pattern production-proven (capellambse, Mermaid, D2 all embed ELK) |
| **Primary renderer** | **Own SVG renderer in Python** (templated SVG from positioned IR) | Total styling/theme/RTL control; SVG is the canonical artifact every other export derives from |
| **Raster/PDF + verification** | **Playwright (Chromium)** | Verified Arabic shaping; PNG/PDF; powers gallery E2E + screenshot regression; no Xvfb |
| **Sequence layout** | **Custom deterministic Python layout** | Sequence ≠ graph layout; trivial to own; removes ELK misuse |
| **Editable exports** | **Own draw.io XML writer** + **python-pptx writer** (both consume positioned IR) | Verified native lanes/RTL keys in mxGraph format; native PowerPoint shapes; drawpyo too immature, EMF rejected |
| **Fallback layout** | Graphviz (`dot`) optional adapter | Zero-Node environments; mature Python libs; reduced fidelity documented |
| **Source exports (best-effort)** | Mermaid, PlantUML writers | Interop/regeneration only; lossiness reported per export |
| **Optional backends** | Kroki client; resvg fast PNG (Latin-only guard); Inkscape (text-to-path); bpmn-js (watermark warning) | Opt-in extras |
| **Excluded** | dagre, OGDF, GoJS, JointJS+/JointJS-core, Cytoscape.js, React Flow, Excalidraw-as-core, CairoSVG | Structural gaps or licensing; Excalidraw optional sketch-style writer later if desired |

Full rationale & trade-offs: `04-architecture.md`. Risks referenced: R-8…R-19.

## 4. Key Sources (verification anchors)

- ELK JSON & options: eclipse.dev/elk (json format, partitioning, direction, hierarchyHandling); elkjs releases (0.11.1, 3/2026); issues #503, #401; capellambse-context-diagrams (Python↔elkjs pattern)
- Mermaid: releases (11.15.0); swimlane issues #551/#2028/#6608; Arabic diacritics #3047; @mermaid-js/layout-elk
- PlantUML: changes (V1.2026.x, native images); horizontal-swimlane forum 13375 (vertical-only); unicode/FAQ (no bidi statement)
- Graphviz: font FAQ (pango for bidi); rankdir=RL; EPL license page; graphviz/pygraphviz PyPI
- D2: releases v0.7.x; layouts docs (TALA commercial, global direction); discussions #236/#328/#990
- dagre: repo status (3.0.0 revival), cluster issues #13/#196
- draw.io: FAQ text-right-to-left & writing-direction; swimlane blog; CLI/export repos (rlespinasse), Xvfb/no-sandbox issues
- Excalidraw: JSON schema docs; RTL PR #1154; CJK/Arabic fonts issue #8408
- bpmn-js: bpmn.io/license (watermark clause); bpmn-to-image
- Playwright: docs (browsers/screenshots/pdf); Chromium HarfBuzz dependency
- resvg: rustybuzz Arabic-fallback gap; CairoSVG svg_support page (no bidi)
- python-pptx: connector/freeform API docs; rtl="1" XML pattern (python-openxml threads)
- drawio2pptx v0.0.7 (alpha, 2/2026); drawpyo v0.2.5 (alpha)
- Fonts: Google Fonts OFL pages (Noto Sans Arabic, Cairo, Tajawal, Amiri, IBM Plex Sans Arabic)
- GoJS pricing (nwoods.com/sales); yFiles/Tom Sawyer licensing pages; OGDF GPL; uharfbuzz/Pillow-raqm docs & issues (#4496, #4859)
