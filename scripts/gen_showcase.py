"""Render a diverse showcase set to out/ (theme variety, complex flows, RTL, sequence).

Throwaway — exercises themes (corporate/monochrome), the full shape set, back-edges,
phases+markers, RTL+theme combos, and a multi-participant sequence. Not committed examples.

Run with the project venv so ``tarseem`` is importable (bare ``python`` raises ModuleNotFoundError):
    .venv/bin/python scripts/gen_showcase.py            # macOS/Linux
    .venv\\Scripts\\python.exe scripts/gen_showcase.py   # Windows
"""
# ruff: noqa: E501 - compact one-line diagram data literals (incl. Arabic) read better unwrapped
from __future__ import annotations

from pathlib import Path

from tarseem.engine import Engine

OUT = Path(__file__).resolve().parent.parent / "out"


def L(text, lang=None):
    return {"text": text, "lang": lang} if lang else {"text": text}


SPECS: dict[str, dict] = {}

# 1. Corporate-themed release pipeline swimlane — phases + markers + decision + back-edge
SPECS["showcase-release-corporate"] = {
    "specVersion": "0.1", "diagramType": "swimlane", "direction": "LR",
    "meta": {"title": "Release Pipeline"},
    "theme": {"ref": "corporate"},
    "layout": {"markers": True},
    "phases": [
        {"id": "build", "label": L("Build")},
        {"id": "test", "label": L("Test")},
        {"id": "deploy", "label": L("Deploy")},
    ],
    "lanes": [
        {"id": "dev", "label": L("Developer")},
        {"id": "ci", "label": L("CI")},
        {"id": "qa", "label": L("QA")},
        {"id": "ops", "label": L("Ops")},
    ],
    "nodes": [
        {"id": "commit", "lane": "dev", "phase": "build", "shape": "stadium", "badge": False, "label": L("Commit")},
        {"id": "compile", "lane": "ci", "phase": "build", "shape": "roundrect", "label": L("Compile")},
        {"id": "unit", "lane": "ci", "phase": "test", "shape": "roundrect", "label": L("Unit tests")},
        {"id": "gate", "lane": "qa", "phase": "test", "shape": "diamond", "label": L("Approve?")},
        {"id": "e2e", "lane": "qa", "phase": "test", "shape": "roundrect", "label": L("E2E suite")},
        {"id": "stage", "lane": "ops", "phase": "deploy", "shape": "cylinder", "label": L("Stage")},
        {"id": "prod", "lane": "ops", "phase": "deploy", "shape": "stadium", "badge": False, "label": L("Production")},
    ],
    "edges": [
        {"id": "a", "source": "commit", "target": "compile"},
        {"id": "b", "source": "compile", "target": "unit"},
        {"id": "c", "source": "unit", "target": "gate"},
        {"id": "d", "source": "gate", "target": "e2e", "label": L("yes")},
        {"id": "e", "source": "gate", "target": "compile", "label": L("rework")},
        {"id": "f", "source": "e2e", "target": "stage"},
        {"id": "g", "source": "stage", "target": "prod", "label": L("ship")},
    ],
}

# 2. Monochrome incident-response swimlane
SPECS["showcase-incident-monochrome"] = {
    "specVersion": "0.1", "diagramType": "swimlane", "direction": "LR",
    "meta": {"title": "Incident Response"},
    "theme": {"ref": "monochrome"},
    "lanes": [
        {"id": "mon", "label": L("Monitoring")},
        {"id": "oncall", "label": L("On-call")},
        {"id": "lead", "label": L("Incident Lead")},
    ],
    "nodes": [
        {"id": "alert", "lane": "mon", "shape": "stadium", "badge": False, "label": L("Alert fires")},
        {"id": "ack", "lane": "oncall", "shape": "roundrect", "label": L("Acknowledge")},
        {"id": "sev", "lane": "lead", "shape": "diamond", "label": L("Sev-1?")},
        {"id": "page", "lane": "lead", "shape": "roundrect", "label": L("Page team")},
        {"id": "mitigate", "lane": "oncall", "shape": "roundrect", "label": L("Mitigate")},
        {"id": "resolve", "lane": "mon", "shape": "stadium", "badge": False, "label": L("Resolved")},
    ],
    "edges": [
        {"id": "a", "source": "alert", "target": "ack"},
        {"id": "b", "source": "ack", "target": "sev"},
        {"id": "c", "source": "sev", "target": "page", "label": L("yes")},
        {"id": "d", "source": "sev", "target": "mitigate", "label": L("no")},
        {"id": "e", "source": "page", "target": "mitigate"},
        {"id": "f", "source": "mitigate", "target": "resolve"},
    ],
}

# 3. Complex flowchart — full shape set + back-edge loop (default theme)
SPECS["showcase-order-flow"] = {
    "specVersion": "0.1", "diagramType": "flowchart", "direction": "TB",
    "meta": {"title": "Order processing"},
    "nodes": [
        {"id": "start", "shape": "stadium", "label": L("New order")},
        {"id": "input", "shape": "parallelogram", "label": L("Read cart")},
        {"id": "stock", "shape": "diamond", "label": L("In stock?")},
        {"id": "pay", "shape": "diamond", "label": L("Payment ok?")},
        {"id": "pack", "shape": "roundrect", "label": L("Pack items")},
        {"id": "db", "shape": "cylinder", "label": L("Save order")},
        {"id": "receipt", "shape": "document", "label": L("Receipt")},
        {"id": "back", "shape": "roundrect", "label": L("Backorder")},
        {"id": "cancel", "shape": "stadium", "label": L("Cancelled")},
        {"id": "done", "shape": "stadium", "label": L("Shipped")},
    ],
    "edges": [
        {"id": "a", "source": "start", "target": "input"},
        {"id": "b", "source": "input", "target": "stock"},
        {"id": "c", "source": "stock", "target": "pay", "label": L("yes")},
        {"id": "d", "source": "stock", "target": "back", "label": L("no")},
        {"id": "e", "source": "back", "target": "stock", "label": L("retry"), "dashed": True},
        {"id": "f", "source": "pay", "target": "pack", "label": L("yes")},
        {"id": "g", "source": "pay", "target": "cancel", "label": L("no")},
        {"id": "h", "source": "pack", "target": "db"},
        {"id": "i", "source": "db", "target": "receipt"},
        {"id": "j", "source": "receipt", "target": "done"},
    ],
}

# 4. Corporate microservice architecture (LR)
SPECS["showcase-architecture-corporate"] = {
    "specVersion": "0.1", "diagramType": "architecture", "direction": "LR",
    "meta": {"title": "Microservices"},
    "theme": {"ref": "corporate"},
    "nodes": [
        {"id": "web", "shape": "roundrect", "label": L("Web app")},
        {"id": "gw", "shape": "roundrect", "label": L("API gateway")},
        {"id": "auth", "shape": "roundrect", "label": L("Auth svc")},
        {"id": "orders", "shape": "roundrect", "label": L("Orders svc")},
        {"id": "cache", "shape": "cylinder", "label": L("Redis")},
        {"id": "db", "shape": "cylinder", "label": L("Postgres")},
        {"id": "queue", "shape": "parallelogram", "label": L("Event bus")},
    ],
    "edges": [
        {"id": "a", "source": "web", "target": "gw"},
        {"id": "b", "source": "gw", "target": "auth"},
        {"id": "c", "source": "gw", "target": "orders"},
        {"id": "d", "source": "orders", "target": "cache", "label": L("read")},
        {"id": "e", "source": "orders", "target": "db", "label": L("write")},
        {"id": "f", "source": "orders", "target": "queue", "label": L("emit"), "dashed": True},
    ],
}

# 5. Complex sequence — multiple participants, self-message, returns
SPECS["showcase-checkout-sequence"] = {
    "specVersion": "0.1", "diagramType": "sequence",
    "meta": {"title": "Checkout"},
    "nodes": [
        {"id": "user", "label": L("User")},
        {"id": "web", "label": L("Web")},
        {"id": "api", "label": L("API")},
        {"id": "pay", "label": L("Payments")},
        {"id": "db", "label": L("DB")},
    ],
    "edges": [
        {"id": "m1", "source": "user", "target": "web", "label": L("Place order")},
        {"id": "m2", "source": "web", "target": "api", "label": L("POST /checkout")},
        {"id": "m3", "source": "api", "target": "api", "label": L("validate cart")},
        {"id": "m4", "source": "api", "target": "pay", "label": L("charge")},
        {"id": "m5", "source": "pay", "target": "api", "label": L("paid"), "dashed": True},
        {"id": "m6", "source": "api", "target": "db", "label": L("persist")},
        {"id": "m7", "source": "db", "target": "api", "label": L("ok"), "dashed": True},
        {"id": "m8", "source": "api", "target": "web", "label": L("201"), "dashed": True},
        {"id": "m9", "source": "web", "target": "user", "label": L("confirmation"), "dashed": True},
    ],
}

# 6. RTL Arabic swimlane under the corporate theme (theme + mirroring combined)
SPECS["showcase-arabic-corporate-rtl"] = {
    "specVersion": "0.1", "diagramType": "swimlane", "direction": "RL",
    "meta": {"title": "طلب إجازة"},
    "theme": {"ref": "corporate"},
    "lanes": [
        {"id": "emp", "label": L("الموظّف", "ar")},
        {"id": "mgr", "label": L("المدير", "ar")},
        {"id": "hr", "label": L("الموارد البشرية", "ar")},
    ],
    "nodes": [
        {"id": "submit", "lane": "emp", "shape": "stadium", "badge": False, "label": L("تقديم الطلب", "ar")},
        {"id": "approve", "lane": "mgr", "shape": "diamond", "label": L("موافقة؟", "ar")},
        {"id": "record", "lane": "hr", "shape": "roundrect", "label": L("تسجيل", "ar")},
        {"id": "reject", "lane": "mgr", "shape": "roundrect", "label": L("رفض", "ar")},
        {"id": "done", "lane": "emp", "shape": "stadium", "badge": False, "label": L("إشعار", "ar")},
    ],
    "edges": [
        {"id": "a", "source": "submit", "target": "approve"},
        {"id": "b", "source": "approve", "target": "record", "label": L("نعم", "ar")},
        {"id": "c", "source": "approve", "target": "reject", "label": L("لا", "ar")},
        {"id": "d", "source": "record", "target": "done"},
    ],
}

# 7. Dependency graph — wider fan-in/out (default theme)
SPECS["showcase-dependency"] = {
    "specVersion": "0.1", "diagramType": "dependency", "direction": "TB",
    "meta": {"title": "Build dependencies"},
    "nodes": [
        {"id": "app", "shape": "roundrect", "label": L("app")},
        {"id": "ui", "shape": "roundrect", "label": L("ui-kit")},
        {"id": "core", "shape": "roundrect", "label": L("core")},
        {"id": "net", "shape": "roundrect", "label": L("net")},
        {"id": "util", "shape": "roundrect", "label": L("utils")},
        {"id": "log", "shape": "roundrect", "label": L("logging")},
    ],
    "edges": [
        {"id": "a", "source": "app", "target": "ui"},
        {"id": "b", "source": "app", "target": "core"},
        {"id": "c", "source": "ui", "target": "core"},
        {"id": "d", "source": "core", "target": "net"},
        {"id": "e", "source": "core", "target": "util"},
        {"id": "f", "source": "net", "target": "util"},
        {"id": "g", "source": "net", "target": "log"},
        {"id": "h", "source": "util", "target": "log"},
    ],
}

# 8. Monochrome auth flowchart (LR)
SPECS["showcase-auth-monochrome"] = {
    "specVersion": "0.1", "diagramType": "flowchart", "direction": "LR",
    "meta": {"title": "Authentication"},
    "theme": {"ref": "monochrome"},
    "nodes": [
        {"id": "start", "shape": "stadium", "label": L("Login")},
        {"id": "creds", "shape": "diamond", "label": L("Valid?")},
        {"id": "mfa", "shape": "diamond", "label": L("MFA?")},
        {"id": "token", "shape": "roundrect", "label": L("Issue token")},
        {"id": "deny", "shape": "roundrect", "label": L("Deny")},
        {"id": "ok", "shape": "stadium", "label": L("Granted")},
    ],
    "edges": [
        {"id": "a", "source": "start", "target": "creds"},
        {"id": "b", "source": "creds", "target": "mfa", "label": L("yes")},
        {"id": "c", "source": "creds", "target": "deny", "label": L("no")},
        {"id": "d", "source": "mfa", "target": "token", "label": L("pass")},
        {"id": "e", "source": "mfa", "target": "deny", "label": L("fail")},
        {"id": "f", "source": "token", "target": "ok"},
    ],
}


def main() -> None:
    OUT.mkdir(exist_ok=True)
    with Engine() as eng:  # reuse one ELK Node session across the batch
        for name, spec in SPECS.items():
            res = eng.render(spec)
            res.export(["png", "svg"], OUT, name)
            r = res.report
            print(f"{name:38} {res.diagram.width:6.0f}x{res.diagram.height:<5.0f} "
                  f"crossings={r.crossings} overlaps={r.overlaps}")


if __name__ == "__main__":
    main()
