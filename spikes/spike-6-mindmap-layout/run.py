"""Spike 6 — mindmap ELK algorithm validation (mrtree vs radial). THROWAWAY.

Drives the *production* pinned elkjs 0.11.1 bundle through the production
``ElkServerProcess`` with ``elk.algorithm`` = ``mrtree`` then ``radial``, on TWO
mindmap graphs (a balanced tree + a wide, uneven fan-out with a deep chain).

For each (graph, algorithm) it records the objective spike criteria:
  1. RUNS   — executes through the real subprocess without an ELK error.
  2. OVERLAP— count of overlapping node bounding boxes (mindmap wants 0).
  3. DETERMINISTIC — identical rounded coordinates across a *fresh subprocess
                     spawn* (matches invariant 7: "same spec ⇒ identical output
                     across renders", where every render spawns a new process —
                     NOT two layout() calls on one warm process).
  4. EDGE SECTIONS — dumps what ELK returns for edge routing under each algo, so
                     we surface NOW whether the mindmap family needs its own edge
                     router (like sequence/lanegrid) vs. ELK's sections.

It also renders a debug PNG per (graph, algorithm) — raw ELK boxes + straight
centre-to-centre edges — purely to JUDGE PLACEMENT SHAPE for the owner's
mrtree-vs-radial pick (there is no mindmap visual oracle in the plan; the default
is a recommendation for sign-off, not a self-certified fact).

No writes under ``src/``. Run with the project venv:
    .venv/Scripts/python.exe spikes/spike-6-mindmap-layout/run.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

# the spike imports the PRODUCTION adapter internals — that is the whole point:
# whatever drives here is exactly what a real render would drive.
from tarseem.export import svg_to_png
from tarseem.layout.elk._server import ElkServerProcess, vendored_bundle

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)


# ---- representative mindmap inputs -------------------------------------------
def _est_size(label: str) -> tuple[float, float]:
    """A cheap, deterministic size estimate (overlap detection doesn't need exact
    shaped advances; the spike tests placement, not text metrics)."""
    return (max(70.0, 14.0 + 8.5 * len(label)), 36.0)


# A: balanced mindmap — root, 4 main branches, 2-3 leaves each (15 nodes).
MINDMAP_BALANCED: list[tuple[str, str]] = [
    ("Tarseem", "Layout"), ("Tarseem", "Render"),
    ("Tarseem", "Export"), ("Tarseem", "Schema"),
    ("Layout", "ELK"), ("Layout", "Sequence"), ("Layout", "Lanegrid"),
    ("Render", "SVG"), ("Render", "Text"),
    ("Export", "drawio"), ("Export", "pptx"), ("Export", "pdf"),
    ("Schema", "validate"), ("Schema", "compile"),
]

# B: wide, uneven fan-out — root with 10 children + one deep chain + a couple of
# 2-leaf sub-trees. Lopsided trees are where overlap / root-detection fails.
MINDMAP_UNEVEN: list[tuple[str, str]] = (
    [("Root", f"C{i}") for i in range(1, 11)]
    + [("C1", "C1a"), ("C1a", "C1b"), ("C1b", "C1c")]  # deep chain
    + [("C2", "C2a"), ("C2", "C2b")]
    + [("C3", "C3a")]
)

GRAPHS = {"balanced": MINDMAP_BALANCED, "uneven": MINDMAP_UNEVEN}

# per-algorithm option dicts — NOT the layered-specific _BASE_OPTIONS, so an
# overlap is a real failure, not a config artifact (advisor note).
ALGOS = {
    "mrtree": {
        "elk.algorithm": "mrtree",
        "elk.direction": "RIGHT",  # horizontal tree reads like a classic mind map
        "elk.spacing.nodeNode": "40",
        "elk.mrtree.spacing.nodeNode": "40",
    },
    "radial": {
        "elk.algorithm": "radial",
        "elk.spacing.nodeNode": "40",
    },
}


def _nodes_and_edges(edge_list: list[tuple[str, str]]) -> tuple[list[dict], list[dict]]:
    ids: list[str] = []
    for s, t in edge_list:
        for n in (s, t):
            if n not in ids:
                ids.append(n)
    children = []
    for nid in ids:
        w, h = _est_size(nid)
        children.append({"id": nid, "width": w, "height": h})
    edges = [
        {"id": f"e{i}", "sources": [s], "targets": [t]}
        for i, (s, t) in enumerate(edge_list)
    ]
    return children, edges


def _build(edge_list: list[tuple[str, str]], options: dict) -> dict:
    children, edges = _nodes_and_edges(edge_list)
    return {"id": "root", "layoutOptions": options, "children": children, "edges": edges}


# ---- run + measure -----------------------------------------------------------
def _layout_fresh(graph: dict) -> dict:
    """One layout on a freshly-spawned, then torn-down, subprocess (the render path)."""
    proc = ElkServerProcess()
    try:
        return proc.layout(graph)
    finally:
        proc.close()


def _coord_hash(laid: dict) -> str:
    rows = sorted(
        (c["id"], round(c.get("x", 0.0), 3), round(c.get("y", 0.0), 3),
         round(c.get("width", 0.0), 3), round(c.get("height", 0.0), 3))
        for c in laid.get("children", [])
    )
    return hashlib.sha256(json.dumps(rows).encode()).hexdigest()[:16]


def _overlap_count(laid: dict) -> int:
    boxes = [
        (c["id"], c.get("x", 0.0), c.get("y", 0.0), c.get("width", 0.0), c.get("height", 0.0))
        for c in laid.get("children", [])
    ]
    n = 0
    for i in range(len(boxes)):
        _, ax, ay, aw, ah = boxes[i]
        for j in range(i + 1, len(boxes)):
            _, bx, by, bw, bh = boxes[j]
            if ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah:
                n += 1
    return n


def _edge_section_summary(laid: dict) -> dict:
    edges = laid.get("edges", [])
    routed = sum(1 for e in edges if e.get("sections"))
    bends = [len(s.get("bendPoints", []) or [])
             for e in edges for s in (e.get("sections") or [])]
    sample = next((e.get("sections") for e in edges if e.get("sections")), None)
    return {
        "edges": len(edges),
        "with_sections": routed,
        "total_bendpoints": sum(bends),
        "sample_section": sample[0] if sample else None,
    }


# ---- debug render (placement judgement only) ---------------------------------
def _debug_svg(laid: dict, title: str) -> str:
    children = laid.get("children", [])
    edges = laid.get("edges", [])
    centre = {c["id"]: (c.get("x", 0.0) + c.get("width", 0.0) / 2,
                        c.get("y", 0.0) + c.get("height", 0.0) / 2)
              for c in children}
    pad = 30.0
    w = laid.get("width") or (max((c.get("x", 0.0) + c.get("width", 0.0) for c in children),
                                  default=0.0))
    h = laid.get("height") or (max((c.get("y", 0.0) + c.get("height", 0.0) for c in children),
                                   default=0.0))
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w + 2 * pad:.0f}" '
        f'height="{h + 2 * pad:.0f}" viewBox="{-pad} {-pad} {w + 2 * pad} {h + 2 * pad}">',
        '<rect x="-9999" y="-9999" width="99999" height="99999" fill="#ffffff"/>',
        f'<text x="0" y="-10" font-family="sans-serif" font-size="13" fill="#888">{title}</text>',
    ]
    for e in edges:  # straight centre-to-centre (judging PLACEMENT, not ELK routing)
        s = centre.get(e["sources"][0])
        t = centre.get(e["targets"][0])
        if s and t:
            parts.append(f'<line x1="{s[0]:.1f}" y1="{s[1]:.1f}" x2="{t[0]:.1f}" '
                         f'y2="{t[1]:.1f}" stroke="#b0b8c4" stroke-width="1.5"/>')
    for c in children:
        x, y = c.get("x", 0.0), c.get("y", 0.0)
        cw, ch = c.get("width", 0.0), c.get("height", 0.0)
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{cw:.1f}" height="{ch:.1f}" rx="6" '
            f'fill="#e8f0fe" stroke="#3b6fb0" stroke-width="1.5"/>'
            f'<text x="{x + cw / 2:.1f}" y="{y + ch / 2 + 4:.1f}" text-anchor="middle" '
            f'font-family="sans-serif" font-size="12" fill="#14281d">{c["id"]}</text>'
        )
    parts.append("</svg>")
    return "\n".join(parts)


def main() -> int:
    print(f"vendored bundle: {vendored_bundle()}  exists={vendored_bundle().exists()}")
    rows = []
    for gname, edge_list in GRAPHS.items():
        for aname, options in ALGOS.items():
            tag = f"{gname}/{aname}"
            graph = _build(edge_list, options)
            try:
                laid = _layout_fresh(graph)
            except Exception as exc:  # an algorithm that errors IS a finding
                print(f"[FAIL] {tag}: {exc}")
                rows.append((tag, "ERROR", "-", "-", str(exc)[:60]))
                continue
            laid2 = _layout_fresh(_build(edge_list, options))  # fresh spawn -> determinism
            h1, h2 = _coord_hash(laid), _coord_hash(laid2)
            overlaps = _overlap_count(laid)
            esum = _edge_section_summary(laid)
            det = "YES" if h1 == h2 else f"NO ({h1}!={h2})"
            dims = f"{laid.get('width', 0):.0f}x{laid.get('height', 0):.0f}"
            print(f"[ok]   {tag}: dims={dims} overlaps={overlaps} det={det} "
                  f"edges={esum['with_sections']}/{esum['edges']} routed, "
                  f"bends={esum['total_bendpoints']}")
            svg = _debug_svg(laid, tag)
            (OUT / f"{gname}-{aname}.svg").write_text(svg, encoding="utf-8")
            try:
                svg_to_png(svg, OUT / f"{gname}-{aname}.png")
            except Exception as exc:
                print(f"       [warn] png render failed: {exc}")
            rows.append((tag, "RUNS", str(overlaps), det, json.dumps(esum)))

    (OUT / "summary.json").write_text(
        json.dumps([dict(zip(["case", "status", "overlaps", "deterministic", "detail"], r))
                    for r in rows], indent=2),
        encoding="utf-8",
    )
    print(f"\nartifacts: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
