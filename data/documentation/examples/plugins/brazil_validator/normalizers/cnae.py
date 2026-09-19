"""CNAE (economic activity code) normalization."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from typing import Any, List

from ..enums import ErrorCode
from ..schemas import ValidationResult, fail, ok
from ..validators.cpf import only_digits

CNAE_LENGTH = 7


def normalize_cnae(value: Any) -> ValidationResult:
    """Normalize 7-digit economic activity code to 0000-0/00."""
    raw = str(value or "").strip()
    if not raw:
        return fail("cnae", ErrorCode.EMPTY_VALUE)

    digits = only_digits(raw)
    if any(c.isalpha() for c in raw):
        return fail("cnae", ErrorCode.INVALID_FORMAT, clean=digits)
    if len(digits) != CNAE_LENGTH:
        return fail(
            "cnae",
            ErrorCode.INVALID_LENGTH,
            clean=digits,
            expected=CNAE_LENGTH,
            actual=len(digits),
        )

    return ok("cnae", digits, f"{digits[:4]}-{digits[4]}/{digits[5:]}")


def normalize_cnae_list(value: Any) -> List[str]:
    """Parse, validate, and deduplicate list of CNAE codes."""
    if isinstance(value, (list, tuple, set)):
        pieces = [str(v) for v in value]
    else:
        pieces = str(value or "").replace(";", ",").replace("\n", ",").split(",")

    masked: List[str] = []
    for piece in pieces:
        if not piece.strip():
            continue
        result = normalize_cnae(piece)
        if result.is_valid and result.formatted not in masked:
            masked.append(result.formatted)
    return masked
