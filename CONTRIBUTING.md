# Contributing to Tarseem

Thanks for your interest! Tarseem is a schema-driven diagram engine with a small set of
non-negotiable architecture invariants. This guide covers setup, the dev loop, and what a PR needs
to land.

## Development setup

Requires **Python ≥ 3.10** and **Node.js** (the ELK layout engine runs in a Node subprocess; the
elkjs bundle is vendored and pinned — you don't install it).

```bash
git clone https://github.com/A-H-911/tarseem.git
cd tarseem
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
playwright install chromium                        # needed for PNG / PDF / visual tests
tarseem doctor                                     # verify Node, pinned elkjs, Chromium, fonts
```

`tarseem doctor` must pass before you start — it checks every runtime dependency with an
actionable hint on failure.

## The dev loop

| Command | Purpose |
|---|---|
| `pytest` | Full suite (schema / unit / adapter-contract / render-golden / E2E / visual) |
| `pytest --cov=tarseem --cov-report=term-missing --cov-fail-under=80` | Coverage gate (CI uses this) |
| `ruff check .` | Lint (line length 100; rules `E,F,I,UP,B`) |
| `ruff check --fix .` | Auto-fix lint + import order |
| `mypy` | Type check |
| `tarseem gallery --examples examples -o build/gallery` | Build the HTML gallery |
| `python -m build` | Build sdist + wheel |

CI runs all of the above on **Windows, macOS, and Linux × Python 3.10 / 3.12**. **No PR merges with
red CI.**

## Architecture invariants (read before large changes)

Tarseem holds eight invariants (see [`README.md`](README.md#architecture) and
[`CLAUDE.md`](CLAUDE.md)). **Changing one requires a new ADR** in [`docs/adr/`](docs/adr/). The most
load-bearing for contributors:

- **One positioned IR, many writers** — no writer computes its own layout.
- **Determinism** — the same spec produces byte-identical output. Never put wall-clock timestamps or
  environment-specific data in artifacts; use content-addressed provenance only.
- **Capability reports, never silent drops** — every export writer returns a `CapabilityReport`
  declaring what it carried and what it dropped.
- **Schema is frozen at v1.0** (ADR-009). Specs use `specVersion: "1.0"`; don't make
  breaking schema changes without a version bump + migration (`tarseem migrate`).
- **Agent surface stability** — `generate()` returns the documented `{ok, svg, report, errors…}`
  JSON contract; the error shape is `{code, path, message, hint}`. Don't break it.

## Adding a diagram type

Diagram types are **entry-point plugins** — you do **not** edit the core to add one. Follow
[`docs/extending/clone-a-type.md`](docs/extending/clone-a-type.md); see the two worked examples in
[`examples/plugins/`](examples/plugins/). A guard test ensures the core never names your type.

## Testing & visual baselines

- Every new feature lands with a **golden sample** in [`examples/`](examples/), rendered into the
  gallery (per `docs/plan/09-testing-gallery-strategy.md`).
- Screenshot baselines are **OS-specific** (`tests/baselines/<platform>/`). They change **only via an
  explicit, reviewed PR**. Regenerate per-OS via the `baselines.yml` workflow (`workflow_dispatch`) —
  never hand-edit baseline PNGs.
- Prefer behavior-focused tests; name them by the behavior under test.

## Submitting a PR

1. Branch from `main`; keep changes small and reviewable.
2. **Conventional commits** (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`, `perf:`, `ci:`).
3. Before opening the PR, confirm locally: `ruff check .` ✓ · `mypy` ✓ · `pytest` (coverage ≥ 80%) ✓.
4. New export feature? Make sure its `CapabilityReport` is honest. New invariant-affecting change?
   Add the ADR.
5. Open the PR against `main` and wait for the 3-OS × 2-Python matrix to go green.

## License

By contributing you agree your contributions are licensed under the project's
[Apache-2.0](LICENSE) license.
