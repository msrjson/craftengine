"""Unit tests for ICU MessageFormat and CLDR Pluralization support."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from engine.support.icu import format_message, plural_category
from engine.support.translation import __, translate


def test_plural_category_english():
    """Verify CLDR plural category rules for English."""
    assert plural_category("en", 1) == "one"
    assert plural_category("en", 0) == "other"
    assert plural_category("en", 2) == "other"
    assert plural_category("en", 5) == "other"


def test_plural_category_portuguese():
    """Verify CLDR plural category rules for Portuguese (0 and 1 are 'one')."""
    assert plural_category("pt-BR", 0) == "one"
    assert plural_category("pt-BR", 1) == "one"
    assert plural_category("pt-BR", 2) == "other"
    assert plural_category("pt-BR", 10) == "other"


def test_format_message_simple_named_replacement():
    """Verify basic {name} substitution."""
    template = "Hello, {name}! Welcome to {place}."
    result = format_message(template, {"name": "Alice", "place": "Wonderland"})
    assert result == "Hello, Alice! Welcome to Wonderland."


def test_format_message_plural_with_exact_match():
    """Verify =0 exact value branch override."""
    template = "{count, plural, =0 {No orders} one {# order} other {# orders}}"
    assert format_message(template, {"count": 0}, locale="en") == "No orders"
    assert format_message(template, {"count": 1}, locale="en") == "1 order"
    assert format_message(template, {"count": 5}, locale="en") == "5 orders"


def test_format_message_nested_parameters():
    """Verify nesting of parameters inside plural branches."""
    template = "{count, plural, =0 {{user} has no items} other {{user} has # items}}"
    assert format_message(template, {"count": 0, "user": "Bob"}, locale="en") == "Bob has no items"
    assert format_message(template, {"count": 3, "user": "Bob"}, locale="en") == "Bob has 3 items"


def test_format_message_graceful_degradation():
    """Verify malformed messages or missing parameters degrade safely without raising."""
    # Missing parameter is left as-is
    assert format_message("Hello, {unknown}!", {}) == "Hello, {unknown}!"
    # Unbalanced brace is emitted verbatim
    assert format_message("Unbalanced {brace", {"brace": "val"}) == "Unbalanced {brace"


def test_translate_helper_with_icu_plurals():
    """Verify translate() and __() invoke format_message for dynamic plurals."""
    raw = "{count, plural, =0 {Cart is empty} one {# item in cart} other {# items in cart}}"
    # Without db/config entry, translate falls back to the key itself
    res_0 = __(raw, count=0)
    res_1 = __(raw, count=1)
    res_2 = __(raw, count=2)

    assert res_0 == "Cart is empty"
    assert res_1 == "1 item in cart"
    assert res_2 == "2 items in cart"
