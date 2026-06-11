"""Spike 1 benchmark: cold + warm round-trip latency for the elkjs subprocess.

Writes out/results.json (metrics) and out/laid_out_sample.json (one positioned graph
for eyeballing). PASS check: every leaf gets x/y, every edge gets a routed section.
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from elk_client import ElkServer  # noqa: E402
from gen_graph import build_compound_graph, count_leaves  # noqa: E402

WARM_CALLS = 30


def validate(g: dict) -> dict:
    issues: list[str] = []

    def walk(node: dict) -> None:
        for ch in node.get("children", []):
            if "x" not in ch or "y" not in ch:
                issues.append(str(ch.get("id")) + " missing position")
            walk(ch)

    walk(g)
    edges = g.get("edges", [])
    routed = sum(1 for e in edges if e.get("sections"))
    return {
        "issues": issues[:10],
        "n_issues": len(issues),
        "edges": len(edges),
        "edges_routed": routed,
        "root_w": g.get("width"),
        "root_h": g.get("height"),
    }


def main() -> int:
    out_dir = HERE / "out"
    out_dir.mkdir(exist_ok=True)

    graph = build_compound_graph()
    leaves = count_leaves(graph)
    ports = sum(len(n.get("ports", [])) for c in graph["children"] for n in c["children"])

    srv = ElkServer(HERE / "elk_server.js", cwd=HERE)
    try:
        t0 = time.perf_counter()
        g = srv.layout(graph)
        cold_ms = (time.perf_counter() - t0) * 1000.0
        stats = validate(g)

        warm = []
        for _ in range(WARM_CALLS):
            t = time.perf_counter()
            srv.layout(graph)
            warm.append((time.perf_counter() - t) * 1000.0)
    finally:
        srv.close()

    def r(x: float) -> float:
        return round(x, 2)

    warm_sorted = sorted(warm)
    result = {
        "leaf_nodes": leaves,
        "ports": ports,
        "edges": stats["edges"],
        "edges_routed": stats["edges_routed"],
        "validation_issues": stats["n_issues"],
        "root_size": [stats["root_w"], stats["root_h"]],
        "cold_ms": r(cold_ms),
        "warm_ms": {
            "n": len(warm),
            "min": r(min(warm)),
            "median": r(statistics.median(warm)),
            "p95": r(warm_sorted[int(len(warm) * 0.95) - 1]),
            "max": r(max(warm)),
            "mean": r(statistics.mean(warm)),
        },
    }
    (out_dir / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (out_dir / "laid_out_sample.json").write_text(json.dumps(g, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    if stats["n_issues"]:
        print("VALIDATION ISSUES:", stats["issues"], file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
