"""Migrator: discovery, batches, rollback, status."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import os
import textwrap

import pytest

from craft.container.application import Application
from craft.migrations.migrator import Migrator, migration_filename
from craft.migrations.safety import DestructiveOperationRefused
from craft.orm.db import DatabaseManager

MIGRATION_A = '''
from craft.migrations import Schema

def up():
    Schema.create_table("alpha", lambda t: (t.id(), t.string("name")))

def down():
    Schema.drop_table("alpha")  # nr02: down() of a migration run on a private in-memory SQLite
'''

MIGRATION_B = '''
from craft.migrations import Schema

def up():
    Schema.create_table("beta", lambda t: (t.id(), t.string("label")))

def down():
    Schema.drop_table("beta")  # nr02: down() of a migration run on a private in-memory SQLite
'''


@pytest.fixture
def migrator(tmp_path):
    """A migrator over a throwaway sqlite DB and a throwaway migration dir.

    This scratch Application must not become the global container — the real
    app booted first, and every other test resolves its models through
    `Container.getInstance()`. `bind_as_global=False` makes that explicit.
    """
    migrations_dir = tmp_path / "database" / "migrations"
    migrations_dir.mkdir(parents=True)
    (migrations_dir / "2025_01_01_000001_create_alpha.py").write_text(
        textwrap.dedent(MIGRATION_A), encoding="utf-8"
    )
    (migrations_dir / "2025_01_01_000002_create_beta.py").write_text(
        textwrap.dedent(MIGRATION_B), encoding="utf-8"
    )

    app = Application(str(tmp_path), bind_as_global=False)
    db = DatabaseManager(app, config={"driver": "sqlite", "database": ":memory:"})
    app.instance("db", db)

    from craft.migrations.schema import SchemaBuilder

    app.instance("schema", SchemaBuilder(db))
    # Migration files call the module-level Schema singleton.
    import craft.migrations.schema as schema_module

    schema_module.Schema._db = db

    yield Migrator(app, path=str(migrations_dir))

    schema_module.Schema._db = None


class TestDiscovery:
    def test_finds_migration_files_in_order(self, migrator):
        names = [f.name for f in migrator.files()]
        assert names == [
            "2025_01_01_000001_create_alpha",
            "2025_01_01_000002_create_beta",
        ]

    def test_all_are_pending_before_running(self, migrator):
        assert len(migrator.pending()) == 2

    def test_filename_is_timestamped(self):
        name = migration_filename("create_widgets_table")
        assert name.endswith("_create_widgets_table.py")
        assert len(name.split("_")[0]) == 4  # year


class TestRunning:
    def test_run_applies_every_pending_migration(self, migrator):
        applied = migrator.run()
        assert len(applied) == 2
        assert migrator.db.table_exists("alpha")
        assert migrator.db.table_exists("beta")

    def test_run_is_idempotent(self, migrator):
        migrator.run()
        assert migrator.run() == []
        assert "Nothing to migrate." in migrator.notes

    def test_step_limits_how_many_run(self, migrator):
        applied = migrator.run(step=1)
        assert len(applied) == 1
        assert migrator.db.table_exists("alpha")
        assert not migrator.db.table_exists("beta")

    def test_pretend_does_not_touch_the_database(self, migrator):
        migrator.run(pretend=True)
        assert not migrator.db.table_exists("alpha")

    def test_migrations_share_one_batch(self, migrator):
        migrator.run()
        assert migrator.last_batch() == 1

    def test_a_second_run_opens_a_new_batch(self, migrator, tmp_path):
        migrator.run(step=1)
        migrator.run()
        assert migrator.last_batch() == 2


class TestRollback:
    def test_rollback_is_refused_after_migration(self, migrator):
        migrator.run()
        with pytest.raises(DestructiveOperationRefused):
            migrator.rollback()
        assert migrator.db.table_exists("alpha")
        assert migrator.db.table_exists("beta")

    def test_rollback_is_refused_even_with_nothing_applied(self, migrator):
        with pytest.raises(DestructiveOperationRefused):
            migrator.rollback()

    def test_reset_preserves_everything(self, migrator):
        migrator.run(step=1)
        migrator.run()
        with pytest.raises(DestructiveOperationRefused):
            migrator.reset()
        assert len(migrator.applied()) == 2

    def test_refresh_is_refused(self, migrator):
        migrator.run()
        with pytest.raises(DestructiveOperationRefused):
            migrator.refresh()
        assert len(migrator.applied()) == 2
        assert migrator.db.table_exists("alpha")


class TestStatus:
    def test_status_marks_pending_and_applied(self, migrator):
        migrator.run(step=1)
        status = {row["migration"]: row for row in migrator.status()}
        assert status["2025_01_01_000001_create_alpha"]["ran"] is True
        assert status["2025_01_01_000002_create_beta"]["ran"] is False

    def test_repository_table_is_created_on_demand(self, migrator):
        migrator.ensure_repository()
        assert migrator.db.table_exists("migrations")

    def test_drop_all_tables_is_refused(self, migrator):
        migrator.run()
        with pytest.raises(DestructiveOperationRefused):
            migrator.drop_all_tables()
        assert migrator.db.table_exists("alpha")
        assert migrator.db.table_exists("migrations")
