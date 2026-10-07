"""Brazilian normalizers: CEP, phone, CNAE and address dictionaries.

Each returns the canonical storage form and the display form. The address helper
canonicalizes the common street-type prefixes so two spellings of the same
street compare equal.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Mapping

from .documents import only_digits
from .errors import ErrorCode
from .schemas import ValidationResult, fail, ok

CEP_LENGTH = 8
CNAE_LENGTH = 7
LANDLINE_LENGTH = 10
MOBILE_LENGTH = 11
COUNTRY_CODE = "55"

#: Every Brazilian area code in service.
AREA_CODES = frozenset(
    {
        "11", "12", "13", "14", "15", "16", "17", "18", "19",
        "21", "22", "24", "27", "28",
        "31", "32", "33", "34", "35", "37", "38",
        "41", "42", "43", "44", "45", "46", "47", "48", "49",
        "51", "53", "54", "55",
        "61", "62", "63", "64", "65", "66", "67", "68", "69",
        "71", "73", "74", "75", "77", "79",
        "81", "82", "83", "84", "85", "86", "87", "88", "89",
        "91", "92", "93", "94", "95", "96", "97", "98", "99",
    }
)

STREET_TYPES = {
    "RUA": "Rua", "R": "Rua",
    "AVENIDA": "Av.", "AV": "Av.", "AVE": "Av.",
    "TRAVESSA": "Trav.", "TRAV": "Trav.", "TV": "Trav.",
    "ALAMEDA": "Al.", "AL": "Al.",
    "PRACA": "Praça", "PCA": "Praça", "PC": "Praça",
    "RODOVIA": "Rod.", "ROD": "Rod.",
    "ESTRADA": "Estr.", "ESTR": "Estr.", "EST": "Estr.",
    "LARGO": "Largo", "LGO": "Largo",
    "VILA": "Vila", "VL": "Vila",
    "CONJUNTO": "Conj.", "CONJ": "Conj.",
    "LOTEAMENTO": "Lot.", "LOT": "Lot.",
    "QUADRA": "Qd.", "QD": "Qd.",
    "RODOANEL": "Rod.",
    "VIELA": "Viela",
    "PASSAGEM": "Pass.", "PASS": "Pass.",
    "SETOR": "Setor", "ST": "Setor",
}

ADDRESS_FIELDS = ("zip", "street", "number", "complement", "neighborhood", "city", "state")

_WHITESPACE = re.compile(r"\s+")
_LEADING_TYPE = re.compile(r"^([A-Za-zÀ-ÿ]+)\.?\s+(.*)$")


def normalize_cep(value: Any) -> ValidationResult:
    """Normalize an eight-digit postal code to the `00000-000` mask."""
    raw = str(value or "").strip()
    if not raw:
        return fail("cep", ErrorCode.EMPTY_VALUE)

    digits = only_digits(raw)
    if any(c.isalpha() for c in raw):
        return fail("cep", ErrorCode.INVALID_FORMAT, clean=digits)
    if len(digits) != CEP_LENGTH:
        return fail("cep", ErrorCode.INVALID_LENGTH, clean=digits, expected=CEP_LENGTH, actual=len(digits))

    return ok("cep", digits, f"{digits[:5]}-{digits[5:]}")


def normalize_phone(value: Any, country_code: bool = True) -> ValidationResult:
    """Normalize a Brazilian phone: 10 digits for a landline, 11 for a mobile."""
    raw = str(value or "").strip()
    if not raw:
        return fail("phone", ErrorCode.EMPTY_VALUE)

    digits = only_digits(raw)
    if digits.startswith(COUNTRY_CODE) and len(digits) in (LANDLINE_LENGTH + 2, MOBILE_LENGTH + 2):
        digits = digits[2:]

    if len(digits) not in (LANDLINE_LENGTH, MOBILE_LENGTH):
        return fail(
            "phone", ErrorCode.INVALID_LENGTH, clean=digits,
            expected=f"{LANDLINE_LENGTH} / {MOBILE_LENGTH}", actual=len(digits),
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


def normalize_cnae(value: Any) -> ValidationResult:
    """Normalize a seven-digit economic activity code to `0000-0/00`."""
    raw = str(value or "").strip()
    if not raw:
        return fail("cnae", ErrorCode.EMPTY_VALUE)

    digits = only_digits(raw)
    if any(c.isalpha() for c in raw):
        return fail("cnae", ErrorCode.INVALID_FORMAT, clean=digits)
    if len(digits) != CNAE_LENGTH:
        return fail("cnae", ErrorCode.INVALID_LENGTH, clean=digits, expected=CNAE_LENGTH, actual=len(digits))

    return ok("cnae", digits, f"{digits[:4]}-{digits[4]}/{digits[5:]}")


def normalize_cnae_list(value: Any) -> List[str]:
    """Parse, validate and deduplicate a list of CNAE codes."""
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


def _collapse(value: Any) -> str:
    return _WHITESPACE.sub(" ", str(value or "").strip())


def _fold(value: str) -> str:
    stripped = unicodedata.normalize("NFKD", value)
    return "".join(c for c in stripped if not unicodedata.combining(c)).upper()


def normalize_street(value: Any) -> str:
    """Capitalize a leading street type, leaving the rest untouched."""
    text = _collapse(value)
    if not text:
        return ""

    match = _LEADING_TYPE.match(text)
    if not match:
        return text

    head, tail = match.group(1), _collapse(match.group(2))
    canonical = STREET_TYPES.get(_fold(head))
    if not canonical or not tail:
        return text
    return f"{canonical} {tail}"


def normalize_address(payload: Mapping[str, Any]) -> Dict[str, str]:
    """Normalize the common address fields present in `payload`."""
    out: Dict[str, str] = {}
    for name in ADDRESS_FIELDS:
        if name not in payload:
            continue
        value = payload[name]
        if name == "zip":
            result = normalize_cep(value)
            out[name] = result.formatted if result.is_valid else _collapse(value)
        elif name == "street":
            out[name] = normalize_street(value)
        elif name == "state":
            out[name] = _fold(_collapse(value))[:2]
        else:
            out[name] = _collapse(value)
    return out


__all__ = [
    "normalize_cep", "normalize_phone", "normalize_cnae", "normalize_cnae_list",
    "normalize_street", "normalize_address", "AREA_CODES", "STREET_TYPES",
]
