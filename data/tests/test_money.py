"""The `Money` value type and its ORM cast."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import json
from decimal import Decimal

import pytest

from craft.orm.casts import MoneyCast, resolve_cast
from craft.orm.model import Model
from craft.support.money import CurrencyMismatch, Money, minor_units


# -- the value type ------------------------------------------------------------


def test_money_arithmetic_is_exact_where_floats_are_not():
    assert 0.1 + 0.2 != 0.3
    total = Money("0.1") + Money("0.2")
    assert total == Money("0.30")
    assert str(total) == "BRL 0.30"


def test_an_amount_is_quantized_to_the_currency_minor_unit():
    assert Money("1.005").amount == Decimal("1.01")
    assert Money("1.004").amount == Decimal("1.00")
    assert Money("10").amount == Decimal("10.00")


def test_a_currency_without_minor_units_keeps_whole_amounts():
    assert minor_units("JPY") == 0
    assert Money("1200.4", "JPY") == Money("1200", "JPY")
    assert str(Money("1200", "JPY")) == "JPY 1200"


def test_combining_different_currencies_is_refused():
    with pytest.raises(CurrencyMismatch):
        Money("10", "BRL") + Money("10", "USD")
    with pytest.raises(CurrencyMismatch):
        _ = Money("10", "BRL") < Money("10", "USD")


def test_an_amount_of_another_currency_is_never_equal():
    assert (Money("10", "BRL") == Money("10", "USD")) is False


def test_multiplication_and_division_keep_the_currency():
    assert Money("10.00") * 3 == Money("30.00")
    assert 3 * Money("10.00") == Money("30.00")
    assert Money("10.00") / 4 == Money("2.50")


def test_sign_helpers_and_negation():
    assert Money("-1.00").is_negative() and Money("0.00").is_zero()
    assert (-Money("5.00")) == Money("-5.00")
    assert abs(Money("-5.00")) == Money("5.00")


def test_an_invalid_currency_or_amount_is_refused():
    with pytest.raises(ValueError):
        Money("10", "REAL")
    with pytest.raises(ValueError):
        Money("not a number")


def test_the_transport_form_is_a_decimal_string_not_a_float():
    payload = Money("10.5").to_dict()
    assert payload == {"amount": "10.50", "currency": "BRL"}
    assert isinstance(payload["amount"], str)


def test_from_dict_falls_back_to_the_default_currency():
    assert Money.from_dict({"amount": "3"}) == Money("3.00", "BRL")
    assert Money.from_dict({"amount": "3"}, default="USD") == Money("3.00", "USD")


# -- the cast ------------------------------------------------------------------


def test_the_cast_round_trips_on_both_drivers():
    cast = MoneyCast()
    price = Money("19.99")

    stored = cast.dehydrate(price, "sqlite")
    assert isinstance(stored, str)
    assert cast.hydrate(stored, "sqlite") == price

    # psycopg2 decodes jsonb itself, so the stored form arrives already parsed.
    assert cast.hydrate({"amount": "19.99", "currency": "BRL"}, "postgresql") == price


def test_the_cast_uses_its_declared_currency_for_a_bare_amount():
    cast = MoneyCast("EUR")
    assert cast.hydrate("12.00", "sqlite") == Money("12.00", "EUR")


def test_the_cast_refuses_a_value_that_is_not_money():
    with pytest.raises(TypeError):
        MoneyCast().dehydrate("19.99", "sqlite")


def test_the_cast_is_resolved_by_name_and_argument():
    assert isinstance(resolve_cast("money"), MoneyCast)
    assert resolve_cast("money:EUR").currency == "EUR"


def test_a_model_hydrates_and_dehydrates_a_money_column():
    class Invoice(Model):
        __table__ = "invoices"
        casts = {"total": "money"}

    invoice = Invoice({"total": '{"amount": "10.00", "currency": "BRL"}'})
    assert invoice.get_attribute("total") == Money("10.00")

    written = Invoice._dehydrate(dict(invoice._attributes))
    encoded = written["total"]
    decoded = json.loads(encoded) if isinstance(encoded, str) else encoded.adapted
    assert decoded == {"amount": "10.00", "currency": "BRL"}
    # The model keeps the value object after the write.
    assert invoice.get_attribute("total") == Money("10.00")
