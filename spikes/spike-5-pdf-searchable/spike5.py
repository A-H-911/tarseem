"""Spike 5: searchable/selectable Arabic in the PDF export (throwaway, DEFERRED outcome).

Investigates adding an invisible logical-text layer over the canonical PDF so Arabic copies and
searches correctly (Chromium prints shaped Arabic as Type3 visual-order glyphs with no logical
Unicode, so the committed visual-only PDF is not searchable). Outcome: the construction below makes
Arabic **selectable + single-word Ctrl+F search** work in Acrobat, but **multi-word phrase search**
does not (Acrobat rejects/scrambles a synthetic RTL text layer; four glyph layouts were tried). The
feature was DEFERRED — see docs/spikes/spike-5-report.md and the phase-6-progress.md deferred task.

The validated construction (`build_searchable_pdf`):
  * visual base = the canonical SVG with textAsPaths (Chromium then emits NO text layer of its own)
  * text layer  = a self-contained empty-glyph Type3 font + ToUnicode CMap (logical codepoints),
                  drawn render-mode-3 (invisible), Tz-scaled to each measured label box
  * structure   = a Tagged PDF (StructTreeRoot -> per-label /Span + /ActualText + MCID linkage)
  * CTM fix      = wrap the base content in `q ... Q` before appending the overlay, else it inherits
                   Chromium's leftover flip+scale and lands mirrored in a corner (the key bug — see
                   `build_debug_visible`, which renders the overlay VISIBLE to prove placement)
  * determinism  = pikepdf deterministic_id + drop Chromium's wall-clock docinfo dates

Run:  ./.venv/Scripts/python.exe spikes/spike-5-pdf-searchable/spike5.py
Optional deps (spike-only, NOT in pyproject): pikepdf; pdftotext/poppler on PATH for the oracle.
"""
from __future__ import annotations

import io
import json
import math
import re
import shutil
import subprocess
from pathlib import Path

import pikepdf
from pikepdf import Array, Dictionary, Name, String
from playwright.sync_api import sync_playwright

from tarseem import Engine
from tarseem.render.export_opts import apply_export_options

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
REPO = HERE.parent.parent

PX2PT = 0.75          # Chromium prints CSS px at 96dpi -> PDF pt (72/96)
EM = 1000
GLYPH_W = 500         # glyph-space advance per char; Tz then stretches to the visual box width

# measure each <text>'s logical string + box per leaf (tspan else text), with per-glyph sub-boxes
MEASURE_JS = """
() => {
  const out = [];
  document.querySelectorAll('text').forEach(t => {
    const tspans = t.querySelectorAll('tspan');
    const leaves = tspans.length ? Array.from(tspans) : [t];
    const fs = parseFloat(getComputedStyle(t).fontSize);
    const dir = getComputedStyle(t).direction;
    leaves.forEach(el => {
      const s = el.textContent;
      if (!s || !s.trim()) return;
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) return;
      out.push({text: s, x: r.x, y: r.y, w: r.width, h: r.height, fs: fs, dir: dir});
    });
  });
  return out;
}
"""


def _html(svg: str) -> str:
    return ("<!doctype html><meta charset='utf-8'>"
            "<style>html,body{margin:0;padding:0}svg{display:block}</style>"
            f"<body>{svg}</body>")


def render_and_measure(name: str):
    """Render an example, measure label boxes from the <text> SVG, print the visual PDF from the
    textAsPaths SVG (same layout, text -> outlines, so Chromium emits no competing text layer)."""
    spec = json.loads((REPO / f"examples/{name}.json").read_text(encoding="utf-8"))
    svg_measure = Engine().render(spec).to_svg(provenance=True)
    svg_visual = apply_export_options(svg_measure, {"textAsPaths": True})
    m = re.search(r'<svg[^>]*width="([\d.]+)"[^>]*height="([\d.]+)"', svg_measure)
    w, h = math.ceil(float(m.group(1))), math.ceil(float(m.group(2)))
    with sync_playwright() as p:
        b = p.chromium.launch()
        try:
            pg = b.new_page()
            pg.set_content(_html(svg_measure), wait_until="load")
            pg.evaluate("document.fonts.ready")
            pg.wait_for_timeout(200)
            boxes = pg.evaluate(MEASURE_JS)
            pg.set_content(_html(svg_visual), wait_until="load")
            pg.wait_for_timeout(150)
            pdf = pg.pdf(width=f"{w}px", height=f"{h}px",
                         margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
                         print_background=True)
        finally:
            b.close()
    return pdf, boxes, w, h


# ---- Type3 ToUnicode font (self-contained, empty glyphs) ------------------------------------
def _tounicode_cmap(code_to_char: dict[int, str]) -> bytes:
    rows = "\n".join(
        f"<{code:02X}> <{ch.encode('utf-16-be').hex().upper()}>"
        for code, ch in sorted(code_to_char.items())
    )
    cmap = (
        "/CIDInit /ProcSet findresource begin\n12 dict begin\nbegincmap\n"
        "/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def\n"
        "/CMapName /Adobe-Identity-UCS def\n/CMapType 2 def\n"
        "1 begincodespacerange <01> <FF> endcodespacerange\n"
        f"{len(code_to_char)} beginbfchar\n{rows}\nendbfchar\n"
        "endcmap\nCMapName currentdict /CMap defineresource pop\nend\nend"
    )
    return cmap.encode("latin-1")


def _build_type3(pdf, chars: list[str]):
    code_to_char = {i + 1: ch for i, ch in enumerate(chars)}
    char_to_code = {ch: i + 1 for i, ch in enumerate(chars)}
    blank = pdf.make_stream(f"{GLYPH_W} 0 d0\n".encode())  # set width, draw nothing
    charprocs = Dictionary()
    diffs: list = [1]
    for i in range(len(chars)):
        nm = Name(f"/g{i + 1}")
        charprocs[nm] = blank
        diffs.append(nm)
    font = pdf.make_indirect(Dictionary(
        Type=Name.Font, Subtype=Name.Type3,
        FontBBox=Array([0, 0, EM, EM]),
        FontMatrix=Array([1.0 / EM, 0, 0, 1.0 / EM, 0, 0]),
        FirstChar=1, LastChar=len(chars),
        Encoding=Dictionary(Type=Name.Encoding, Differences=Array(diffs)),
        CharProcs=charprocs,
        Widths=Array([GLYPH_W] * len(chars)),
        ToUnicode=pdf.make_stream(_tounicode_cmap(code_to_char)),
    ))
    return font, char_to_code


def _u16(s: str) -> String:
    return String(b"\xfe\xff" + s.encode("utf-16-be"))


def _u16_hex(s: str) -> str:
    return "<" + (b"\xfe\xff" + s.encode("utf-16-be")).hex().upper() + ">"


def _isolate_then_append(pdf, page, overlay: bytes) -> None:
    """Wrap the base content in q..Q so the appended overlay draws at page-default CTM (else it
    inherits Chromium's leftover flip+scale and lands mirrored in a corner)."""
    page.contents_add(pikepdf.Stream(pdf, b"q\n"), prepend=True)
    page.contents_add(pikepdf.Stream(pdf, b"Q\n"))
    page.contents_add(pikepdf.Stream(pdf, overlay))


def build_searchable_pdf(base_pdf: bytes, boxes, w, h) -> bytes:
    """The validated overlay: invisible Type3/ToUnicode text per label, tagged + /ActualText."""
    pdf = pikepdf.open(io.BytesIO(base_pdf))
    page = pdf.pages[0]
    chars = sorted({c for bx in boxes for c in bx["text"]})
    font, c2c = _build_type3(pdf, chars)
    fname = page.add_resource(font, Name.Font, Name("/TsT3"))

    page_h_pt = h * PX2PT
    ops: list[bytes] = [b"q", b"BT", b"3 Tr"]  # render mode 3 = invisible
    for i, bx in enumerate(boxes):
        s = bx["text"]
        size = max(bx["fs"] * PX2PT, 1.0)
        x = bx["x"] * PX2PT
        baseline = page_h_pt - (bx["y"] + bx["h"] * 0.78) * PX2PT
        natural = len(s) * (GLYPH_W / EM) * size
        tz = 100.0 * (bx["w"] * PX2PT) / natural if natural else 100.0
        codes = "".join(f"{c2c[c]:02X}" for c in s)  # logical order (best Acrobat result)
        ops.append(f"/Span <</MCID {i} /ActualText {_u16_hex(s)}>> BDC".encode())
        ops.append(f"{fname} {size:.2f} Tf".encode())
        ops.append(f"{tz:.2f} Tz".encode())
        ops.append(f"1 0 0 1 {x:.2f} {baseline:.2f} Tm".encode())
        ops.append(f"<{codes}> Tj".encode())
        ops.append(b"EMC")
    ops += [b"ET", b"Q"]
    _isolate_then_append(pdf, page, b"\n".join(ops))

    # Tagged-PDF structure: Document -> Span per label (ActualText + MCID), ParentTree linkage
    struct_root = pdf.make_indirect(Dictionary(Type=Name.StructTreeRoot))
    document = pdf.make_indirect(Dictionary(
        Type=Name.StructElem, S=Name.Document, P=struct_root))
    spans = [
        pdf.make_indirect(Dictionary(
            Type=Name.StructElem, S=Name.Span, P=document, Pg=page.obj,
            ActualText=_u16(bx["text"]), K=i))
        for i, bx in enumerate(boxes)
    ]
    document.K = Array(spans)
    struct_root.K = document
    struct_root.ParentTree = pdf.make_indirect(Dictionary(Nums=Array([0, Array(spans)])))
    struct_root.ParentTreeNextKey = 1
    page.obj.StructParents = 0
    pdf.Root.StructTreeRoot = struct_root
    pdf.Root.MarkInfo = Dictionary(Marked=True)

    pdf.docinfo[Name.Producer] = "tarseem"
    pdf.docinfo[Name.Creator] = "tarseem"
    for k in ("/CreationDate", "/ModDate"):  # the date trap: pin via library, not raw-bytes regex
        if k in pdf.docinfo:
            del pdf.docinfo[k]
    out = io.BytesIO()
    pdf.save(out, deterministic_id=True, compress_streams=False)
    return out.getvalue()


def build_debug_visible(base_pdf: bytes, boxes, w, h) -> bytes:
    """Diagnostic: same placement but VISIBLE red text, to prove the overlay lands on the labels
    (this is how the Chromium-CTM mirror bug was found and the q..Q fix verified)."""
    pdf = pikepdf.open(io.BytesIO(base_pdf))
    page = pdf.pages[0]
    helv = pdf.make_indirect(Dictionary(
        Type=Name.Font, Subtype=Name.Type1, BaseFont=Name.Helvetica))
    page.add_resource(helv, Name.Font, Name("/F1"))
    page_h = h * PX2PT
    ops = [b"q", b"BT", b"0 Tr", b"1 0 0 rg", b"/F1 24 Tf",
           f"1 0 0 1 20 {page_h - 30:.1f} Tm".encode(), b"(DEBUG-OVERLAY-VISIBLE) Tj"]
    for bx in boxes:
        size = max(bx["fs"] * PX2PT, 1.0)
        x = bx["x"] * PX2PT
        baseline = page_h - (bx["y"] + bx["h"] * 0.78) * PX2PT
        ops += [f"/F1 {size:.2f} Tf".encode(),
                f"1 0 0 1 {x:.2f} {baseline:.2f} Tm".encode(),
                b"(" + b"X" * max(len(bx["text"]), 1) + b") Tj"]
    ops += [b"ET", b"Q"]
    _isolate_then_append(pdf, page, b"\n".join(ops))
    out = io.BytesIO()
    pdf.save(out)
    return out.getvalue()


# ---- validation -----------------------------------------------------------------------------
def _poppler(path: Path, *mode: str) -> str | None:
    if not shutil.which("pdftotext"):
        return None
    raw = subprocess.run(["pdftotext", "-enc", "UTF-8", *mode, str(path), "-"],
                         capture_output=True).stdout.decode("utf-8")
    return "".join(c for c in raw if c not in "‪‫‬‭‮⁦⁧⁨⁩")


def validate(name: str = "arabic-flowchart") -> None:
    base, boxes, w, h = render_and_measure(name)
    final = build_searchable_pdf(base, boxes, w, h)
    path = OUT / f"{name}-searchable.pdf"
    path.write_bytes(final)
    (OUT / f"{name}-debug-visible.pdf").write_bytes(build_debug_visible(base, boxes, w, h))

    again = build_searchable_pdf(base, boxes, w, h)
    print(f"{name}: boxes={len(boxes)} size={len(final)}")
    print("deterministic (two runs byte-identical):", again == final)
    print("tagged (MarkInfo+StructTreeRoot):",
          b"/Marked true" in final and b"/StructTreeRoot" in final)
    print("no live wall-clock date:", b"D:2026" not in final)

    labels = ["نعم", "بداية", "بيانات صحيحة؟", "دخول ناجح", "رفض الدخول"]
    raw = _poppler(path, "-raw")
    if raw is None:
        print("pdftotext not on PATH — skipping the poppler oracle")
    else:
        # poppler (honors inline /ActualText) reads logical in stream order; Acrobat does NOT
        # honor /ActualText for find/select and only matches single words (see report).
        print("poppler-raw logical found:", {ascii(lab): (lab in raw) for lab in labels})
    print("wrote:", path, "+", OUT / f"{name}-debug-visible.pdf")


if __name__ == "__main__":
    validate()
