"""Translation helper: BCP 47 normalisation, fallback chain, and locales."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest

from craft.facades import DB
from craft.support.translation import __, locale_chain, normalize_locale, translate


class TestNormalizeLocale:
    @pytest.mark.parametrize(
        "given,expected",
        [
            ("en", "en"),
            ("EN", "en"),
            ("pt-BR", "pt-BR"),
            ("PT-br", "pt-BR"),
            ("pt_BR", "pt-BR"),
            ("Pt-Br", "pt-BR"),
        ],
    )
    def test_canonical_form(self, given, expected):
        # BCP 47 writes the language lowercase and the region uppercase.
        assert normalize_locale(given) == expected

    def test_none_stays_none(self):
        assert normalize_locale(None) is None
        assert normalize_locale("") is None


class TestLocaleChain:
    def test_a_regional_locale_falls_back_to_its_base(self):
        assert locale_chain("pt-BR", "en") == ["pt-BR", "pt", "en"]

    def test_a_base_locale_has_no_region_step(self):
        assert locale_chain("pt", "en") == ["pt", "en"]

    def test_the_fallback_is_not_duplicated(self):
        assert locale_chain("en", "en") == ["en"]

    def test_a_regional_fallback_expands_too(self):
        assert locale_chain("es", "pt-BR") == ["es", "pt-BR", "pt"]

    def test_casing_is_normalised_in_the_chain(self):
        assert locale_chain("PT-br", "EN") == ["pt-BR", "pt", "en"]


class TestTranslationLookup:
    @pytest.fixture(autouse=True)
    def seeded(self, migrated_database):
        rows = [
            ("test_greeting", "en", "Hello"),
            ("test_greeting", "pt", "Olá"),
            ("test_greeting", "pt-BR", "Oi"),
            ("test_greeting", "es", "Hola"),
            ("only_in_pt", "pt", "Apenas em pt"),
            ("only_in_en", "en", "English only"),
        ]
        for key, locale, value in rows:
            if DB.table("translations").where("key", key).where("locale", locale).first() is None:
                DB.table("translations").insert({"key": key, "locale": locale, "value": value})

    def test_exact_locale_wins(self):
        assert __("test_greeting", "pt-BR") == "Oi"

    def test_each_locale_resolves_independently(self):
        assert __("test_greeting", "pt") == "Olá"
        assert __("test_greeting", "es") == "Hola"
        assert __("test_greeting", "en") == "Hello"

    def test_a_regional_locale_inherits_from_its_base(self):
        # Without the chain this returned the raw key.
        assert __("only_in_pt", "pt-BR") == "Apenas em pt"

    def test_a_regional_locale_falls_back_to_the_default(self):
        assert __("only_in_en", "pt-BR") == "English only"

    def test_a_missing_key_returns_the_key(self):
        assert __("no.such.key", "pt-BR") == "no.such.key"

    def test_locale_casing_does_not_matter(self):
        assert __("test_greeting", "PT-br") == "Oi"

    def test_placeholders_are_replaced(self):
        DB.statement(
            "INSERT INTO translations (key, locale, value) VALUES (?, ?, ?)",
            ["welcome_user", "pt-BR", "Olá, {name}!"],
        )
        assert translate("welcome_user", "pt-BR", name="Ana") == "Olá, Ana!"

    def test_placeholders_work_on_the_key_fallback(self):
        assert translate("missing_{n}", "pt-BR", n=3) == "missing_3"

    def test_database_translations_override_config_and_config_acts_as_fallback(self, migrated_database):
        config = migrated_database.make("config")
        config.set("lang.pt-BR.test_greeting", "Config Greeting")
        config.set("lang.pt-BR.fallback_only_key", "Config Fallback Value")
        try:
            # DB has "Oi" for greeting in pt-BR, so DB overrides config
            assert __("test_greeting", "pt-BR") == "Oi"
            # DB does not have fallback_only_key, so config is used as fallback
            assert __("fallback_only_key", "pt-BR") == "Config Fallback Value"
        finally:
            config.set("lang.pt-BR.test_greeting", None)
            config.set("lang.pt-BR.fallback_only_key", None)


