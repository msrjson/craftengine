"""Address dictionary and street type normalization."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import re
import unicodedata
from typing import Any, Dict, Mapping

from .cep import normalize_cep

STREET_TYPES = {
    "RUA": "Rua",
    "R": "Rua",
    "AVENIDA": "Av.",
    "AV": "Av.",
    "AVE": "Av.",
    "TRAVESSA": "Trav.",
    "TRAV": "Trav.",
    "TV": "Trav.",
    "ALAMEDA": "Al.",
    "AL": "Al.",
    "PRACA": "Praça",
    "PCA": "Praça",
    "PC": "Praça",
    "RODOVIA": "Rod.",
    "ROD": "Rod.",
    "ESTRADA": "Estr.",
    "ESTR": "Estr.",
    "EST": "Estr.",
    "LARGO": "Largo",
    "LGO": "Largo",
    "VILA": "Vila",
    "VL": "Vila",
    "CONJUNTO": "Conj.",
    "CONJ": "Conj.",
    "LOTEAMENTO": "Lot.",
    "LOT": "Lot.",
    "QUADRA": "Qd.",
    "QD": "Qd.",
    "RODOANEL": "Rod.",
    "VIELA": "Viela",
    "PASSAGEM": "Pass.",
    "PASS": "Pass.",
    "SETOR": "Setor",
    "ST": "Setor",
}

ADDRESS_FIELDS = (
    "zip",
    "street",
    "number",
    "complement",
    "neighborhood",
    "city",
    "state",
)

_WHITESPACE = re.compile(r"\s+")
_LEADING_TYPE = re.compile(r"^([A-Za-zÀ-ÿ]+)\.?\s+(.*)$")


def _collapse(value: Any) -> str:
    return _WHITESPACE.sub(" ", str(value or "").strip())


def _fold(value: str) -> str:
    stripped = unicodedata.normalize("NFKD", value)
    return "".join(c for c in stripped if not unicodedata.combining(c)).upper()


def normalize_street(value: Any) -> str:
    """Normalize street name and capitalize standard street prefixes."""
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
    """Normalize common address dictionary fields."""
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
        elif name == "number":
            out[name] = _collapse(value)
        else:
            out[name] = _collapse(value)

    return out
