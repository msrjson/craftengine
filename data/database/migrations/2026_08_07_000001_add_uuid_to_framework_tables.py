"""Add the public UUID identifier to the framework's own tables.

The integer `id` stays the primary key — narrow, sequential, fast to join. The
UUID is what you expose in URLs and APIs, so a public identifier never reveals
how many records exist or lets someone walk the table by incrementing a number.

Models fill it in automatically; see `Model.uses_uuid`.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import uuid as uuid_module

from craft.facades import DB
from craft.migrations import Migration, Schema

TABLES = ["users", "roles", "permissions", "modules"]


def up():
    for table in TABLES:
        # Added nullable and without an inline UNIQUE: SQLite rejects both a
        # NOT NULL and a UNIQUE constraint on ALTER TABLE ADD COLUMN. The
        # uniqueness comes from the index below.
        Schema.table(table, lambda t: t.uuid("uuid").nullable())

    # Backfill, or the column is useless for every row created before now.
    for table in TABLES:
        rows = DB.statement(f"SELECT id FROM {table} WHERE uuid IS NULL", read=True).fetchall()
        for row in rows:
            DB.statement(
                f"UPDATE {table} SET uuid = ? WHERE id = ?",
                [str(uuid_module.uuid4()), row["id"]],
            )

    for table in TABLES:
        DB.statement(f'CREATE UNIQUE INDEX IF NOT EXISTS "uniq_{table}_uuid" ON "{table}" ("uuid")')


def down():
    for table in TABLES:
        DB.statement(f'DROP INDEX IF EXISTS "uniq_{table}_uuid"')
        Schema.drop_column(table, "uuid")
