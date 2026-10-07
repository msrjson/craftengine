"""The single outcome shape every check in the Brazil validator returns.

A `ValidationResult` never carries user-facing copy: it carries the machine
`error_code`, the `message_key` and the `params` the sentence needs. `message()`
resolves the key through the application's translator, so the copy lives with
every other translation and not in this plugin.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from .errors import ErrorCode

#: Prefix every message key shares, so a project can seed or override the block.
KEY_PREFIX = "validation.brazil"


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Outcome of one validation or normalization call. Immutable, stateless."""

    is_valid: bool
    kind: str
    clean: str = ""
    formatted: Optional[str] = None
    version: Optional[str] = None
    error_code: Optional[ErrorCode] = None
    message_key: str = ""
    params: Mapping[str, Any] = field(default_factory=dict)

    def __bool__(self) -> bool:
        return self.is_valid

    def message(self, locale: Optional[str] = None) -> str:
        """Render `message_key` for the active locale, or "" when there is none."""
        if not self.message_key:
            return ""
        from engine.support.translation import __

        return __(self.message_key, locale=locale, **dict(self.params))


def ok(kind: str, clean: str, formatted: str, version: str = "") -> ValidationResult:
    """A successful check."""
    return ValidationResult(
        is_valid=True,
        kind=kind,
        clean=clean,
        formatted=formatted,
        version=version or None,
    )


def fail(kind: str, code: Any, clean: str = "", **params: Any) -> ValidationResult:
    """A failed check, keyed by `kind` and the machine `code`."""
    code_enum = code if isinstance(code, ErrorCode) else _coerce(code)
    return ValidationResult(
        is_valid=False,
        kind=kind,
        clean=clean,
        error_code=code_enum,
        message_key=f"{KEY_PREFIX}.{kind}.{code_enum.value.lower()}",
        params=dict(params),
    )


def _coerce(code: Any) -> ErrorCode:
    try:
        return ErrorCode(str(code))
    except ValueError:
        return ErrorCode.UNKNOWN_ERROR


__all__ = ["ValidationResult", "KEY_PREFIX", "ok", "fail"]
