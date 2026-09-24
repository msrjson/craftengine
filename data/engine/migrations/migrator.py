"""Migration runner for Craft Framework.

Discovers migration files in `database/migrations`, tracks applied migrations in
a `migrations` table with batch numbers, and supports run / rollback / reset /
refresh / fresh / status - mirroring the framework's migrator semantics.

Category: Core Framework (Migrations).
Relations:
  - Bound as `migrator`, exposed via the `Migrator` facade and the
    `dev.py migrate*` CLI commands (`engine/cli/app.py`).
  - Drives `engine/migrations/schema.py` and reads/writes through
    `engine/orm/connection.py`.
References:
  - Guide: `documentation/migrations.md`, `documentation/cli.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import importlib.util
import os
import re
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from engine.migrations.safety import assert_disposable

MIGRATION_FILE_RE = re.compile(r"^\d{4}_\d{2}_\d{2}_\d{6}_[\w]+\.py$")


class MigrationLockTimeout(RuntimeError):
    """Another process held the migration lock for longer than allowed."""

    code = "MIGRATION_LOCK_TIMEOUT"
    message_key = "database.migration.lock_timeout"

    def __init__(self, seconds: float):
        super().__init__(self.code)
        self.seconds = seconds


class Migration:
    """Base class for class-style migrations.

    Both class-style (``class CreateUsersTable(Migration)`` with ``up``/``down``
    methods) and function-style (module level ``up()`` / ``down()``) migrations
    are supported.
    """

    def up(self) -> None:  # pragma: no cover - overridden by user migrations
        raise NotImplementedError

    def down(self) -> None:  # pragma: no cover - overridden by user migrations
        raise NotImplementedError


class MigrationFile:
    """A discovered migration on disk."""

    def __init__(self, path: str):
        self.path = path
        self.name = os.path.splitext(os.path.basename(path))[0]
        self._module: Any = None

    @property
    def module(self) -> Any:
        if self._module is None:
            spec = importlib.util.spec_from_file_location(
                f"database.migrations.{self.name}", self.path
            )
            if spec is None or spec.loader is None:
                raise ImportError(f"Cannot load migration [{self.name}].")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self._module = module
        return self._module

    def _resolve(self, direction: str) -> Optional[Callable[[], Any]]:
        module = self.module

        # Class-style migration takes precedence.
        for attr in vars(module).values():
            if (
                isinstance(attr, type)
                and issubclass(attr, Migration)
                and attr is not Migration
            ):
                instance = attr()
                method = getattr(instance, direction, None)
                if callable(method):
                    return method

        method = getattr(module, direction, None)
        return method if callable(method) else None

    @property
    def transactional(self) -> bool:
        """Whether this migration may be wrapped in a transaction.

        Set `transactional = False` at module level for DDL PostgreSQL refuses
        inside a transaction block - `CREATE INDEX CONCURRENTLY`,
        `ALTER TYPE … ADD VALUE`. Such a migration has to be written to be
        re-runnable, because a failure leaves it half applied with no rollback.
        """
        return bool(getattr(self.module, "transactional", True))

    def run(self, direction: str = "up") -> None:
        method = self._resolve(direction)
        if method is None:
            if direction == "down":
                return  # irreversible migration - nothing to undo
            raise AttributeError(f"Migration [{self.name}] has no `{direction}()`.")
        method()


class Migrator:
    """Runs and reverts migrations against the application database."""

    TABLE = "migrations"

    def __init__(self, app: Any = None, path: Optional[str] = None):
        self.app = app
        base_path = getattr(app, "base_path", None) or os.getcwd()
        self.path = path or os.path.join(base_path, "database", "migrations")
        self.notes: List[str] = []

    # -- infrastructure --------------------------------------------------------

    @property
    def db(self) -> Any:
        if self.app is not None:
            return self.app.make("db")
        from engine.container.application import Container

        return Container.getInstance().make("db")

    def ensure_repository(self) -> None:
        """Create the migrations tracking table if it does not exist."""
        driver = getattr(self.db, "driver", "sqlite")
        if driver == "postgresql":
            pk = "SERIAL PRIMARY KEY"
        elif driver == "mysql":
            pk = "INT AUTO_INCREMENT PRIMARY KEY"
        else:
            pk = "INTEGER PRIMARY KEY AUTOINCREMENT"
        self.db.statement(
            f"""CREATE TABLE IF NOT EXISTS {self.TABLE} (
                id {pk},
                migration VARCHAR(255) NOT NULL,
                batch INTEGER NOT NULL,
                applied_at VARCHAR(64)
            )"""
        )

    def applied(self) -> List[str]:
        self.ensure_repository()
        rows = self.db.statement(
            f"SELECT migration FROM {self.TABLE} ORDER BY batch ASC, id ASC"
        ).fetchall()
        return [row["migration"] for row in rows]

    def last_batch(self) -> int:
        self.ensure_repository()
        row = self.db.statement(f"SELECT MAX(batch) AS b FROM {self.TABLE}").fetchone()
        value = row["b"] if row is not None else None
        return int(value or 0)

    def _log(self, migration: str, batch: int) -> None:
        self.db.statement(
            f"INSERT INTO {self.TABLE} (migration, batch, applied_at) VALUES (?, ?, ?)",
            [migration, batch, datetime.now(timezone.utc).isoformat()],
        )

    def _forget(self, migration: str) -> None:
        self.db.statement(f"DELETE FROM {self.TABLE} WHERE migration = ?", [migration])

    # -- discovery -------------------------------------------------------------

    def files(self) -> List[MigrationFile]:
        if not os.path.isdir(self.path):
            return []
        names = sorted(
            name
            for name in os.listdir(self.path)
            if MIGRATION_FILE_RE.match(name)
        )
        return [MigrationFile(os.path.join(self.path, name)) for name in names]

    def pending(self) -> List[MigrationFile]:
        applied = set(self.applied())
        return [f for f in self.files() if f.name not in applied]

    # -- operations ------------------------------------------------------------

    def run(self, step: Optional[int] = None, pretend: bool = False) -> List[str]:
        """Apply all pending migrations. Returns the names that ran."""
        return self.with_lock(lambda: self._run(step, pretend))

    #: One lock for the whole migrator, so `migrate` and `rollback` cannot
    #: interleave either.
    LOCK_KEY = "craft:migrations"

    def with_lock(self, callback: Callable[[], Any]) -> Any:
        """Run `callback` as the only migrator touching this database.

        Production images run migrations at container start, so a deployment
        that replaces three containers runs three migrators against one
        database within the same second. Each reads the same pending list and
        applies it, and the second one fails somewhere in the middle with a
        half-built schema.

        A session-scoped advisory lock rather than a transactional one: the
        migrations themselves open and close transactions, and some (a
        concurrent index build) cannot run inside one at all. Waiting is the
        right behaviour, not failing: the loser wakes up when the winner
        finishes and finds nothing pending, which is what makes every container
        able to run the same command.
        """
        db = self.db
        try:
            supported = db.dialect.supports("advisory_locks")
        except Exception:
            supported = False
        if not supported:
            # SQLite and MySQL: no advisory locks, and no deployment shape that
            # needs them here. Running unlocked is the previous behaviour.
            return callback()

        from engine.orm.locks import LockManager

        timeout = self._lock_timeout()
        handle = LockManager(self.app).key(self.LOCK_KEY)
        if timeout > 0:
            handle = handle.block_for(timeout)
        if not handle.acquire():
            raise MigrationLockTimeout(timeout)
        try:
            return callback()
        finally:
            try:
                handle.release()
            except Exception:
                pass

    def _lock_timeout(self) -> float:
        try:
            return float(self.app.make("config").get("framework.MIGRATION_LOCK_TIMEOUT", 120))
        except Exception:
            return 120.0

    def _run(self, step: Optional[int] = None, pretend: bool = False) -> List[str]:
        self.ensure_repository()
        pending = self.pending()
        if step:
            pending = pending[:step]
        if not pending:
            self.notes.append("Nothing to migrate.")
            return []

        batch = self.last_batch() + 1
        applied: List[str] = []
        for migration in pending:
            if pretend:
                self.notes.append(f"[pretend] would migrate {migration.name}")
                applied.append(migration.name)
                continue
            self._apply(migration, "up", batch)
            self.notes.append(f"Migrated:  {migration.name}")
            applied.append(migration.name)
        return applied

    def _apply(self, migration: MigrationFile, direction: str, batch: int) -> None:
        """Run one migration and record it - as a single unit of work.

        A migration is one decision, and its ledger row belongs inside it.
        Running the statements one at a time (each auto-committing, which is
        what `Connection.statement` does outside a transaction) meant a failure
        on statement four of seven left a half-built schema and no ledger row
        to say so - the worst possible state to recover from. PostgreSQL and
        SQLite both roll back DDL, so this costs nothing where it works and is
        skipped where it does not.
        """
        def work() -> None:
            migration.run(direction)
            if direction == "up":
                self._log(migration.name, batch)
            else:
                self._forget(migration.name)

        if migration.transactional and self.db.dialect.supports("transactional_ddl"):
            self.db.transaction(work)
        else:
            work()

    def rollback(self, step: int = 1) -> List[str]:
        """Revert the last `step` batches."""
        assert_disposable(self.app, self.db, "rollback")
        return self.with_lock(lambda: self._rollback(step))

    def _rollback(self, step: int = 1) -> List[str]:
        assert_disposable(self.app, self.db, "rollback")
        self.ensure_repository()
        batch = self.last_batch()
        if batch == 0:
            self.notes.append("Nothing to rollback.")
            return []

        target_batches = list(range(batch, max(batch - step, 0), -1))
        by_name = {f.name: f for f in self.files()}
        reverted: List[str] = []

        for current in target_batches:
            rows = self.db.statement(
                f"SELECT migration FROM {self.TABLE} WHERE batch = ? ORDER BY id DESC",
                [current],
            ).fetchall()
            for row in rows:
                name = row["migration"]
                migration = by_name.get(name)
                if migration is None:
                    # Deleting the ledger row without running down() would
                    # silently strand the schema - keep it and tell the user.
                    self.notes.append(f"Migration file missing, skipped:  {name}")
                    continue
                self._apply(migration, "down", current)
                self.notes.append(f"Rolled back:  {name}")
                reverted.append(name)
        return reverted

    def reset(self) -> List[str]:
        """Revert every applied migration.

        Raises:
            DestructiveOperationRefused: When the database is not disposable.
        """
        assert_disposable(self.app, self.db, "reset")
        return self.rollback(step=self.last_batch() or 1)

    def refresh(self) -> List[str]:
        """Reset then re-run all migrations."""
        self.reset()
        return self.run()

    def fresh(self) -> List[str]:
        """Drop every table then re-run all migrations."""
        self.drop_all_tables()
        return self.run()

    def status(self) -> List[Dict[str, Any]]:
        self.ensure_repository()
        rows = self.db.statement(
            f"SELECT migration, batch FROM {self.TABLE}"
        ).fetchall()
        batches = {row["migration"]: row["batch"] for row in rows}
        return [
            {
                "migration": f.name,
                "ran": f.name in batches,
                "batch": batches.get(f.name),
            }
            for f in self.files()
        ]

    def drop_all_tables(self) -> None:
        """Drop every table in the current schema.

        Raises:
            DestructiveOperationRefused: When the database is not disposable.
        """
        assert_disposable(self.app, self.db, "drop_all_tables")
        driver = getattr(self.db, "driver", "sqlite")
        if driver == "sqlite":
            rows = self.db.statement(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
            tables = [row["name"] for row in rows]
            self.db.statement("PRAGMA foreign_keys = OFF")
            for table in tables:
                self.db.statement(f'DROP TABLE IF EXISTS "{table}"')
            self.db.statement("PRAGMA foreign_keys = ON")
        elif driver == "postgresql":
            rows = self.db.statement(
                "SELECT tablename FROM pg_tables WHERE schemaname = current_schema()"
            ).fetchall()
            for row in rows:
                self.db.statement(f'DROP TABLE IF EXISTS "{row["tablename"]}" CASCADE')
        else:
            rows = self.db.statement(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE()"
            ).fetchall()
            self.db.statement("SET FOREIGN_KEY_CHECKS = 0")
            for row in rows:
                self.db.statement(f'DROP TABLE IF EXISTS `{row["table_name"]}`')
            self.db.statement("SET FOREIGN_KEY_CHECKS = 1")


def make_migration_stub(name: str, table: Optional[str] = None, create: bool = True) -> str:
    """Return the source of a new migration file."""
    table = table or name
    if create:
        body = f'''def up():
    Schema.create_table("{table}", lambda t: (
        t.id(),
        t.timestamps(),
    ))


def down():
    Schema.drop_table("{table}")
'''
    else:
        body = f'''def up():
    Schema.table("{table}", lambda t: (
        t.string("new_column").nullable(),
    ))


def down():
    Schema.drop_column("{table}", "new_column")
'''
    return f'"""Migration: {name}."""\n\nfrom craft.migrations import Migration, Schema\n\n\n{body}'


def migration_filename(name: str, when: Optional[datetime] = None) -> str:
    stamp = (when or datetime.now()).strftime("%Y_%m_%d_%H%M%S")
    return f"{stamp}_{name}.py"
