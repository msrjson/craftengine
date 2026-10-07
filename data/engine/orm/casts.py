"""Attribute casting between column values and Python values.

Without this, `Model._attributes` holds whatever the driver handed back and
`save()` writes it straight back out. That works for text and numbers and
breaks for every interesting PostgreSQL type: a `jsonb` column arrives as a
`dict` under psycopg2 and as a `str` under sqlite3, and writing a `dict` back
raises *can't adapt type 'dict'*. Arrays, ranges and vectors have no round trip
at all.

Declare the shape on the model and both directions become the framework's
problem::

    class Account(Model):
        casts = {"meta": "jsonb", "tags": "array:str", "period": "tsrange"}

Category: Core Framework (ORM).
Relations:
  - Applied by `Model._hydrate()` / `Model._dehydrate()`
    (`engine/orm/model.py`).
  - The column types they pair with are declared in
    `engine/migrations/schema.py`.
References:
  - Guide: `documentation/orm.md#attribute-casting`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import json
from typing import Any, Protocol, runtime_checkable

from engine.support.money import DEFAULT_CURRENCY, Money


@runtime_checkable
class Cast(Protocol):
    """Two-way conversion between a column value and a Python value."""

    def hydrate(self, value: Any, driver: str) -> Any: ...

    def dehydrate(self, value: Any, driver: str) -> Any: ...


class JsonbCast:
    """`dict` / `list` <-> `jsonb`.

    psycopg2 decodes a jsonb column into a Python object on the way out but
    refuses to adapt a bare `dict` on the way in — it wants the `Json` wrapper.
    sqlite3 does neither and stores text. Both directions have to be explicit or
    writes fail on one driver and reads fail on the other.
    """

    def hydrate(self, value: Any, driver: str) -> Any:
        if value is None or isinstance(value, (dict, list)):
            return value
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            # Not JSON after all — hand back what was stored rather than
            # replacing a readable value with None.
            return value

    def dehydrate(self, value: Any, driver: str) -> Any:
        if value is None:
            return None
        if driver == "postgresql":
            from psycopg2.extras import Json

            return Json(value)
        return json.dumps(value, default=str)


class ArrayCast:
    """`list` <-> `ARRAY`. psycopg2 adapts a list natively; SQLite gets JSON."""

    #: `"array:int"` and friends resolve through here rather than `eval`.
    ELEMENTS = {"str": str, "int": int, "float": float, "bool": bool}

    def __init__(self, of: Any = str):
        self.of = self.ELEMENTS[of] if isinstance(of, str) else of

    def hydrate(self, value: Any, driver: str) -> Any:
        if value is None or isinstance(value, list):
            return value
        if isinstance(value, tuple):
            return list(value)
        try:
            decoded = json.loads(value)
        except (TypeError, ValueError):
            return value
        return [self.of(item) for item in decoded] if isinstance(decoded, list) else value

    def dehydrate(self, value: Any, driver: str) -> Any:
        if value is None:
            return None
        if driver == "postgresql":
            return list(value)
        return json.dumps(list(value), default=str)


class RangeCast:
    """`(lower, upper)` <-> a range type, half-open by convention.

    Half-open — `[lower, upper)` — because it is the only convention under
    which adjacent ranges neither overlap nor leave a gap, which is what makes
    an exclusion constraint on `&&` mean "double booked".
    """

    KINDS = {"tsrange": "timestamp", "tstzrange": "timestamptz",
             "daterange": "date", "int4range": "int", "int8range": "bigint",
             "numrange": "numeric"}

    def __init__(self, kind: str = "tsrange"):
        if kind not in self.KINDS:
            raise ValueError(
                f"Unknown range type [{kind}]. Known: {', '.join(sorted(self.KINDS))}."
            )
        self.kind = kind

    def hydrate(self, value: Any, driver: str) -> Any:
        if value is None or isinstance(value, tuple):
            return value
        lower = getattr(value, "lower", None)
        upper = getattr(value, "upper", None)
        if lower is not None or upper is not None:
            return (lower, upper)
        return value

    def dehydrate(self, value: Any, driver: str) -> Any:
        """Render as the literal PostgreSQL parses for any range type.

        A two-element tuple is the whole surface, so the same model attribute
        reads the same on SQLite (where it is stored as text) as it does here.
        """
        if value is None:
            return None
        lower, upper = value
        return f"[{'' if lower is None else lower},{'' if upper is None else upper})"


class MoneyCast:
    """`Money` <-> a JSON object `{"amount": "10.00", "currency": "BRL"}`.

    The amount travels as a decimal string, never a JSON number: a JSON number
    is a float on the wire, and a float round trip is exactly what a money type
    exists to avoid. The cast argument sets the currency used when a stored
    value carries none (``"money:EUR"``), defaulting to the framework default.
    """

    def __init__(self, currency: str | None = None):
        self.currency = currency.upper() if currency else None

    def hydrate(self, value: Any, driver: str) -> Any:
        if value is None or isinstance(value, Money):
            return value
        if isinstance(value, (bytes, bytearray)):
            value = value.decode()
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except (TypeError, ValueError):
                return Money(value, self.currency or DEFAULT_CURRENCY)
        if isinstance(value, dict):
            return Money.from_dict(value, default=self.currency)
        return Money(value, self.currency or DEFAULT_CURRENCY)

    def dehydrate(self, value: Any, driver: str) -> Any:
        if value is None:
            return None
        if not isinstance(value, Money):
            raise TypeError(
                f"Expected Money on a money cast column, got {type(value).__name__}."
            )
        payload = value.to_dict()
        if driver == "postgresql":
            from psycopg2.extras import Json

            return Json(payload)
        return json.dumps(payload)


class VectorCast:
    """`list[float]` <-> `vector(n)`, in pgvector's own literal form."""

    def hydrate(self, value: Any, driver: str) -> Any:
        if value is None or isinstance(value, list):
            return value
        if isinstance(value, str) and value.startswith("["):
            body = value.strip()[1:-1]
            return [float(part) for part in body.split(",") if part.strip()]
        return value

    def dehydrate(self, value: Any, driver: str) -> Any:
        if value is None:
            return None
        return vector_literal(value)


def vector_literal(vector: Any) -> str:
    """`[0.1,0.2]` — the text form pgvector casts from, built once, here.

    Every macro and every write goes through this, so a vector is rendered the
    same way whichever path produced it.
    """
    return "[" + ",".join(repr(float(component)) for component in vector) + "]"


#: Cast names usable in `Model.casts`. `"array:int"` and `"tsrange"` are the
#: two shapes: a name, optionally followed by a colon and one argument.
CAST_ALIASES = {
    "jsonb": JsonbCast,
    "json": JsonbCast,
    "array": ArrayCast,
    "vector": VectorCast,
    "money": MoneyCast,
    "tsrange": lambda: RangeCast("tsrange"),
    "tstzrange": lambda: RangeCast("tstzrange"),
    "daterange": lambda: RangeCast("daterange"),
    "int4range": lambda: RangeCast("int4range"),
    "int8range": lambda: RangeCast("int8range"),
    "numrange": lambda: RangeCast("numrange"),
}


def resolve_cast(spec: str) -> Cast:
    """Build the cast a `Model.casts` entry names.

    An unknown name raises rather than being ignored: a typo that silently
    disables casting produces a write failure far from its cause.
    """
    name, _, argument = str(spec).partition(":")
    factory = CAST_ALIASES.get(name)
    if factory is None:
        raise ValueError(
            f"Unknown cast [{spec}]. Known: {', '.join(sorted(CAST_ALIASES))}."
        )
    return factory(argument) if argument else factory()


__all__ = [
    "ArrayCast",
    "CAST_ALIASES",
    "Cast",
    "JsonbCast",
    "MoneyCast",
    "RangeCast",
    "VectorCast",
    "resolve_cast",
    "vector_literal",
]
