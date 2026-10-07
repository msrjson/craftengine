"""A tenant overrides a translation; the global row is the fallback."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import uuid

from craft.orm.tenancy import TenantManager, current_tenant_id
from craft.support import translation

_SUFFIX = uuid.uuid4().hex[:8]
KEY = f"demo.tenant_override_{_SUFFIX}"
#: A real UUID: `tenant_id` is a uuid column on PostgreSQL, and a made-up
#: string there is a type error, not a tenant that happens to have no rows.
TENANT = str(uuid.uuid4())


def _seed_rows(app):
    db = app.make("db")
    db.table("translations").insert({"key": KEY, "locale": "en", "value": "Global copy"})
    db.table("translations").insert({
        "key": KEY, "locale": "en", "value": "Tenant copy", "tenant_id": TENANT,
    })


def _translated(app, locale="en"):
    translation.clear_translation_cache()
    return translation.translate(KEY, locale=locale)


def test_without_a_bound_tenant_the_global_row_is_used(migrated_database):
    _seed_rows(migrated_database)
    TenantManager(migrated_database).bind(None)
    assert _translated(migrated_database) == "Global copy"


def test_a_bound_tenant_overrides_the_global_row(migrated_database):
    TenantManager(migrated_database).bind(TENANT)
    try:
        assert current_tenant_id() == TENANT
        assert _translated(migrated_database) == "Tenant copy"
    finally:
        TenantManager(migrated_database).bind(None)


def test_another_tenant_still_reads_the_global_row(migrated_database):
    TenantManager(migrated_database).bind(str(uuid.uuid4()))
    try:
        assert _translated(migrated_database) == "Global copy"
    finally:
        TenantManager(migrated_database).bind(None)


def test_a_key_with_no_override_falls_back_for_everyone(migrated_database):
    other = f"demo.no_override_{_SUFFIX}"
    migrated_database.make("db").table("translations").insert(
        {"key": other, "locale": "en", "value": "Shared copy"}
    )
    TenantManager(migrated_database).bind(TENANT)
    try:
        translation.clear_translation_cache()
        assert translation.translate(other, locale="en") == "Shared copy"
    finally:
        TenantManager(migrated_database).bind(None)
