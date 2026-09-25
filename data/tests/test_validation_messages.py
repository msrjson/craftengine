"""Validation messages are translation keys, seeded in every locale."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest

from craft.support.translation import current_locale
from craft.validation import Validator
from craft.validation.messages import KEY_PREFIX, LOCALES, TRANSLATIONS, seed_translations


def _first_error(data, rules, messages=None):
    validator = Validator(data, rules, messages or {})
    validator.passes()
    return next(iter(validator.errors.values()))[0]


@pytest.fixture
def locale():
    tokens = []

    def use(code):
        tokens.append(current_locale.set(code))

    yield use
    for token in reversed(tokens):
        current_locale.reset(token)


def test_every_code_is_seeded_in_every_locale(migrated_database):
    rows = migrated_database.make("db").table("translations").where("key", "like", KEY_PREFIX + "%").get()
    seeded = {(row["key"], row["locale"]) for row in rows}
    expected = {(KEY_PREFIX + code, locale) for code in TRANSLATIONS for locale in LOCALES}
    assert expected <= seeded


def test_seeding_again_inserts_nothing(migrated_database):
    assert seed_translations(migrated_database.make("db")) == 0


def test_the_message_follows_the_request_locale(migrated_database, locale):
    locale("pt-BR")
    assert _first_error({}, {"email": ["required"]}) == "O campo email é obrigatório"
    locale("es")
    assert _first_error({"age": 3}, {"age": ["integer", "min:18"]}) == "El campo age debe ser al menos 18"


def test_english_is_unchanged(migrated_database, locale):
    locale("en")
    assert _first_error({"code": "abc"}, {"code": ["digits:4"]}) == "code must be 4 digits"


def test_a_message_given_by_the_form_still_wins(migrated_database, locale):
    locale("pt-BR")
    assert _first_error({}, {"email": ["required"]}, {"email.required": "custom"}) == "custom"


def test_every_code_formats_with_its_placeholders():
    from craft.support.icu import format_message

    params = {"field": "f", "value": 1, "min": 1, "max": 2, "values": "a, b", "length": 3, "expected": 2, "types": "png"}
    for code, texts in TRANSLATIONS.items():
        for text in texts:
            assert "{" not in format_message(text, params, locale="en"), (code, text)
