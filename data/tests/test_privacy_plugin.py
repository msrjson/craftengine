"""Tests for the privacy kit plugin (`plugins/privacy/`)."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import json
import os

from engine.plugins.manager import PluginManager
from plugins.privacy import Privacy
from plugins.privacy.engine import PORTABILITY_FORMAT


class TestPortability:
    def test_the_bundle_counts_and_orders_sections(self):
        bundle = Privacy.portability_bundle(
            "subject-1",
            {"orders": [{"id": 1}, {"id": 2}], "profile": [{"name": "Ana"}]},
            generated_at="2026-10-07T00:00:00",
        )
        assert bundle["format"] == PORTABILITY_FORMAT
        assert bundle["subject"] == "subject-1"
        assert bundle["total_records"] == 3
        assert [section["name"] for section in bundle["sections"]] == ["orders", "profile"]
        assert bundle["sections"][0]["count"] == 2

    def test_rows_are_copied_not_aliased(self):
        row = {"id": 1}
        bundle = Privacy.portability_bundle("s", {"x": [row]})
        bundle["sections"][0]["records"][0]["id"] = 99
        assert row["id"] == 1

    def test_the_bundle_is_json_serializable(self):
        bundle = Privacy.portability_bundle("s", {"x": [{"id": 1}]})
        assert json.loads(json.dumps(bundle))["total_records"] == 1


class TestLegalPages:
    def test_the_three_legal_pages_are_declared(self):
        slugs = [page["slug"] for page in Privacy.legal_pages()]
        assert slugs == ["privacy", "terms", "cookies"]

    def test_each_page_carries_a_route_and_a_title_key(self):
        for page in Privacy.legal_pages():
            assert page["route"].startswith("/")
            assert page["title_key"].startswith("legal.")


class TestPluginWiring:
    def test_the_plugin_is_discoverable_on_disk(self):
        slugs = {descriptor["slug"] for descriptor in PluginManager().discover(os.getcwd())}
        assert "privacy" in slugs

    def test_register_binds_the_service_in_the_container(self):
        from bootstrap.app import app
        from plugins.privacy.plugin import register

        register(app)
        assert isinstance(app.make("privacy"), Privacy)
