"""Migration: a tenant may override a translation row.

Copy that differs per tenant - a product name, a legal notice, a tax label -
could only live in a second `translations` table, and shipping one meant the
framework's own `__()` never saw it. Adding `tenant_id` lets a tenant override
a global row with its own, and `_fetch_bundle()` prefers the tenant's row over
the global one.

The table's `(key, locale)` unique index predates this and would reject the
override row that shares both columns with the global one, so it is replaced by
two partial indexes: one enforcing a single global row per `(key, locale)`, one
enforcing a single row per `(tenant_id, key, locale)`. Only an index changes;
no row is touched.

Category: Framework schema (localization).
References:
  - `engine/support/translation.py` (`_fetch_bundle`, `_lookup`).
  - `database/migrations/2026_10_07_000001_unique_index_on_translations.py`.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.facades import DB, Schema


def up():
    Schema.table("translations", lambda t: (
        t.uuid("tenant_id").nullable(),
        t.index_on(["tenant_id"], name="idx_translations_tenant_id"),
    ))

    # Replace the global uniqueness with two partial indexes so a tenant row
    # and the global row can share `(key, locale)`. `IF EXISTS` keeps the
    # migration runnable on a database where the earlier index is already gone.
    DB.statement('DROP INDEX IF EXISTS "uq_translations_key_locale"')
    Schema.table("translations", lambda t: (
        t.index_on(
            ["key", "locale"],
            name="uq_translations_key_locale_global",
            unique=True,
            where="tenant_id IS NULL",
        ),
        t.index_on(
            ["tenant_id", "key", "locale"],
            name="uq_translations_key_locale_tenant",
            unique=True,
            where="tenant_id IS NOT NULL",
        ),
    ))


def down():
    raise RuntimeError("This migration is forward-only.")
