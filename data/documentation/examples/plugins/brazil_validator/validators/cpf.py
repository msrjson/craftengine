"""Individual Taxpayer Register (CPF) validation using Modulo 11 arithmetic."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from typing import Any

from ..enums import ErrorCode
from ..schemas import ValidationResult, fail, ok

CPF_LENGTH = 11


def only_digits(value: Any) -> str:
    return "".join(c for c in str(value or "") if c.isdigit())


def only_alnum(value: Any) -> str:
    return "".join(c for c in str(value or "") if c.isalnum()).upper()


def mask_cpf(digits: str) -> str:
    if len(digits) != CPF_LENGTH:
        return digits
    return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"


def validate_cpf(value: Any) -> ValidationResult:
    """Check a CPF: 11 digits, no repeated sequence, both check digits."""
    raw = str(value or "").strip()
    if not raw:
        return fail("cpf", ErrorCode.EMPTY_VALUE)

    digits = only_digits(raw)
    if only_alnum(raw) != digits:
        return fail("cpf", ErrorCode.INVALID_FORMAT, clean=digits)
    if len(digits) != CPF_LENGTH:
        return fail(
            "cpf",
            ErrorCode.INVALID_LENGTH,
            clean=digits,
            expected=CPF_LENGTH,
            actual=len(digits),
        )
    if digits == digits[0] * CPF_LENGTH:
        return fail("cpf", ErrorCode.REPEATED_DIGITS, clean=digits)

    for position, upto in ((1, 9), (2, 10)):
        total = sum(int(digits[i]) * (upto + 1 - i) for i in range(upto))
        expected = (total * 10) % 11
        if expected == 10:
            expected = 0
        if int(digits[upto]) != expected:
            return fail("cpf", ErrorCode.INVALID_CHECKSUM, clean=digits, position=position)

    return ok("cpf", digits, mask_cpf(digits))
