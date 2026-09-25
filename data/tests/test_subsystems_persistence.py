"""Settings and Modules must actually reach the database.

Both managers fall back to in-memory state when a query fails, so the existing
subsystem test passed entirely on the memory path — the persistence it claims to
provide was never exercised. These tests read the tables back directly.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import uuid

import pytest

from craft.facades import DB, Module, Setting
from craft.modules.manager import ModuleManager
from craft.support.settings import SettingManager


@pytest.fixture(autouse=True)
def cold_memory_cache(migrated_database):
    """Start and end every test with an empty in-memory settings cache.

    Rows are never deleted (NR-02): `settings` and `modules` keep what earlier
    tests wrote, so every test below owns uniquely named keys, slugs and
    tenants instead of relying on an empty table.
    """
    SettingManager._memory_settings = {}
    yield
    SettingManager._memory_settings = {}


@pytest.fixture
def key():
    """A settings key no other test uses."""
    return f"site_title_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def slug():
    """A module slug no other test uses."""
    return f"billing_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def tenants():
    """Two tenant ids no other test uses."""
    suffix = uuid.uuid4().hex[:8]
    return f"tenant-a-{suffix}", f"tenant-b-{suffix}"


class TestSettingPersistence:
    def test_set_writes_a_row(self, key):
        Setting.set(key, "Craft")
        row = DB.statement(
            "SELECT value FROM settings WHERE key = ?", [key], read=True
        ).fetchone()
        assert row is not None
        assert row["value"] == '"Craft"'  # values are stored JSON-encoded

    def test_value_survives_losing_the_memory_cache(self, key):
        Setting.set(key, "Craft")
        SettingManager._memory_settings = {}
        assert Setting.get(key) == "Craft"

    def test_setting_the_same_key_twice_updates_it(self, key):
        Setting.set(key, "First")
        Setting.set(key, "Second")

        rows = DB.statement(
            "SELECT value FROM settings WHERE key = ?", [key], read=True
        ).fetchall()
        assert len(rows) == 1
        assert rows[0]["value"] == '"Second"'  # values are stored JSON-encoded

    def test_missing_key_returns_the_default(self):
        assert Setting.get(f"never_set_{uuid.uuid4().hex[:8]}", "fallback") == "fallback"

    def test_values_keep_their_type(self):
        # Values used to be flattened through str(), so set("x", False) came
        # back as the truthy string "False". JSON encoding keeps the type.
        suffix = uuid.uuid4().hex[:8]
        max_items_key, feature_key = f"max_items_{suffix}", f"feature_on_{suffix}"
        Setting.set(max_items_key, 42)
        Setting.set(feature_key, False)
        SettingManager._memory_settings = {}
        assert Setting.get(max_items_key) == 42
        assert Setting.get(feature_key) is False

    def test_plain_string_rows_are_read_back_as_is(self, key):
        # Rows written before JSON encoding hold raw strings.
        DB.statement(
            "INSERT INTO settings (key, value) VALUES (?, ?)", [key, "Craft"]
        )
        assert Setting.get(key) == "Craft"


class TestModulePersistence:
    @pytest.fixture
    def seeded(self, slug):
        DB.statement(
            "INSERT INTO modules (name, slug, enabled) VALUES (?, ?, ?)",
            ["Billing", slug, True],
        )

    def _enabled_in_db(self, slug: str):
        row = DB.statement(
            "SELECT enabled FROM modules WHERE slug = ?", [slug], read=True
        ).fetchone()
        return bool(row["enabled"]) if row is not None else None

    def test_disable_writes_to_the_database(self, slug, seeded):
        Module.disable(slug)
        assert self._enabled_in_db(slug) is False

    def test_enable_writes_to_the_database(self, slug, seeded):
        Module.disable(slug)
        Module.enable(slug)
        assert self._enabled_in_db(slug) is True

    def test_is_enabled_reads_from_the_database(self, slug, seeded):
        DB.statement("UPDATE modules SET enabled = ? WHERE slug = ?", [False, slug])
        assert Module.is_enabled(slug) is False

    def test_all_lists_database_modules(self, slug, seeded):
        slugs = [m["slug"] for m in Module.all()]
        assert slug in slugs

    def test_enabling_an_unknown_module_reports_failure(self):
        # It used to return True unconditionally, so a typo in the slug looked
        # like a successful call.
        assert ModuleManager().enable("does-not-exist") is False

    def test_disabling_an_unknown_module_reports_failure(self):
        assert ModuleManager().disable("does-not-exist") is False

    def test_an_in_memory_module_can_still_be_toggled(self):
        manager = ModuleManager()
        manager.register("inmem", "In Memory")
        assert manager.disable("inmem") is True
        assert manager.is_enabled("inmem") is False

    def test_unknown_module_is_not_enabled(self):
        assert ModuleManager().is_enabled("does-not-exist") is False


class TestTenantSettings:
    def test_a_tenant_never_reads_another_tenants_value(self, key, tenants):
        from craft.orm.tenancy import TenantManager

        tenant_a, tenant_b = tenants

        with TenantManager().scope(tenant_a):
            Setting.set(key, "Alpha Funeral Home")
        with TenantManager().scope(tenant_b):
            assert Setting.get(key, "default") == "default"

    def test_a_tenant_falls_back_to_the_installation_value(self, key, tenants):
        from craft.orm.tenancy import TenantManager

        tenant_a, tenant_b = tenants

        Setting.set(key, "Installation")
        with TenantManager().scope(tenant_a):
            assert Setting.get(key) == "Installation"
            Setting.set(key, "Alpha")
            assert Setting.get(key) == "Alpha"
        assert Setting.get(key) == "Installation"

    def test_global_scope_writes_the_installation_value_from_a_tenant(self, key, tenants):
        from craft.orm.tenancy import TenantManager

        tenant_a, tenant_b = tenants

        with TenantManager().scope(tenant_a):
            Setting.set(key, "Everyone", global_scope=True)
        with TenantManager().scope(tenant_b):
            assert Setting.get(key) == "Everyone"
