"""PIX BR Code: the EMV payload for a PIX charge.

The format is EMV® QRCPS-MPM: a sequence of `ID(2) + LEN(2) + VALUE` fields
closed by a CRC16 over everything before it. Building the payload by hand is
error-prone, so the TLV writer and the checksum live here and the service
(`engine.py`) only decides which fields to write.
"""

from __future__ import annotations

import unicodedata

#: The PIX GUI inside the merchant account information template.
PIX_GUI = "BR.GOV.BCB.PIX"
CURRENCY_BRL = "986"
COUNTRY_BR = "BR"
STATIC = "11"
DYNAMIC = "12"
MAX_TXID = 25


def tlv(field_id: str, value: str) -> str:
    """One EMV field: two-digit id, two-digit length, value."""
    text = str(value)
    if len(field_id) != 2 or not field_id.isdigit():
        raise ValueError(f"emv_field_id_invalid:{field_id}")
    if len(text) > 99:
        raise ValueError(f"emv_value_too_long:{field_id}")
    return f"{field_id}{len(text):02d}{text}"


def sanitize(value: str, limit: int) -> str:
    """Fold a human value to plain uppercase ASCII, truncated to `limit`."""
    folded = unicodedata.normalize("NFKD", str(value or ""))
    ascii_only = folded.encode("ascii", "ignore").decode("utf-8")
    return ascii_only.upper()[:limit]


def crc16(payload: str) -> str:
    """CRC16/CCITT-FALSE (poly 0x1021, init 0xFFFF), as four uppercase hex digits."""
    crc = 0xFFFF
    for byte in payload.encode("utf-8"):
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return f"{crc:04X}"


def read_fields(payload: str) -> dict:
    """Parse a flat EMV payload into `{id: value}`; nested templates stay raw."""
    fields: dict = {}
    index = 0
    while index + 4 <= len(payload):
        field_id = payload[index:index + 2]
        length = int(payload[index + 2:index + 4])
        value = payload[index + 4:index + 4 + length]
        fields[field_id] = value
        index += 4 + length
    return fields


__all__ = ["tlv", "sanitize", "crc16", "read_fields", "PIX_GUI", "CURRENCY_BRL", "COUNTRY_BR", "STATIC", "DYNAMIC", "MAX_TXID"]
