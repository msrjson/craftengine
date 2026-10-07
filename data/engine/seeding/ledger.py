"""Seed ledger: the record of seeds that may run exactly once per node.

A seeder that is idempotent by `first_or_create` is only idempotent while the row
it looks for still exists unchanged. A catalog the owner edited no longer matches
the factory value, so the next `release:sync` inserts a second copy. A seeder
that must never run twice declares `SEED_ONCE` and is recorded here instead:

    class PlatformCatalogSeeder(Seeder):
        SEED_ONCE = "platform_catalog"   # or True, keyed by the class name

Nothing here deletes: the ledger is the proof of what already ran.

Category: Core Framework (Seeding).
Relations:
  - Consulted by `run_seeder()` and `Seeder.call()` (`engine/seeding/__init__.py`).
References:
  - Guide: `documentation/migrations.md#seeders`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import uuid as _uuid
from datetime import datetime, timezone
from typing import Any, Optional, Type

TABLE = "seed_ledger"


class SeedLedger:
    """Read and append the once-only seed record."""

    def __init__(self, app: Any = None):
        self.app = app

    def _db(self) -> Any:
        if self.app is not None:
            return self.app.make("db")
        from engine.container.application import Container

        return Container.getInstance().make("db")

    def _table_exists(self) -> bool:
        # Before the migration runs (a bare `db seed` on a fresh checkout) there
        # is no ledger yet: nothing can have been recorded, so a once-only seed
        # is allowed to run and simply not recorded.
        from engine.migrations.schema import Schema

        return Schema.has_table(TABLE)

    def has(self, key: str) -> bool:
        """Whether `key` has already been seeded on this node."""
        if not self._table_exists():
            return False
        row = self._db().statement(
            f'SELECT 1 AS ok FROM {TABLE} WHERE "key" = ? LIMIT 1', [key], read=True
        ).fetchone()
        return row is not None

    def record(self, key: str, version: Optional[str] = None, note: Optional[str] = None) -> bool:
        """Append `key`. Returns False when there is no ledger to write to."""
        if not self._table_exists():
            return False
        now = datetime.now(timezone.utc)
        self._db().statement(
            f'INSERT INTO {TABLE} (uuid, "key", version, note, seeded_at, created_at, updated_at) '
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [str(_uuid.uuid4()), key, version, note, now, now, now],
        )
        return True


def once_key(seeder_class: Type[Any]) -> Optional[str]:
    """The ledger key a seeder declares, or None when it is not once-only.

    `SEED_ONCE = True` keys on the seeder's module and class name; a string keys
    on that string, so a seed can be locked under a stable name of its own.
    """
    marker = getattr(seeder_class, "SEED_ONCE", None)
    if not marker:
        return None
    if marker is True:
        return f"{seeder_class.__module__}.{seeder_class.__name__}"
    return str(marker)


__all__ = ["TABLE", "SeedLedger", "once_key"]
