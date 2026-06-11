"""Spike 3 (MVP-gating): swimlane via lane-grid placement + Tarseem's own SVG renderer.

Reproduces reference-1 (Bug Triage, LTR 4 lanes) and reference-3 (Pipeline, LTR 3 lanes,
full shape set + UML markers + dashed + back-edge). Placement ports the proven lane-grid
from the local horizontal-swimlane-diagram skill (one step per column = topological number,
lanes = fixed rows). Routing is a from-scratch orthogonal router exploiting the
one-step-per-column property so vertical segments stay in single-node columns and
horizontal segments ride node-free rows.

Also probes ELK `partitioning` (via the spike-1 subprocess) to show numerically that
partitions group along the FLOW axis (phases), not the LANE axis -> lane-grid is the path.
"""
from __future__ import annotations

import base64
import io
import json
import sys
from collections import defaultdict, deque
from pathlib import Path

import uharfbuzz as hb
from fontTools import subset
from fontTools.ttLib import TTFont
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
FONT = HERE.parent / "assets" / "fonts" / "Cairo-VF.ttf"
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT / "spikes" / "spike-1-elk"))

# ---- geometry constants (from the skill's DEFAULT_LAYOUT) -------------------
M = 20
TITLE_H = 50
LABEL_W = 160
LANE_H = 120
STEP_W = 150
STEP_H = 70
COL_GAP = 40
LABEL_GAP = 30
MARKER = 36
END_W = 80
TRAIL = 80

PALETTE = [
    {"row": "#E4F8F1", "box": "#C8F0E0", "label": "#269973"},  # green
    {"row": "#FFE8D6", "box": "#FFD4B0", "label": "#D97706"},  # orange
    {"row": "#E8F0FF", "box": "#D0E0FF", "label": "#1976D2"},  # blue
    {"row": "#FFF3CD", "box": "#FFE69C", "label": "#A06600"},  # yellow
]
PRIMARY = "#269973"
EDGE_DEFAULT = "#2e8b57"

# ---- specs (match the reference images) -------------------------------------
BUG_TRIAGE = {
    "title": "Bug Triage",
    "markers": False,
    "lanes": [
        {"id": "rep", "label": "Reporter"},
        {"id": "tri", "label": "Triage Engineer"},
        {"id": "dev", "label": "Developer"},
        {"id": "qa", "label": "QA"},
    ],
    "steps": [
        {"id": "report", "lane": "rep", "label": "Bug report", "shape": "stadium", "badge": False},
        {"id": "classify", "lane": "tri", "label": "Classify", "shape": "roundrect"},
        {"id": "realbug", "lane": "tri", "label": "Real bug?", "shape": "diamond"},
        {"id": "fix", "lane": "dev", "label": "Fix", "shape": "roundrect"},
        {"id": "verify", "lane": "qa", "label": "Verify", "shape": "diamond"},
        {"id": "close", "lane": "tri", "label": "Close", "shape": "stadium", "badge": False},
    ],
    "edges": [
        {"from": "report", "to": "classify"},
        {"from": "classify", "to": "realbug"},
        {"from": "realbug", "to": "close", "label": "no"},
        {"from": "realbug", "to": "fix", "label": "yes"},
        {"from": "fix", "to": "verify"},
        {"from": "verify", "to": "fix", "label": "fails"},
        {"from": "verify", "to": "close", "label": "passes"},
    ],
}

PIPELINE = {
    "title": "Pipeline",
    "markers": True,
    "lanes": [
        {"id": "user", "label": "User"},
        {"id": "sys", "label": "System"},
        {"id": "stor", "label": "Storage"},
    ],
    "steps": [
        {"id": "upload", "lane": "user", "label": "Upload", "shape": "parallelogram"},
        {"id": "validate", "lane": "sys", "label": "Validate?", "shape": "diamond"},
        {"id": "process", "lane": "sys", "label": "Process", "shape": "roundrect"},
        {"id": "save", "lane": "stor", "label": "Save", "shape": "cylinder"},
        {"id": "receipt", "lane": "user", "label": "Receipt", "shape": "document"},
    ],
    "edges": [
        {"from": "upload", "to": "validate"},
        {"from": "validate", "to": "process", "label": "ok"},
        {"from": "validate", "to": "upload", "label": "bad"},
        {"from": "process", "to": "save", "label": "async", "dashed": True},
        {"from": "save", "to": "receipt"},
    ],
}

# ---- font embedding ---------------------------------------------------------
_blob = hb.Blob.from_file_path(str(FONT))
_face = hb.Face(_blob)


def woff2_datauri(all_text: str) -> str:
    chars = {c for c in all_text if not c.isspace()}
    ttf = TTFont(str(FONT))
    ss = subset.Subsetter()
    ss.populate(unicodes=[ord(c) for c in chars])
    ss.subset(ttf)
    ttf.flavor = "woff2"
    b = io.BytesIO()
    ttf.save(b)
    return base64.b64encode(b.getvalue()).decode("ascii")


# ---- topological column assignment (ported from the skill) ------------------
def topo_numbers(steps, edges):
    indeg = {s["id"]: 0 for s in steps}
    succ = defaultdict(list)
    for e in edges:
        succ[e["from"]].append(e["to"])
        indeg[e["to"]] += 1
    declared = {s["id"]: i for i, s in enumerate(steps)}
    q = deque(sorted([sid for sid, d in indeg.items() if d == 0], key=lambda x: declared[x]))
    order, seen = [], set()
    while q:
        sid = q.popleft()
        order.append(sid)
        seen.add(sid)
        for nb in sorted(succ[sid], key=lambda x: declared[x]):
            indeg[nb] -= 1
            if indeg[nb] == 0:
                q.append(nb)
    if len(order) != len(steps):  # cycle -> declared order
        order = [s["id"] for s in steps]
    return {sid: i + 1 for i, sid in enumerate(order)}


def layout(spec):
    lanes = spec["lanes"]
    steps = spec["steps"]
    nums = topo_numbers(steps, spec["edges"])
    n_cols = max(nums.values())
    markers = spec.get("markers", False)
    end_w = END_W if markers else 0
    inner_w = n_cols * STEP_W + (n_cols - 1) * COL_GAP
    total_w = M + LABEL_W + LABEL_GAP + end_w + inner_w + end_w + TRAIL + M
    total_h = M + TITLE_H + len(lanes) * LANE_H + M

    lane_rows = {}
    for i, lane in enumerate(lanes):
        lane_rows[lane["id"]] = {
            "i": i, "y": M + TITLE_H + i * LANE_H, "label": lane["label"], "c": PALETTE[i % len(PALETTE)],
        }

    def col_x(col):
        return M + LABEL_W + LABEL_GAP + end_w + (col - 1) * (STEP_W + COL_GAP)

    pos = {}
    for s in steps:
        row = lane_rows[s["lane"]]
        col = nums[s["id"]]
        pos[s["id"]] = {
            "x": col_x(col), "y": row["y"] + (LANE_H - STEP_H) / 2, "w": STEP_W, "h": STEP_H,
            "col": col, "n": nums[s["id"]], "lane_i": row["i"], "c": row["c"],
            "shape": s.get("shape", "roundrect"), "label": s["label"], "badge": s.get("badge", True),
        }

    first = min(nums, key=nums.get)
    last = max(nums, key=nums.get)
    return {
        "total_w": total_w, "total_h": total_h, "lane_rows": lane_rows, "pos": pos,
        "n_cols": n_cols, "markers": markers, "end_w": end_w, "col_x": col_x,
        "first": first, "last": last,
    }


# ---- SVG shapes -------------------------------------------------------------
def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def shape_svg(p):
    x, y, w, h = p["x"], p["y"], p["w"], p["h"]
    fill, stroke = p["c"]["box"], p["c"]["label"]
    st = f'fill="{fill}" stroke="{stroke}" stroke-width="2"'
    kind = p["shape"]
    if kind == "stadium":
        return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h/2}" {st}/>'
    if kind == "roundrect":
        return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" {st}/>'
    if kind == "diamond":
        cx, cy = x + w / 2, y + h / 2
        return f'<polygon points="{cx},{y} {x+w},{cy} {cx},{y+h} {x},{cy}" {st}/>'
    if kind == "parallelogram":
        s = 20
        return f'<polygon points="{x+s},{y} {x+w},{y} {x+w-s},{y+h} {x},{y+h}" {st}/>'
    if kind == "cylinder":
        ry = 9
        body = (f'<path d="M {x} {y+ry} A {w/2} {ry} 0 0 1 {x+w} {y+ry} '
                f'L {x+w} {y+h-ry} A {w/2} {ry} 0 0 1 {x} {y+h-ry} Z" {st}/>')
        top = f'<path d="M {x} {y+ry} A {w/2} {ry} 0 0 0 {x+w} {y+ry}" fill="none" stroke="{stroke}" stroke-width="2"/>'
        return body + top
    if kind == "document":
        wv = 14
        return (f'<path d="M {x} {y} L {x+w} {y} L {x+w} {y+h-wv} '
                f'Q {x+3*w/4} {y+h} {x+w/2} {y+h-wv/2} T {x} {y+h-wv} Z" {st}/>')
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" {st}/>'


def anchors(p):
    x, y, w, h = p["x"], p["y"], p["w"], p["h"]
    return {"cx": x + w / 2, "cy": y + h / 2, "l": x, "r": x + w, "t": y, "b": y + h}


def route(a, b):
    """Orthogonal polyline exploiting one-step-per-column. Returns list of (x,y)."""
    A, B = anchors(a), anchors(b)
    if a["lane_i"] == b["lane_i"]:  # same lane -> straight horizontal at center y
        if B["cx"] > A["cx"]:
            return [(A["r"], A["cy"]), (B["l"], A["cy"])]
        return [(A["l"], A["cy"]), (B["r"], A["cy"])]
    # different lane: vertical in A's column, then horizontal at B center y into B
    exit_y = A["t"] if B["cy"] < A["cy"] else A["b"]
    enter_x = B["l"] if B["cx"] >= A["cx"] else B["r"]
    return [(A["cx"], exit_y), (A["cx"], B["cy"]), (enter_x, B["cy"])]


def path_midpoint(pts):
    """Point at half the cumulative orthogonal length (true middle, not an endpoint)."""
    segs = [(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    total = sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in segs)
    half = total / 2
    for a, b in segs:
        seg_len = abs(a[0] - b[0]) + abs(a[1] - b[1])
        if seg_len >= half:
            t = half / seg_len if seg_len else 0
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        half -= seg_len
    return pts[len(pts) // 2]


def arrowhead(p1, p2, color):
    (x1, y1), (x2, y2) = p1, p2
    sz = 9
    if abs(x2 - x1) > abs(y2 - y1):  # horizontal
        d = 1 if x2 > x1 else -1
        pts = f"{x2},{y2} {x2-d*sz},{y2-sz*0.6} {x2-d*sz},{y2+sz*0.6}"
    else:  # vertical
        d = 1 if y2 > y1 else -1
        pts = f"{x2},{y2} {x2-sz*0.6},{y2-d*sz} {x2+sz*0.6},{y2-d*sz}"
    return f'<polygon points="{pts}" fill="{color}"/>'


def render_svg(spec, b64):
    g = layout(spec)
    W, H = g["total_w"], g["total_h"]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" viewBox="0 0 {W:.0f} {H:.0f}">',
        "<style>",
        f"@font-face{{font-family:'CairoSpike';src:url(data:font/woff2;base64,{b64}) format('woff2');}}",
        "text{font-family:'CairoSpike';}",
        "</style>",
        f'<rect width="{W:.0f}" height="{H:.0f}" fill="#ffffff"/>',
    ]
    # title bar
    parts.append(f'<rect x="{M}" y="{M}" width="{W-2*M:.0f}" height="{TITLE_H}" rx="6" fill="{PRIMARY}"/>')
    parts.append(f'<text x="{W/2:.0f}" y="{M+TITLE_H/2:.0f}" font-size="18" font-weight="700" fill="#fff" '
                 f'text-anchor="middle" dominant-baseline="central">{esc(spec["title"])}</text>')
    # lane bands + header chips
    for lane_id, row in g["lane_rows"].items():
        c = row["c"]
        parts.append(f'<rect x="{M}" y="{row["y"]}" width="{W-2*M:.0f}" height="{LANE_H}" '
                     f'fill="{c["row"]}" stroke="{c["label"]}" stroke-width="1" opacity="0.85"/>')
        chip_h, chip_w = 56, LABEL_W - 16
        chip_x, chip_y = M + 8, row["y"] + (LANE_H - chip_h) / 2
        parts.append(f'<rect x="{chip_x}" y="{chip_y:.0f}" width="{chip_w}" height="{chip_h}" rx="8" fill="{c["label"]}"/>')
        parts.append(f'<text x="{chip_x+chip_w/2:.0f}" y="{chip_y+chip_h/2:.0f}" font-size="13" font-weight="700" '
                     f'fill="#fff" text-anchor="middle" dominant-baseline="central">{esc(row["label"])}</text>')
    # separator
    sep_x = M + LABEL_W + 2
    parts.append(f'<line x1="{sep_x}" y1="{M+TITLE_H}" x2="{sep_x}" y2="{M+TITLE_H+len(spec["lanes"])*LANE_H}" '
                 f'stroke="#B0BEC5" stroke-width="2"/>')

    # UML markers
    if g["markers"]:
        fp = g["pos"][g["first"]]
        lp = g["pos"][g["last"]]
        sx = M + LABEL_W + LABEL_GAP + (END_W - MARKER) / 2
        sy = fp["y"] + (STEP_H - MARKER) / 2
        parts.append(f'<circle cx="{sx+MARKER/2:.0f}" cy="{sy+MARKER/2:.0f}" r="{MARKER/2}" fill="#000"/>')
        ex = W - M - TRAIL - END_W + (END_W - MARKER) / 2
        ey = lp["y"] + (STEP_H - MARKER) / 2
        parts.append(f'<circle cx="{ex+MARKER/2:.0f}" cy="{ey+MARKER/2:.0f}" r="{MARKER/2}" fill="#fff" stroke="#000" stroke-width="2"/>')
        parts.append(f'<circle cx="{ex+MARKER/2:.0f}" cy="{ey+MARKER/2:.0f}" r="{MARKER*0.27:.1f}" fill="#000"/>')
        # marker edges
        parts.append(f'<line x1="{sx+MARKER:.0f}" y1="{sy+MARKER/2:.0f}" x2="{fp["x"]:.0f}" y2="{fp["y"]+STEP_H/2:.0f}" stroke="#000" stroke-width="2"/>')
        parts.append(arrowhead((sx + MARKER, sy + MARKER / 2), (fp["x"], fp["y"] + STEP_H / 2), "#000"))
        parts.append(f'<line x1="{lp["x"]+STEP_W:.0f}" y1="{lp["y"]+STEP_H/2:.0f}" x2="{ex:.0f}" y2="{ey+MARKER/2:.0f}" stroke="#000" stroke-width="2"/>')
        parts.append(arrowhead((lp["x"] + STEP_W, lp["y"] + STEP_H / 2), (ex, ey + MARKER / 2), "#000"))

    # edges (draw before nodes so arrowheads tuck at borders)
    edge_layer = []
    by_id = g["pos"]
    for e in spec["edges"]:
        a, b = by_id[e["from"]], by_id[e["to"]]
        color = e.get("color", EDGE_DEFAULT)
        pts = route(a, b)
        dash = ' stroke-dasharray="6 4"' if e.get("dashed") else ""
        poly = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)
        edge_layer.append(f'<polyline points="{poly}" fill="none" stroke="{color}" stroke-width="2"{dash}/>')
        edge_layer.append(arrowhead(pts[-2], pts[-1], color))
        if e.get("label"):
            lx, ly = path_midpoint(pts)
            edge_layer.append(f'<rect x="{lx-16:.0f}" y="{ly-10:.0f}" width="32" height="16" fill="#ffffff" opacity="0.9"/>')
            edge_layer.append(f'<text x="{lx:.0f}" y="{ly:.0f}" font-size="12" fill="{color}" '
                              f'text-anchor="middle" dominant-baseline="central">{esc(e["label"])}</text>')
    parts.extend(edge_layer)

    # nodes + badges + labels
    for sid, p in g["pos"].items():
        parts.append(shape_svg(p))
        if p["badge"]:
            parts.append(f'<text x="{p["x"]+10:.0f}" y="{p["y"]+15:.0f}" font-size="12" font-weight="700" '
                         f'fill="{p["c"]["label"]}" text-anchor="start">{p["n"]}.</text>')
        parts.append(f'<text x="{p["x"]+p["w"]/2:.0f}" y="{p["y"]+p["h"]/2:.0f}" font-size="12" fill="#14281d" '
                     f'text-anchor="middle" dominant-baseline="central">{esc(p["label"])}</text>')

    parts.append("</svg>")
    return "\n".join(parts), g


def rasterize(svg, name):
    html = f"<!doctype html><meta charset='utf-8'><body style='margin:0'>{svg}</body>"
    hp = OUT / f"{name}.html"
    hp.write_text(html, encoding="utf-8")
    (OUT / f"{name}.svg").write_text(svg, encoding="utf-8")
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(device_scale_factor=2)
        pg.goto(hp.as_uri())
        pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(250)
        pg.query_selector("svg").screenshot(path=str(OUT / f"{name}.png"))
        b.close()


# ---- ELK partitioning probe (reuse spike-1 subprocess) ----------------------
def elk_partition_probe():
    from elk_client import ElkServer  # noqa

    steps = BUG_TRIAGE["steps"]
    lane_idx = {l["id"]: i for i, l in enumerate(BUG_TRIAGE["lanes"])}
    children = [{
        "id": s["id"], "width": STEP_W, "height": STEP_H,
        "layoutOptions": {"elk.partitioning.partition": str(lane_idx[s["lane"]])},
    } for s in steps]
    edges = [{"id": f"e{i}", "sources": [e["from"]], "targets": [e["to"]]}
             for i, e in enumerate(BUG_TRIAGE["edges"])]
    graph = {
        "id": "root",
        "layoutOptions": {"elk.algorithm": "layered", "elk.direction": "RIGHT",
                          "elk.partitioning.activate": "true"},
        "children": children, "edges": edges,
    }
    srv = ElkServer(ROOT / "spikes" / "spike-1-elk" / "elk_server.js", cwd=ROOT / "spikes" / "spike-1-elk")
    try:
        g = srv.layout(graph)
    finally:
        srv.close()
    by = {c["id"]: c for c in g["children"]}
    rows = []
    for s in steps:
        c = by[s["id"]]
        rows.append({"id": s["id"], "lane": s["lane"], "partition": lane_idx[s["lane"]],
                     "x": round(c["x"], 1), "y": round(c["y"], 1)})
    part_to_x = defaultdict(set)
    part_to_y = defaultdict(set)
    for r in rows:
        part_to_x[r["partition"]].add(r["x"])
        part_to_y[r["partition"]].add(r["y"])
    x_banded = all(len(v) == 1 for v in part_to_x.values())
    y_banded = all(len(v) == 1 for v in part_to_y.values())
    return {"rows": rows, "partition_groups_by_x": x_banded, "partition_groups_by_y": y_banded}


def main():
    all_text = ""
    for spec in (BUG_TRIAGE, PIPELINE):
        all_text += spec["title"]
        all_text += "".join(s["label"] for s in spec["steps"])
        all_text += "".join(l["label"] for l in spec["lanes"])
        all_text += "".join(e.get("label", "") for e in spec["edges"])
    all_text += "0123456789."
    b64 = woff2_datauri(all_text)

    for spec, name in ((BUG_TRIAGE, "bug_triage"), (PIPELINE, "pipeline")):
        svg, g = render_svg(spec, b64)
        rasterize(svg, name)
        print(f"{name}: {g['n_cols']} cols, {len(spec['lanes'])} lanes, "
              f"size {g['total_w']:.0f}x{g['total_h']:.0f} -> out/{name}.png")

    probe = elk_partition_probe()
    (OUT / "elk_probe.json").write_text(json.dumps(probe, indent=2), encoding="utf-8")
    print("\nELK partitioning probe (Bug Triage nodes, partition = lane index):")
    print(f"  partition groups by X (flow/phase axis): {probe['partition_groups_by_x']}")
    print(f"  partition groups by Y (lane axis):        {probe['partition_groups_by_y']}")
    print("  => partitioning controls the FLOW axis, not lanes." if probe["partition_groups_by_x"]
          else "  => unexpected; inspect elk_probe.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
