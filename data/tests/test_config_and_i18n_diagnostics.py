"""Configuration and translation lookups report what is missing."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest

from craft.config.repository import MissingConfigKeyError


class TestRequire:
    def test_an_existing_key_is_returned(self, migrated_database):
        assert migrated_database.make("config").require("app.APP_ENV") is not None

    def test_a_guessed_key_names_the_real_one(self, migrated_database):
        with pytest.raises(MissingConfigKeyError) as raised:
            migrated_database.make("config").require("app.APP_DEBG")
        assert "app.APP_DEBUG" in str(raised.value)

    def test_it_is_a_key_error(self, migrated_database):
        with pytest.raises(KeyError):
            migrated_database.make("config").require("app.no_such_setting_anywhere")


class TestMissingTranslation:
    def test_a_missing_key_is_logged_once_and_counted(self, migrated_database, caplog):
        from craft.support import __
        from craft.support.metrics import registry

        key = "diagnostics.never.translated"
        with caplog.at_level("WARNING", logger="craft.i18n"):
            assert __(key, "es") == key
            __(key, "es")
        assert caplog.text.count("i18n.missing_key") == 1
        counter = registry.get("i18n_missing_keys_total")
        assert counter is not None
