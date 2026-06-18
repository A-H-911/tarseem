# Tarseem — Deferred Work & Tech-Debt Register

Durable, findable index of known-but-not-yet-done work. Each entry is actionable enough that a
future session can pick it up cold. This is **tracking**, not a contract — the approved design
lives in `docs/plan/`; architecture decisions in `docs/adr/`.

Status legend: **Open** (not started) · **In progress** · **Done** (move to a dated note below) ·
**Won't do** (record why).

---

## TD-001 — ELK adapter selects the mindmap algorithm by `diagram_type` (invariant-8 seam)

- **Status:** Open
- **Severity:** Low — documented as non-blocking in ADR-008; no correctness/security/visual impact.
  It is a *purity* gap in invariant 8, not a defect.
- **Invariant at stake:** #8 (CLAUDE.md) — *"diagram types are plugins … nothing in the core
  pipeline hard-codes a family name."*

### What's coupled

The ELK layout adapter still branches on the literal family string `"mindmap"` in three places
(`src/tarseem/layout/elk/__init__.py`):

| Site | Line | What it does |
|---|---|---|
| `layout()` | ~130 | `graph.diagram_type == "mindmap" and mindmapStyle == "radial"` → runs `remove_radial_overlaps` (a post-ELK cleanup pass) |
| `_to_elk()` | ~139 | `graph.diagram_type == "mindmap"` → diverts to `_to_elk_mindmap` |
| `_to_elk_mindmap()` | ~195 | selects `_MRTREE_OPTIONS` vs `_RADIAL_OPTIONS` from `mindmapStyle` |

### Why it's debt

`DiagramTypePlugin` (`src/tarseem/families/base.py`) exposes `layouter_factory`, `svg_renderer`,
`default_shape`, etc., but **no field to declare ELK layout options or a post-layout hook**. So a
family that uses ELK (rather than a full custom `layouter_factory`) but needs non-default ELK
options or a cleanup pass has nowhere to put that config except hardcoded in the core adapter. A
new ELK-based family with the same need would require editing core — the exact thing invariant 8
and F9 forbid.

This was deferred deliberately (ADR-008 "Costs/ceilings"): external clones reuse layered ELK +
the generic renderer, so F9 passed without it. It surfaces only when a third party wants to tune
ELK or post-process its output.

### Proposed fix (additive, behavior-preserving)

1. Extend `DiagramTypePlugin` with two optional, declarative fields:
   - `elk_options: Callable[[LogicalGraph], dict] | dict | None` — merged over `_BASE_OPTIONS`
     (carries `elk.algorithm` + spacing; the mindmap plugin derives `mrtree`/`radial` from
     `mindmapStyle`, and omits `elk.direction` for radial).
   - `post_layout: Callable[[PositionedDiagram, LogicalGraph], PositionedDiagram] | None` —
     post-ELK hook (carries `remove_radial_overlaps`).
2. In the ELK adapter, read both via `get_plugin(graph.diagram_type)`; delete the literal
   `"mindmap"` branches. The mindmap built-in (`families/mindmap.py`) declares the options + hook.
3. `_to_elk` can likely unify with `_to_elk_mindmap`: the layered-only machinery (preferred-side
   ports, edge priority, INTERACTIVE) already no-ops when those edge/graph properties are absent,
   which they are for mindmaps — confirm during implementation rather than assuming.

### Acceptance / guards

- [ ] Behavior-preserving: determinism + 3-OS visual-regression baselines **byte-identical** (same
      bar ADR-008/009 held). No `examples/` golden or baseline regen.
- [ ] Add a guard that the ELK adapter contains no `diagram_type == "mindmap"` dispatch branch.
      Note: a blanket grep for the literal `mindmap` across `layout/**` **cannot** reach zero —
      `radial.py` and the `_MRTREE/_RADIAL_OPTIONS` comments legitimately mention it, and `mindmap`
      is a built-in (unlike the *external*-name guard `test_engine_core_never_names_the_external_type`).
      So either scope the assertion to dispatch sites, or relocate `radial.py` into the mindmap
      plugin package as part of the move.
- [ ] `.venv` pytest green; ruff + mypy clean.
- [ ] (Optional, closes a related gap) a 3rd external plugin exercise supplying `elk_options` —
      the `elk_options` axis would then be proven externally. Note `svg_renderer` would still be
      the only declared extension point exercised solely by built-ins.

### Notes

- **Not a schema change.** `DiagramTypePlugin` is a code contract, not the frozen JSON schema
  (ADR-009) — extending it needs no `specVersion` bump or `migrate` step.
- `EDGE_WIDTH_DEFAULT` (a per-family styling table) is a separate, lower-priority ADR-008 ceiling —
  styling data, not dispatch. Track separately if it ever bites.

### References

- ADR-008 — "Costs/ceilings" (first bullet records this coupling)
- `docs/spikes/phase-7-progress.md` — PR1 "Known internal coupling"
- CLAUDE.md — Architecture invariant 8

---

## See also — deferred scope recorded elsewhere (not tech-debt; planned-but-out-of-v1.0)

These are tracked in their canonical locations; listed here only so this register is the single
index of "known not-yet-done."

- **Mermaid + PlantUML source writers** — deferred from Phase 6. See
  `docs/spikes/phase-6-progress.md` "Deferred / future tasks".
- **Searchable-Arabic PDF** — PDF stays visual-only (Acrobat can't multi-word-search a synthetic
  RTL text layer). See the PDF notes under `docs/spikes/`.
- **F10 documentation tooling tail** — mkdocs site structure + auto-generated per-object schema
  reference (content is present; only the site-build tooling is deferred). See the Phase-7
  acceptance audit under `docs/`.
