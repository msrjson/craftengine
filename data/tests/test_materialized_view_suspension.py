"""With the opt-in on, the migrator suspends materialized views and restores them."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest

from engine.migrations.migrator import Migrator

VIEW = "craft_mv_suspension_test"
INDEX = "craft_mv_suspension_test_n"


def _app():
    from bootstrap.app import app

    return app


def _db():
    return _app().make("db")


def _exists(db) -> bool:
    return db.statement(f"SELECT to_regclass('{VIEW}') AS r", read=True).fetchone()["r"] is not None


def _create(db) -> None:
    db.statement(f"CREATE MATERIALIZED VIEW {VIEW} AS SELECT 1 AS n")
    db.statement(f"CREATE UNIQUE INDEX {INDEX} ON {VIEW} (n)")


def _indexes(db):
    rows = db.statement(
        "SELECT indexname FROM pg_indexes WHERE tablename = ?", [VIEW], read=True
    ).fetchall()
    return [row["indexname"] for row in rows]


def _cleanup(db) -> None:
    # The test's own throwaway view on the session database, never a shared
    # record - the suspension under test drops and recreates views the same way.
    db.statement(f"DROP MATERIALIZED VIEW IF EXISTS {VIEW}")  # nr02: the test's own view


def test_suspension_drops_the_views_and_restore_brings_them_back(
    migrated_database, is_postgres, monkeypatch
):
    if not is_postgres:
        pytest.skip("materialized views are PostgreSQL-only")
    db = _db()
    _create(db)
    try:
        migrator = Migrator(_app())
        monkeypatch.setattr(migrator, "_suspend_views_enabled", lambda: True)

        snapshot = migrator._suspend_materialized_views()
        assert VIEW in [view["matviewname"] for view in snapshot]
        assert _exists(db) is False

        migrator._restore_materialized_views(snapshot)
        assert _exists(db) is True
        assert INDEX in _indexes(db)
    finally:
        _cleanup(db)


def test_suspension_is_off_by_default(migrated_database, is_postgres):
    if not is_postgres:
        pytest.skip("materialized views are PostgreSQL-only")
    db = _db()
    _create(db)
    try:
        migrator = Migrator(_app())
        assert migrator._suspend_materialized_views() == []
        assert _exists(db) is True
    finally:
        _cleanup(db)
