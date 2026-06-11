"""Long-lived Node/elkjs subprocess client (ADR-002).

Internal to the layout adapter. Speaks newline-delimited JSON to ``elk_server.js``,
serializing requests. The pinned bundle path is passed as argv so Node never resolves
``node_modules``. ELK's JSON dialect lives only behind this boundary.
"""
from __future__ import annotations

import json
import subprocess
import threading
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SERVER_JS = _HERE / "elk_server.js"
_BUNDLE = _HERE.parent.parent / "_vendor" / "elkjs" / "lib" / "elk.bundled.js"


def vendored_bundle() -> Path:
    return _BUNDLE


class ElkServerProcess:
    """Spawns ``node elk_server.js <bundle>`` once and reuses it per layout() call."""

    def __init__(self, node: str = "node") -> None:
        if not _BUNDLE.exists():
            raise FileNotFoundError(
                f"vendored elkjs bundle missing at {_BUNDLE}; run `engine doctor`"
            )
        self._proc = subprocess.Popen(
            [node, str(_SERVER_JS), str(_BUNDLE)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        self._id = 0
        self._stderr_lines: list[str] = []
        threading.Thread(target=self._drain_stderr, daemon=True).start()

    def _drain_stderr(self) -> None:
        assert self._proc.stderr is not None
        for line in self._proc.stderr:
            self._stderr_lines.append(line.rstrip("\n"))

    def layout(self, graph: dict) -> dict:
        assert self._proc.stdin is not None and self._proc.stdout is not None
        self._id += 1
        rid = self._id
        self._proc.stdin.write(
            json.dumps({"id": rid, "graph": graph}, ensure_ascii=False) + "\n"
        )
        self._proc.stdin.flush()
        line = self._proc.stdout.readline()
        if not line:
            raise RuntimeError(
                "elk server closed stdout unexpectedly; stderr:\n"
                + "\n".join(self._stderr_lines)
            )
        resp = json.loads(line)
        if resp.get("id") != rid:
            raise RuntimeError(f"response id mismatch: sent {rid} got {resp.get('id')}")
        if not resp.get("ok"):
            raise RuntimeError("elk error: " + str(resp.get("error")))
        return resp["graph"]

    def close(self) -> None:
        try:
            if self._proc.stdin:
                self._proc.stdin.close()
            self._proc.wait(timeout=5)
        except Exception:
            self._proc.kill()
