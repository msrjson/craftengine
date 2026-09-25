"""Plugin manager: registration, activation, hooks, discovery and persistence."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import logging
import os
import textwrap
import uuid

import pytest

from craft.facades import DB
from craft.plugins.manager import PluginManager


@pytest.fixture
def plugins():
    return PluginManager()


def _write_plugin(base_path: str, slug: str, name: str = None, extra: str = "") -> str:
    """Create a `plugins/<slug>/plugin.py` manifest under `base_path`."""
    plugin_dir = os.path.join(base_path, "plugins", slug)
    os.makedirs(plugin_dir, exist_ok=True)
    manifest = os.path.join(plugin_dir, "plugin.py")
    with open(manifest, "w", encoding="utf-8") as handle:
        handle.write(textwrap.dedent(f"""
            PLUGIN = {{
                "slug": "{slug}",
                "name": "{name or slug}",
                "version": "1.0.0",
                "description": "A test plugin",
            }}
            {extra}
        """))
    return plugin_dir


class TestRegistration:
    def test_a_registered_plugin_is_active(self, plugins):
        plugins.register("stripe", {"version": "1.0"})
        assert plugins.is_active("stripe") is True

    def test_an_unknown_plugin_is_not_active(self, plugins):
        assert plugins.is_active("nope") is False

    def test_all_lists_registered_plugins(self, plugins):
        plugins.register("a", {})
        plugins.register("b", {})
        assert {p["name"] for p in plugins.all()} == {"a", "b"}

    def test_deactivate_then_activate(self, plugins):
        plugins.register("stripe", {})
        plugins.deactivate("stripe")
        assert plugins.is_active("stripe") is False
        plugins.activate("stripe")
        assert plugins.is_active("stripe") is True

    def test_registering_twice_replaces_the_entry(self, plugins):
        plugins.register("stripe", {"version": "1"})
        plugins.register("stripe", {"version": "2"})
        assert len(plugins.all()) == 1
        assert plugins.all()[0]["instance"]["version"] == "2"


class TestHooks:
    def test_a_hook_receives_the_arguments(self, plugins):
        seen = []
        plugins.add_hook("payment", lambda amount, currency=None: seen.append((amount, currency)))
        plugins.trigger_hook("payment", 150.0, currency="BRL")
        assert seen == [(150.0, "BRL")]

    def test_hooks_run_in_registration_order(self, plugins):
        order = []
        plugins.add_hook("e", lambda: order.append(1))
        plugins.add_hook("e", lambda: order.append(2))
        plugins.trigger_hook("e")
        assert order == [1, 2]

    def test_results_are_collected(self, plugins):
        plugins.add_hook("e", lambda: "a")
        plugins.add_hook("e", lambda: "b")
        assert plugins.trigger_hook("e") == ["a", "b"]

    def test_triggering_an_unregistered_hook_is_harmless(self, plugins):
        assert plugins.trigger_hook("nothing-here") == []

    def test_has_hook(self, plugins):
        assert plugins.has_hook("e") is False
        plugins.add_hook("e", lambda: None)
        assert plugins.has_hook("e") is True

    def test_remove_a_single_hook(self, plugins):
        keep = lambda: "keep"  # noqa: E731
        drop = lambda: "drop"  # noqa: E731
        plugins.add_hook("e", keep)
        plugins.add_hook("e", drop)
        plugins.remove_hook("e", drop)
        assert plugins.trigger_hook("e") == ["keep"]

    def test_remove_every_hook_for_an_event(self, plugins):
        plugins.add_hook("e", lambda: None)
        plugins.remove_hook("e")
        assert plugins.has_hook("e") is False


class TestHookFailureIsolation:
    def test_one_failing_plugin_does_not_stop_the_others(self, plugins):
        def explodes():
            raise RuntimeError("bad plugin")

        plugins.add_hook("e", explodes)
        plugins.add_hook("e", lambda: "survivor")

        assert plugins.trigger_hook("e") == ["survivor"]

    def test_the_failure_is_logged_not_swallowed(self, plugins, caplog):
        def explodes():
            raise RuntimeError("bad plugin")

        plugins.add_hook("payment", explodes)
        with caplog.at_level(logging.WARNING, logger="craft"):
            plugins.trigger_hook("payment")

        assert any("payment" in record.message for record in caplog.records)

    def test_the_exception_does_not_propagate(self, plugins):
        plugins.add_hook("e", lambda: 1 / 0)
        plugins.trigger_hook("e")  # must not raise


class TestDiscovery:
    def test_discover_finds_a_manifest(self, plugins, tmp_path):
        _write_plugin(str(tmp_path), "billing", name="Billing Plugin")
        found = plugins.discover(str(tmp_path))
        assert len(found) == 1
        assert found[0]["slug"] == "billing"
        assert found[0]["name"] == "Billing Plugin"
        assert found[0]["path"] == os.path.join(str(tmp_path), "plugins", "billing")

    def test_discover_returns_empty_list_when_no_plugins_dir(self, plugins, tmp_path):
        assert plugins.discover(str(tmp_path)) == []

    def test_discover_skips_a_directory_without_a_manifest(self, plugins, tmp_path):
        os.makedirs(os.path.join(str(tmp_path), "plugins", "empty"))
        assert plugins.discover(str(tmp_path)) == []

    def test_discover_skips_a_broken_manifest(self, plugins, tmp_path):
        _write_plugin(str(tmp_path), "good")
        broken_dir = os.path.join(str(tmp_path), "plugins", "broken")
        os.makedirs(broken_dir)
        with open(os.path.join(broken_dir, "plugin.py"), "w", encoding="utf-8") as handle:
            handle.write("raise RuntimeError('boom')\n")

        found = plugins.discover(str(tmp_path))
        assert [p["slug"] for p in found] == ["good"]

    def test_discover_skips_a_manifest_without_a_slug(self, plugins, tmp_path):
        _write_plugin(str(tmp_path), "valid")
        no_slug_dir = os.path.join(str(tmp_path), "plugins", "no_slug")
        os.makedirs(no_slug_dir)
        with open(os.path.join(no_slug_dir, "plugin.py"), "w", encoding="utf-8") as handle:
            handle.write("PLUGIN = {'name': 'No Slug'}\n")

        found = plugins.discover(str(tmp_path))
        assert [p["slug"] for p in found] == ["valid"]


@pytest.fixture
def slug():
    """A plugin slug no other test uses.

    The `plugins` table is shared for the whole session and tests never delete
    rows (NR-02), so every database-touching test owns its slug.
    """
    return f"billing_{uuid.uuid4().hex[:8]}"


class TestPersistence:
    @pytest.fixture
    def seeded(self, slug):
        DB.statement(
            "INSERT INTO plugins (name, slug, enabled, path) VALUES (?, ?, ?, ?)",
            ["Billing Plugin", slug, True, f"/plugins/{slug}"],
        )

    def _enabled_in_db(self, slug: str):
        row = DB.statement(
            "SELECT enabled FROM plugins WHERE slug = ?", [slug], read=True
        ).fetchone()
        return bool(row["enabled"]) if row is not None else None

    def test_disable_writes_to_the_database(self, plugins, slug, seeded):
        plugins.disable(slug)
        assert self._enabled_in_db(slug) is False

    def test_enable_writes_to_the_database(self, plugins, slug, seeded):
        plugins.disable(slug)
        plugins.enable(slug)
        assert self._enabled_in_db(slug) is True

    def test_is_enabled_reads_from_the_database(self, plugins, slug, seeded):
        DB.statement("UPDATE plugins SET enabled = ? WHERE slug = ?", [False, slug])
        assert plugins.is_enabled(slug) is False

    def test_installed_lists_database_plugins(self, plugins, slug, seeded):
        slugs = [p["slug"] for p in plugins.installed()]
        assert slug in slugs

    def test_enabling_an_unknown_plugin_reports_failure(self, plugins):
        assert plugins.enable("does-not-exist") is False

    def test_disabling_an_unknown_plugin_reports_failure(self, plugins):
        assert plugins.disable("does-not-exist") is False

    def test_unknown_plugin_is_not_enabled(self, plugins):
        assert plugins.is_enabled("does-not-exist") is False

    def test_an_in_memory_plugin_can_still_be_toggled(self, plugins):
        plugins.register_slug("inmem", "In Memory")
        assert plugins.disable("inmem") is True
        assert plugins.is_enabled("inmem") is False


class TestSync:
    def test_sync_registers_newly_discovered_plugins(self, plugins, slug, tmp_path):
        _write_plugin(str(tmp_path), slug, name="Billing Plugin")
        newly_registered = plugins.sync(str(tmp_path))

        assert newly_registered == [slug]
        slugs = [p["slug"] for p in plugins.installed()]
        assert slug in slugs
        assert plugins.is_enabled(slug) is True

    def test_sync_does_not_reenable_a_disabled_plugin(self, plugins, slug, tmp_path):
        _write_plugin(str(tmp_path), slug, name="Billing Plugin")
        plugins.sync(str(tmp_path))
        plugins.disable(slug)

        newly_registered = plugins.sync(str(tmp_path))

        assert newly_registered == []
        assert plugins.is_enabled(slug) is False

    def test_sync_returns_no_new_plugins_on_an_empty_directory(self, plugins, tmp_path):
        assert plugins.sync(str(tmp_path)) == []
