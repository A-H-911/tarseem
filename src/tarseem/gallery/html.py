"""Static HTML templates for the gallery (no framework, openable from disk).

Deliberately styled — a green technical/editorial identity matching the diagram palette,
card hover states, monospace metrics — not a default grid. All dynamic values are escaped.
"""
from __future__ import annotations

import html

__all__ = ["page", "index_card", "detail_body", "INDEX_CSS"]

INDEX_CSS = """
:root{--bg:#f4f7f5;--surface:#ffffff;--ink:#14281d;--muted:#5d7066;
--accent:#2e8b57;--accent-deep:#1f6b41;--line:#dce5e0;--radius:14px}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
header.masthead{padding:48px 40px 28px;border-bottom:1px solid var(--line);
background:linear-gradient(180deg,#ffffff,transparent)}
.masthead h1{margin:0;font-size:30px;letter-spacing:-.02em}
.masthead p{margin:6px 0 0;color:var(--muted);max-width:60ch}
.wrap{padding:32px 40px 64px;max-width:1280px;margin:0 auto}
.grid{display:grid;gap:22px;grid-template-columns:repeat(auto-fill,minmax(320px,1fr))}
.card{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);
overflow:hidden;text-decoration:none;color:inherit;display:flex;flex-direction:column;
transition:transform .18s cubic-bezier(.16,1,.3,1),box-shadow .18s}
.card:hover{transform:translateY(-4px);box-shadow:0 12px 30px rgba(20,40,29,.12)}
.thumb{background:#fbfdfc;border-bottom:1px solid var(--line);padding:16px;
height:200px;display:flex;align-items:center;justify-content:center;overflow:hidden}
.thumb svg{max-width:100%;max-height:100%;height:auto}
.meta{padding:14px 16px}
.meta h2{margin:0 0 6px;font-size:17px}
.tags{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
.tag{font:11px/1 ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--accent-deep);
background:#e8f3ee;border:1px solid #cfe6da;border-radius:999px;padding:5px 9px}
.tag.bad{color:#a3261d;background:#fbeae8;border-color:#f0c8c2}
.detail{padding:32px 40px 64px;max-width:1080px;margin:0 auto}
.detail a.back{color:var(--accent-deep);text-decoration:none;font-weight:600}
.stage{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);
padding:20px;margin:20px 0;overflow:auto}
table.metrics{border-collapse:collapse;font:13px/1.4 ui-monospace,Menlo,monospace}
table.metrics td{border:1px solid var(--line);padding:7px 12px}
table.metrics td:first-child{color:var(--muted)}
pre.spec{background:#11211a;color:#d8efe3;border-radius:var(--radius);padding:18px;
overflow:auto;font:12.5px/1.5 ui-monospace,Menlo,monospace}
.downloads a{display:inline-block;margin-right:12px;color:var(--accent-deep);font-weight:600}
""".strip()


def _e(s: str) -> str:
    return html.escape(str(s), quote=True)


def page(title: str, body: str) -> str:
    return (
        "<!doctype html>\n"
        f'<html lang="en"><head><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{_e(title)}</title><style>{INDEX_CSS}</style></head>"
        f"<body>{body}</body></html>\n"
    )


def index_card(name: str, title: str, family: str, thumb_svg: str, tags: list[str],
               ok: bool) -> str:
    tag_html = "".join(f'<span class="tag">{_e(t)}</span>' for t in tags)
    if not ok:
        tag_html = '<span class="tag bad">render failed</span>' + tag_html
    thumb = thumb_svg if ok else "<em>no render</em>"
    return (
        f'<a class="card" href="{_e(name)}.html">'
        f'<div class="thumb">{thumb}</div>'
        f'<div class="meta"><h2>{_e(title)}</h2>'
        f'<div class="tags"><span class="tag">{_e(family)}</span>{tag_html}</div>'
        f"</div></a>"
    )


def detail_body(name: str, title: str, family: str, svg: str, spec_json: str,
                metrics: dict, downloads: list[tuple[str, str]], error: str | None) -> str:
    rows = "".join(
        f"<tr><td>{_e(k)}</td><td>{_e(v)}</td></tr>" for k, v in metrics.items()
    )
    dl = "".join(f'<a href="{_e(href)}">{_e(label)}</a>' for label, href in downloads)
    if error:
        stage = f'<div class="stage"><strong>Render failed:</strong> {_e(error)}</div>'
    else:
        stage = f'<div class="stage">{svg}</div>'
    return (
        f'<div class="detail"><a class="back" href="index.html">&larr; gallery</a>'
        f"<h1>{_e(title)}</h1>"
        f'<div class="tags"><span class="tag">{_e(family)}</span></div>'
        f"{stage}"
        f"<h3>Metrics</h3><table class=\"metrics\">{rows}</table>"
        f'<h3>Downloads</h3><div class="downloads">{dl}</div>'
        f"<h3>Spec</h3><pre class=\"spec\">{_e(spec_json)}</pre>"
        f"</div>"
    )
