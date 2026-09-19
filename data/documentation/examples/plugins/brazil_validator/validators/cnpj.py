"""CNPJ validation for legacy numeric and 2026 Receita Federal Alphanumeric layouts."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import re
from typing import Any, Sequence, Tuple

from ..enums import ErrorCode
from ..schemas import ValidationResult, fail, ok
from .cpf import only_alnum

CNPJ_LENGTH = 14
CNPJ_FIRST_WEIGHTS: Tuple[int, ...] = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
CNPJ_SECOND_WEIGHTS: Tuple[int, ...] = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)

_CNPJ_BODY = re.compile(r"^[0-9A-Z]{12}$")
_CNPJ_CHECK = re.compile(r"^[0-9]{2}$")
_ASCII_ZERO = 48


def _weighted_sum(chars: str, weights: Sequence[int]) -> int:
    return sum((ord(c) - _ASCII_ZERO) * w for c, w in zip(chars, weights))


def _check_digit(chars: str, weights: Sequence[int]) -> int:
    remainder = _weighted_sum(chars, weights) % 11
    return 0 if remainder < 2 else 11 - remainder


def mask_cnpj(chars: str) -> str:
    if len(chars) != CNPJ_LENGTH:
        return chars
    return f"{chars[:2]}.{chars[2:5]}.{chars[5:8]}/{chars[8:12]}-{chars[12:]}"


def validate_cnpj(value: Any) -> ValidationResult:
    """Check a CNPJ in either the legacy numeric or the 2026 alphanumeric layout."""
    raw = str(value or "").strip()
    if not raw:
        return fail("cnpj", ErrorCode.EMPTY_VALUE)

    chars = only_alnum(raw)
    if len(chars) != CNPJ_LENGTH:
        return fail(
            "cnpj",
            ErrorCode.INVALID_LENGTH,
            clean=chars,
            expected=CNPJ_LENGTH,
            actual=len(chars),
        )

    body, checks = chars[:12], chars[12:]
    if not _CNPJ_BODY.match(body) or not _CNPJ_CHECK.match(checks):
        return fail("cnpj", ErrorCode.INVALID_FORMAT, clean=chars)
    if chars == chars[0] * CNPJ_LENGTH:
        return fail("cnpj", ErrorCode.REPEATED_DIGITS, clean=chars)

    version = "numeric" if body.isdigit() else "alphanumeric"

    first = _check_digit(body, CNPJ_FIRST_WEIGHTS)
    if int(checks[0]) != first:
        return fail("cnpj", ErrorCode.INVALID_CHECKSUM, clean=chars, position=1)

    second = _check_digit(body + str(first), CNPJ_SECOND_WEIGHTS)
    if int(checks[1]) != second:
        return fail("cnpj", ErrorCode.INVALID_CHECKSUM, clean=chars, position=2)

    return ok("cnpj", chars, mask_cnpj(chars), version=version)
