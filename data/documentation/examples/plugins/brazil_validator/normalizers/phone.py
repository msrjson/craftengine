"""Brazilian phone number normalization (landlines and mobile)."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from typing import Any

from ..enums import ErrorCode
from ..schemas import ValidationResult, fail, ok
from ..validators.cpf import only_digits

LANDLINE_LENGTH = 10
MOBILE_LENGTH = 11
COUNTRY_CODE = "55"

AREA_CODES = frozenset(
    {
        "11",
        "12",
        "13",
        "14",
        "15",
        "16",
        "17",
        "18",
        "19",
        "21",
        "22",
        "24",
        "27",
        "28",
        "31",
        "32",
        "33",
        "34",
        "35",
        "37",
        "38",
        "41",
        "42",
        "43",
        "44",
        "45",
        "46",
        "47",
        "48",
        "49",
        "51",
        "53",
        "54",
        "55",
        "61",
        "62",
        "63",
        "64",
        "65",
        "66",
        "67",
        "68",
        "69",
        "71",
        "73",
        "74",
        "75",
        "77",
        "79",
        "81",
        "82",
        "83",
        "84",
        "85",
        "86",
        "87",
        "88",
        "89",
        "91",
        "92",
        "93",
        "94",
        "95",
        "96",
        "97",
        "98",
        "99",
    }
)


def normalize_phone(value: Any, country_code: bool = True) -> ValidationResult:
    """Normalize Brazilian phone: 10 digits for landline, 11 for mobile."""
    raw = str(value or "").strip()
    if not raw:
        return fail("phone", ErrorCode.EMPTY_VALUE)

    digits = only_digits(raw)
    if digits.startswith(COUNTRY_CODE) and len(digits) in (
        LANDLINE_LENGTH + 2,
        MOBILE_LENGTH + 2,
    ):
        digits = digits[2:]

    if len(digits) not in (LANDLINE_LENGTH, MOBILE_LENGTH):
        return fail(
            "phone",
            ErrorCode.INVALID_LENGTH,
            clean=digits,
            expected=f"{LANDLINE_LENGTH} / {MOBILE_LENGTH}",
            actual=len(digits),
        )

    area, subscriber = digits[:2], digits[2:]
    if area not in AREA_CODES:
        return fail("phone", ErrorCode.INVALID_FORMAT, clean=digits, area_code=area)

    mobile = len(digits) == MOBILE_LENGTH
    if mobile and not subscriber.startswith("9"):
        return fail("phone", ErrorCode.INVALID_FORMAT, clean=digits, area_code=area)
    if not mobile and subscriber[0] in "019":
        return fail("phone", ErrorCode.INVALID_FORMAT, clean=digits, area_code=area)

    split = 5 if mobile else 4
    formatted = f"({area}) {subscriber[:split]}-{subscriber[split:]}"
    clean = f"{COUNTRY_CODE}{digits}" if country_code else digits

    return ok("phone", clean, formatted, version="mobile" if mobile else "landline")
