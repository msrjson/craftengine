"""CPF, CNPJ and RG — shape, check digits and display masks.

CPF and the legacy CNPJ are Modulo 11 over digits; the 2026 CNPJ is the same
arithmetic over the first twelve alphanumeric characters (the weights read each
character as its ASCII value minus the code of `"0"`). RG has no national check
digit, so only its shape is verified.
"""

from __future__ import annotations

import re
from typing import Any, Sequence, Tuple

from .errors import ErrorCode
from .schemas import ValidationResult, fail, ok

CPF_LENGTH = 11
CNPJ_LENGTH = 14
RG_MIN_LENGTH = 7
RG_MAX_LENGTH = 9

_ASCII_ZERO = ord("0")
_CNPJ_BODY = re.compile(r"^[0-9A-Z]{12}$")
_CNPJ_CHECK = re.compile(r"^[0-9]{2}$")
_RG = re.compile(r"^[0-9]{6,8}[0-9X]$")

#: Weights for the first and second CNPJ check digit.
_CNPJ_FIRST_WEIGHTS: Tuple[int, ...] = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
_CNPJ_SECOND_WEIGHTS: Tuple[int, ...] = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)


def only_digits(value: Any) -> str:
    """Keep the decimal digits of `value`."""
    return "".join(c for c in str(value or "") if c.isdigit())


def only_alnum(value: Any) -> str:
    """Keep letters and digits of `value`, uppercased."""
    return "".join(c for c in str(value or "") if c.isalnum()).upper()


def mask_cpf(digits: str) -> str:
    """Display mask `000.000.000-00`, or the input when it is not 11 digits."""
    if len(digits) != CPF_LENGTH:
        return digits
    return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"


def mask_cnpj(chars: str) -> str:
    """Display mask `00.000.000/0000-00`, or the input when it is not 14 chars."""
    if len(chars) != CNPJ_LENGTH:
        return chars
    return f"{chars[:2]}.{chars[2:5]}.{chars[5:8]}/{chars[8:12]}-{chars[12:]}"


def mask_rg(chars: str) -> str:
    """Display mask `00.000.000-0`, or the input when it is not 9 characters."""
    if len(chars) != RG_MAX_LENGTH:
        return chars
    return f"{chars[:2]}.{chars[2:5]}.{chars[5:8]}-{chars[8:]}"


def validate_cpf(value: Any) -> ValidationResult:
    """Check a CPF: 11 digits, no repeated sequence, both check digits."""
    raw = str(value or "").strip()
    if not raw:
        return fail("cpf", ErrorCode.EMPTY_VALUE)

    digits = only_digits(raw)
    if only_alnum(raw) != digits:
        return fail("cpf", ErrorCode.INVALID_FORMAT, clean=digits)
    if len(digits) != CPF_LENGTH:
        return fail("cpf", ErrorCode.INVALID_LENGTH, clean=digits, expected=CPF_LENGTH, actual=len(digits))
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


def _weighted_sum(chars: str, weights: Sequence[int]) -> int:
    return sum((ord(c) - _ASCII_ZERO) * w for c, w in zip(chars, weights))


def _cnpj_check_digit(chars: str, weights: Sequence[int]) -> int:
    remainder = _weighted_sum(chars, weights) % 11
    return 0 if remainder < 2 else 11 - remainder


def validate_cnpj(value: Any) -> ValidationResult:
    """Check a CNPJ in either the legacy numeric or the 2026 alphanumeric layout."""
    raw = str(value or "").strip()
    if not raw:
        return fail("cnpj", ErrorCode.EMPTY_VALUE)

    chars = only_alnum(raw)
    if len(chars) != CNPJ_LENGTH:
        return fail("cnpj", ErrorCode.INVALID_LENGTH, clean=chars, expected=CNPJ_LENGTH, actual=len(chars))

    body, check = chars[:12], chars[12:]
    if not (_CNPJ_BODY.match(body) and _CNPJ_CHECK.match(check)):
        return fail("cnpj", ErrorCode.INVALID_FORMAT, clean=chars)
    if chars == chars[0] * CNPJ_LENGTH:
        return fail("cnpj", ErrorCode.REPEATED_DIGITS, clean=chars)

    version = "numeric" if body.isdigit() else "alphanumeric"

    first = _cnpj_check_digit(body, _CNPJ_FIRST_WEIGHTS)
    if int(check[0]) != first:
        return fail("cnpj", ErrorCode.INVALID_CHECKSUM, clean=chars, position=1)

    second = _cnpj_check_digit(body + str(first), _CNPJ_SECOND_WEIGHTS)
    if int(check[1]) != second:
        return fail("cnpj", ErrorCode.INVALID_CHECKSUM, clean=chars, position=2)

    return ok("cnpj", chars, mask_cnpj(chars), version=version)


def validate_rg(value: Any) -> ValidationResult:
    """Check the shape of an RG: 7-9 characters, digits with optional trailing X."""
    raw = str(value or "").strip()
    if not raw:
        return fail("rg", ErrorCode.EMPTY_VALUE)

    chars = only_alnum(raw)
    if not (RG_MIN_LENGTH <= len(chars) <= RG_MAX_LENGTH):
        return fail(
            "rg", ErrorCode.INVALID_LENGTH, clean=chars,
            expected=f"{RG_MIN_LENGTH}-{RG_MAX_LENGTH}", actual=len(chars),
        )
    if not _RG.match(chars):
        return fail("rg", ErrorCode.INVALID_FORMAT, clean=chars)

    return ok("rg", chars, mask_rg(chars))


__all__ = [
    "CPF_LENGTH", "CNPJ_LENGTH", "RG_MIN_LENGTH", "RG_MAX_LENGTH",
    "only_digits", "only_alnum", "mask_cpf", "mask_cnpj", "mask_rg",
    "validate_cpf", "validate_cnpj", "validate_rg",
]
