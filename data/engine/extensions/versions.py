"""Version ranges for extension manifests, standard library only.

A range is a comma-separated list of clauses, every one of which must hold:
`>=4.3,<5`, `==1.2.0`, `>1`, `!=2.0`. An empty range accepts every version.
Versions are dotted integers; missing parts count as zero, so `4.3` equals
`4.3.0`. Pre-release tags are not part of the model.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import operator
import re
from collections.abc import Callable

from engine.extensions.errors import ExtensionError

_CLAUSE = re.compile(r"^(>=|<=|==|!=|>|<)?\s*(\d+(?:\.\d+)*)$")
_OPERATORS: dict[str, Callable[[tuple[int, ...], tuple[int, ...]], bool]] = {
    ">=": operator.ge,
    "<=": operator.le,
    "==": operator.eq,
    "!=": operator.ne,
    ">": operator.gt,
    "<": operator.lt,
}


def parse_version(version: str) -> tuple[int, ...]:
    """Return `version` as a comparable tuple of three integers or more.

    Raises:
        ExtensionError: `EXTENSION_VERSION_INVALID` when it is not dotted integers.
    """
    if not re.fullmatch(r"\d+(?:\.\d+)*", version.strip()):
        raise ExtensionError("EXTENSION_VERSION_INVALID", detail=version)
    parts = tuple(int(part) for part in version.strip().split("."))
    return parts + (0,) * (3 - len(parts)) if len(parts) < 3 else parts


def check_range(spec: str) -> None:
    """Validate a range without evaluating it, so a manifest fails at discovery.

    Raises:
        ExtensionError: `EXTENSION_VERSION_RANGE_INVALID` for a malformed clause.
    """
    for clause in _clauses(spec):
        if not _CLAUSE.match(clause):
            raise ExtensionError("EXTENSION_VERSION_RANGE_INVALID", detail=spec)


def satisfies(version: str, spec: str) -> bool:
    """Return whether `version` lies inside the range `spec`.

    Raises:
        ExtensionError: The version or the range is malformed.
    """
    check_range(spec)
    current = parse_version(version)
    for clause in _clauses(spec):
        match = _CLAUSE.match(clause)
        symbol = (match.group(1) if match else None) or "=="
        if not _OPERATORS[symbol](current, parse_version(match.group(2) if match else "0")):
            return False
    return True


def _clauses(spec: str) -> list[str]:
    """Split a range into its non-empty clauses."""
    return [clause.strip() for clause in (spec or "").split(",") if clause.strip()]


__all__ = ["check_range", "parse_version", "satisfies"]
