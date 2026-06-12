"""libavoid post-placement re-router (ADR-006) — OPTIONAL + EXPERIMENTAL.

Re-routes the edges of an already-placed ``PositionedDiagram`` with the vendored libavoid
WASM (LGPL-2.1), leaving node geometry untouched. Off by default; opted in per-spec via
``layout.router: "libavoid"``. Its value is obstacle avoidance on fixed/manual layouts; it
is *worse than ELK for auto-layout* (ADR-006). Adaptagrams' object model never leaves this
module: the WASM server returns plain routed points, we splice them into the IR.
"""
from __future__ import annotations

import functools
import json
import subprocess
import threading
from pathlib import Path
from types import TracebackType

from tarseem.model.ir import LogicalGraph, PositionedDiagram, PositionedEdge, replace

__all__ = ["LibavoidRouter", "libavoid_available", "VENDOR_DIR"]

_HERE = Path(__file__).resolve().parent
_SERVER_MJS = _HERE / "libavoid_server.mjs"
VENDOR_DIR = _HERE.parent.parent / "_vendor" / "libavoid-js" / "dist"
_GLUE = VENDOR_DIR / "index-node.mjs"
_WASM = VENDOR_DIR / "libavoid.wasm"

# default routing knobs (px). Buffer keeps connectors clear of obstacle shapes.
_SHAPE_BUFFER = 12.0
_NUDGE = 6.0


def libavoid_available() -> bool:
    """True when the vendored WASM bundle + Node glue are present (Node checked on spawn)."""
    return _WASM.exists() and _GLUE.exists() and _SERVER_MJS.exists()


@functools.lru_cache(maxsize=1)
def _libavoid_version() -> str:
    pkg = VENDOR_DIR.parent / "package.json"
    try:
        return json.loads(pkg.read_text(encoding="utf-8")).get("version", "unknown")
    except OSError:
        return "unknown"


class _LibavoidServer:
    """Long-lived ``node libavoid_server.mjs`` subprocess. Serializes route requests."""

    def __init__(self, node: str = "node") -> None:
        if not libavoid_available():
            raise FileNotFoundError(
                f"vendored libavoid WASM missing under {VENDOR_DIR}; run `engine doctor`"
            )
        self._proc = subprocess.Popen(
            [node, str(_SERVER_MJS), _GLUE.as_uri(), str(_WASM)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", bufsize=1,
        )
        self._id = 0
        self._stderr: list[str] = []
        threading.Thread(target=self._drain, daemon=True).start()
        ready = self._proc.stdout.readline() if self._proc.stdout else ""
        if not ready:
            raise RuntimeError("libavoid server failed to start; stderr:\n" + self._err())

    def _drain(self) -> None:
        assert self._proc.stderr is not None
        for line in self._proc.stderr:
            self._stderr.append(line.rstrip("\n"))

    def _err(self) -> str:
        return "\n".join(self._stderr)

    def route(self, payload: dict) -> dict:
        assert self._proc.stdin is not None and self._proc.stdout is not None
        self._id += 1
        rid = self._id
        self._proc.stdin.write(json.dumps({"id": rid, "route": payload}) + "\n")
        self._proc.stdin.flush()
        line = self._proc.stdout.readline()
        if not line:
            raise RuntimeError("libavoid server closed stdout; stderr:\n" + self._err())
        resp = json.loads(line)
        if not resp.get("ok"):
            raise RuntimeError("libavoid error: " + str(resp.get("error")))
        return resp

    def close(self) -> None:
        try:
            if self._proc.stdin:
                self._proc.stdin.close()
            self._proc.wait(timeout=5)
        except Exception:
            self._proc.kill()


def _polyline_midpoint(points: tuple[tuple[float, float], ...]) -> tuple[float, float]:
    if len(points) < 2:
        return points[0] if points else (0.0, 0.0)
    segs = [(points[i], points[i + 1]) for i in range(len(points) - 1)]
    total = sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in segs)
    half = total / 2
    for a, b in segs:
        seg = abs(a[0] - b[0]) + abs(a[1] - b[1])
        if seg >= half:
            t = half / seg if seg else 0.0
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        half -= seg
    return points[len(points) // 2]


class LibavoidRouter:
    """Context-managed re-router. Spawns one WASM subprocess for its lifetime."""

    def __init__(self, node: str = "node") -> None:
        self._node = node
        self._server: _LibavoidServer | None = None

    def __enter__(self) -> LibavoidRouter:
        self._server = _LibavoidServer(node=self._node)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._server is not None:
            self._server.close()
            self._server = None

    def capabilities(self) -> dict:
        return {
            "engine": "libavoid",
            "version": _libavoid_version(),
            "role": "post-placement re-router (optional, experimental)",
            "supports": {"orthogonal_edges": True, "obstacle_avoidance": True},
        }

    def reroute(self, graph: LogicalGraph, diagram: PositionedDiagram) -> PositionedDiagram:
        """Re-route ``diagram``'s edges around its nodes with libavoid; geometry of nodes,
        lanes, phases and markers is preserved. Edge connectivity comes from ``graph``
        (a ``PositionedEdge`` carries no source/target)."""
        if self._server is None:
            raise RuntimeError("LibavoidRouter must be used as a context manager")
        if not diagram.edges:
            return diagram

        nodes = [{"id": n.id, "x": n.x, "y": n.y, "width": n.width, "height": n.height}
                 for n in diagram.nodes]
        edges = [{"id": e.id, "source": e.source, "target": e.target} for e in graph.edges]
        resp = self._server.route({
            "nodes": nodes, "edges": edges,
            "options": {"shapeBufferDistance": _SHAPE_BUFFER, "idealNudgingDistance": _NUDGE},
        })
        routed = {e["id"]: tuple((float(p[0]), float(p[1])) for p in e["points"])
                  for e in resp.get("edges", [])}

        new_edges: list[PositionedEdge] = []
        for e in diagram.edges:
            pts = routed.get(e.id)
            if pts is None or len(pts) < 2:
                new_edges.append(e)  # libavoid dropped it -> keep the original route
                continue
            label_xy = _polyline_midpoint(pts) if e.label and e.label.text else None
            new_edges.append(replace(e, points=pts, label_xy=label_xy))
        return replace(diagram, edges=tuple(new_edges))
