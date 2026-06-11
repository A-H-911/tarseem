"""Deterministically build a compound ELK graph with ports (spike 1).

5 containers x 10 leaves = 50 leaf nodes; every leaf has a WEST input port and an
EAST output port (FIXED_ORDER). Edges chain leaves inside a container and link each
container last leaf to the next container first leaf -- cross-hierarchy edges declared
at root, resolved by INCLUDE_CHILDREN. No randomness: same output every run.
"""
from __future__ import annotations

NODE_W, NODE_H = 70, 40
PORT_SZ = 8


def build_compound_graph(n_containers: int = 5, per_container: int = 10) -> dict:
    children = []
    edges = []

    for c in range(n_containers):
        leaves = []
        for i in range(per_container):
            nid = f"n{c}_{i}"
            leaves.append(
                {
                    "id": nid,
                    "width": NODE_W,
                    "height": NODE_H,
                    "layoutOptions": {"elk.portConstraints": "FIXED_ORDER"},
                    "ports": [
                        {
                            "id": f"{nid}.in",
                            "width": PORT_SZ,
                            "height": PORT_SZ,
                            "layoutOptions": {"elk.port.side": "WEST"},
                        },
                        {
                            "id": f"{nid}.out",
                            "width": PORT_SZ,
                            "height": PORT_SZ,
                            "layoutOptions": {"elk.port.side": "EAST"},
                        },
                    ],
                }
            )
            if i > 0:
                prev = f"n{c}_{i - 1}"
                edges.append(
                    {"id": f"e_{prev}_{nid}", "sources": [f"{prev}.out"], "targets": [f"{nid}.in"]}
                )
        children.append(
            {
                "id": f"c{c}",
                "layoutOptions": {"elk.padding": "[top=30,left=20,bottom=20,right=20]"},
                "children": leaves,
            }
        )
        if c > 0:
            edges.append(
                {
                    "id": f"e_x_{c}",
                    "sources": [f"n{c - 1}_{per_container - 1}.out"],
                    "targets": [f"n{c}_0.in"],
                }
            )

    return {
        "id": "root",
        "layoutOptions": {
            "elk.algorithm": "layered",
            "elk.direction": "RIGHT",
            "elk.hierarchyHandling": "INCLUDE_CHILDREN",
            "elk.edgeRouting": "ORTHOGONAL",
            "elk.spacing.nodeNode": "30",
            "elk.layered.spacing.nodeNodeBetweenLayers": "40",
        },
        "children": children,
        "edges": edges,
    }


def count_leaves(graph: dict) -> int:
    return sum(len(c.get("children", [])) for c in graph["children"])
