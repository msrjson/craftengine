"""An exact money amount in a single currency.

Category: Core Framework (Support).
Relations:
  - Cast by `engine/orm/casts.py::MoneyCast`, so a `Model.casts` entry can
    declare a column as money.
References:
  - Guide: `documentation/orm.md#attribute-casting`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Dict

#: Used when no currency is given. A framework default keeps a typo in one
#: call site from producing a value no comparison will ever match.
DEFAULT_CURRENCY = "BRL"

#: Currencies whose minor unit is not the usual hundredth. Anything not listed
#: uses two decimal places, which is the overwhelming majority.
_MINOR_UNITS = {
    "BIF": 0, "CLP": 0, "DJF": 0, "GNF": 0, "ISK": 0, "JPY": 0, "KMF": 0,
    "KRW": 0, "PYG": 0, "RWF": 0, "UGX": 0, "VND": 0, "VUV": 0, "XAF": 0,
    "XOF": 0, "XPF": 0,
    "BHD": 3, "IQD": 3, "JOD": 3, "KWD": 3, "LYD": 3, "OMR": 3, "TND": 3,
}


class CurrencyMismatch(ValueError):
    """Raised when two amounts in different currencies are combined."""


def minor_units(currency: str) -> int:
    """How many decimal places the currency settles in."""
    return _MINOR_UNITS.get(currency.upper(), 2)


def _quantum(currency: str) -> Decimal:
    return Decimal(1).scaleb(-minor_units(currency))


class Money:
    """A fixed-point amount, quantized to its currency's minor unit.

    Arithmetic stays exact because the amount is a `Decimal`, never a float:
    `0.1 + 0.2` is `0.3` here and `0.30000000000000004` with floats, which is
    the whole reason a money type exists. Adding two currencies, or comparing
    them, raises `CurrencyMismatch` rather than silently mixing them.
    """

    __slots__ = ("amount", "currency")

    def __init__(self, amount: Any = 0, currency: str = DEFAULT_CURRENCY) -> None:
        code = str(currency).upper()
        if len(code) != 3 or not code.isalpha():
            raise ValueError(f"Invalid currency code [{currency}].")
        if isinstance(amount, Money):
            amount = amount.amount
        try:
            value = amount if isinstance(amount, Decimal) else Decimal(str(amount))
        except (InvalidOperation, ValueError, TypeError) as error:
            raise ValueError(f"Invalid money amount [{amount!r}].") from error
        self.currency = code
        self.amount = value.quantize(_quantum(code), rounding=ROUND_HALF_UP)

    # -- helpers ---------------------------------------------------------------

    def _amount_of(self, other: Any) -> Decimal:
        if not isinstance(other, Money):
            raise TypeError(
                f"Expected Money, got {type(other).__name__}."
            )
        if other.currency != self.currency:
            raise CurrencyMismatch(
                f"Cannot combine {self.currency} with {other.currency}."
            )
        return other.amount

    def _same_currency(self, other: Any) -> bool:
        return isinstance(other, Money) and other.currency == self.currency

    # -- arithmetic ------------------------------------------------------------

    def __add__(self, other: Any) -> "Money":
        return Money(self.amount + self._amount_of(other), self.currency)

    def __sub__(self, other: Any) -> "Money":
        return Money(self.amount - self._amount_of(other), self.currency)

    def __mul__(self, factor: Any) -> "Money":
        return Money(self.amount * Decimal(str(factor)), self.currency)

    __rmul__ = __mul__

    def __truediv__(self, divisor: Any) -> "Money":
        return Money(self.amount / Decimal(str(divisor)), self.currency)

    def __neg__(self) -> "Money":
        return Money(-self.amount, self.currency)

    def __abs__(self) -> "Money":
        return Money(abs(self.amount), self.currency)

    # -- comparison ------------------------------------------------------------

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return self.currency == other.currency and self.amount == other.amount

    def __lt__(self, other: Any) -> bool:
        if not self._same_currency(other):
            raise CurrencyMismatch(
                f"Cannot compare {self.currency} with {getattr(other, 'currency', other)!r}."
            )
        return self.amount < other.amount

    def __le__(self, other: Any) -> bool:
        return self == other or self < other

    def __gt__(self, other: Any) -> bool:
        return not self <= other

    def __ge__(self, other: Any) -> bool:
        return not self < other

    def __hash__(self) -> int:
        return hash((self.currency, self.amount))

    def __bool__(self) -> bool:
        return self.amount != 0

    # -- representation --------------------------------------------------------

    def __str__(self) -> str:
        return f"{self.currency} {self.amount:.{minor_units(self.currency)}f}"

    def __repr__(self) -> str:
        return f"Money({self.amount!r}, {self.currency!r})"

    def is_zero(self) -> bool:
        return self.amount == 0

    def is_positive(self) -> bool:
        return self.amount > 0

    def is_negative(self) -> bool:
        return self.amount < 0

    def to_dict(self) -> Dict[str, str]:
        """The transport form the ORM cast writes."""
        return {"amount": str(self.amount), "currency": self.currency}

    @classmethod
    def from_dict(cls, data: Dict[str, Any], default: str | None = None) -> "Money":
        return cls(data.get("amount", 0), data.get("currency") or default or DEFAULT_CURRENCY)


__all__ = ["CurrencyMismatch", "DEFAULT_CURRENCY", "Money", "minor_units"]
