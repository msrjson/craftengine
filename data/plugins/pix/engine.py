"""Pix — build and inspect a PIX BR Code payload.

`brcode()` writes a static (reusable) or dynamic (single-use) charge. `verify()`
recomputes the CRC of a payload it did not build, so a scanner or a receiver can
refuse a corrupted code instead of trusting it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .emv import (
    COUNTRY_BR,
    CURRENCY_BRL,
    DYNAMIC,
    MAX_TXID,
    PIX_GUI,
    STATIC,
    crc16,
    read_fields,
    sanitize,
    tlv,
)

DEFAULT_TXID = "***"


@dataclass(frozen=True, slots=True)
class PixCharge:
    """A built BR Code and the fields it carries."""

    payload: str
    key: str
    merchant_name: str
    merchant_city: str
    amount: Optional[str] = None
    txid: str = DEFAULT_TXID
    dynamic: bool = False


class Pix:
    """Stateless PIX BR Code builder. Pure function of its arguments."""

    @staticmethod
    def brcode(
        key: str,
        merchant_name: str,
        merchant_city: str,
        amount: Optional[float] = None,
        txid: Optional[str] = None,
        description: Optional[str] = None,
        dynamic: bool = False,
    ) -> PixCharge:
        """Build a PIX BR Code for `key` and the merchant details."""
        clean_key = str(key or "").strip()
        if not clean_key:
            raise ValueError("pix_key_empty")

        name = sanitize(merchant_name, 25)
        city = sanitize(merchant_city, 15)
        reference = sanitize(txid or DEFAULT_TXID, MAX_TXID) or DEFAULT_TXID

        merchant = tlv("00", PIX_GUI) + tlv("01", clean_key)
        if description:
            merchant += tlv("02", sanitize(description, 72))

        payload = tlv("00", "01")
        payload += tlv("01", DYNAMIC if dynamic else STATIC)
        payload += tlv("26", merchant)
        payload += tlv("52", "0000")
        payload += tlv("53", CURRENCY_BRL)

        formatted_amount: Optional[str] = None
        if amount is not None:
            formatted_amount = f"{float(amount):.2f}"
            payload += tlv("54", formatted_amount)

        payload += tlv("58", COUNTRY_BR)
        payload += tlv("59", name)
        payload += tlv("60", city)
        payload += tlv("62", tlv("05", reference))
        payload += "6304"
        payload += crc16(payload)

        return PixCharge(
            payload=payload,
            key=clean_key,
            merchant_name=name,
            merchant_city=city,
            amount=formatted_amount,
            txid=reference,
            dynamic=dynamic,
        )

    @staticmethod
    def verify(payload: str) -> bool:
        """Whether the payload's CRC matches its content."""
        text = str(payload or "")
        if len(text) < 8 or not text[-8:-4] == "6304":
            return False
        return crc16(text[:-4]) == text[-4:].upper()

    @staticmethod
    def fields(payload: str) -> dict:
        """Parse the flat fields of a payload into `{id: value}`."""
        return read_fields(str(payload or ""))


__all__ = ["Pix", "PixCharge", "DEFAULT_TXID"]
