"""Migration: the unique index `translations` needs to key `(key, locale)`.

`Translation._fetch_bundle()` builds `{key: value}` from every row of a locale,
so two rows with the same `(key, locale)` silently overwrite each other and the
last one wins. The table was created without the constraint its own seeders
already assume - each one pre-checks for an existing row before inserting - so a
seed mistake or a concurrent admin edit changed displayed copy with no error.

Category: Framework schema (localization).
References:
  - `engine/support/translation.py:94-102` (`_fetch_bundle`).
  - `database/migrations/2025_01_01_000004_create_framework_dynamic_tables.py`
    creates the table this migration completes.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.facades import DB, Schema


def up():
    # A duplicate would make CREATE UNIQUE INDEX fail, and NR-02 forbids
    # deleting a translation row to force it through: ask for a deliberate,
    # non-destructive reconciliation instead.
    duplicate = DB.statement("""
        SELECT key, locale
        FROM translations
        GROUP BY key, locale
        HAVING COUNT(*) > 1
        LIMIT 1
    """).fetchone()
    if duplicate is not None:
        raise RuntimeError("Duplicate translation (key, locale) rows require non-destructive reconciliation.")
    Schema.table("translations", lambda t: (
        t.unique_index(["key", "locale"], name="uq_translations_key_locale"),
    ))


def down():
    raise RuntimeError("This migration is forward-only.")
