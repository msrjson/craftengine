"""General Register ID (RG) format and shape validation."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import re
from typing import Any

from ..enums import ErrorCode
from ..schemas import ValidationResult, fail, ok
from .cpf import only_alnum

_RG = re.compile(r"^[0-9]{6,8}[0-9X]$")
RG_MIN_LENGTH = 7
RG_MAX_LENGTH = 9


def mask_rg(chars: str) -> str:
    if len(chars) != RG_MAX_LENGTH:
        return chars
    return f"{chars[:2]}.{chars[2:5]}.{chars[5:8]}-{chars[8:]}"


def validate_rg(value: Any) -> ValidationResult:
    """Check the shape of an RG (7-9 characters: digits with optional trailing X)."""
    raw = str(value or "").strip()
    if not raw:
        return fail("rg", ErrorCode.EMPTY_VALUE)

    chars = only_alnum(raw)
    if not (RG_MIN_LENGTH <= len(chars) <= RG_MAX_LENGTH):
        return fail(
            "rg",
            ErrorCode.INVALID_LENGTH,
            clean=chars,
            expected=f"{RG_MIN_LENGTH}-{RG_MAX_LENGTH}",
            actual=len(chars),
        )
    if not _RG.match(chars):
        return fail("rg", ErrorCode.INVALID_FORMAT, clean=chars)

    return ok("rg", chars, mask_rg(chars))
