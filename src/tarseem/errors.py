"""Shared issue / result model (05 §5).

Every validation or capability problem is a machine-actionable ``Issue`` with a
``{code, path, message, hint}`` shape and a severity. JSON-Pointer paths make
errors agent-repairable (R-28).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Issue:
    code: str
    path: str
    message: str
    hint: str = ""
    severity: str = "error"  # error | warning | info

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "path": self.path,
            "message": self.message,
            "hint": self.hint,
            "severity": self.severity,
        }


@dataclass
class ValidationResult:
    errors: list[Issue]
    warnings: list[Issue]

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
        }


class TarseemError(Exception):
    """Base class for engine-raised errors."""


class SpecValidationError(TarseemError):
    """Raised when an invalid spec is rendered. Carries the structured result."""

    def __init__(self, result: ValidationResult) -> None:
        self.result = result
        first = result.errors[0] if result.errors else None
        detail = f"{first.code} at {first.path}: {first.message}" if first else "invalid spec"
        super().__init__(f"spec validation failed ({len(result.errors)} error(s)) - {detail}")
