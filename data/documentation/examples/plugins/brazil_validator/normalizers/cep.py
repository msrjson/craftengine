"""Postal Code (CEP) normalization."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from typing import Any

from ..enums import ErrorCode
from ..schemas import ValidationResult, fail, ok
from ..validators.cpf import only_digits

CEP_LENGTH = 8


def normalize_cep(value: Any) -> ValidationResult:
    """Normalize eight-digit Brazilian postal code into 00000-000 mask."""
    raw = str(value or "").strip()
    if not raw:
        return fail("cep", ErrorCode.EMPTY_VALUE)

    digits = only_digits(raw)
    if any(c.isalpha() for c in raw):
        return fail("cep", ErrorCode.INVALID_FORMAT, clean=digits)
    if len(digits) != CEP_LENGTH:
        return fail(
            "cep",
            ErrorCode.INVALID_LENGTH,
            clean=digits,
            expected=CEP_LENGTH,
            actual=len(digits),
        )

    return ok("cep", digits, f"{digits[:5]}-{digits[5:]}")
