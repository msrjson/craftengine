"""Refusal of schema-wide destructive operations in every environment.

Category: Core Framework (Migrations).
Relations:
  - Called by `engine/migrations/migrator.py` before `drop_all_tables`, `reset`
    and `refresh`, which back `dev.py migrate fresh|reset|refresh` and
    `dev.py db wipe`.
References:
  - Standard: `.claude/rules/RELEASE_NON_REGRESSION_STANDARD.md` (NR-02)
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

from collections.abc import Iterable
from typing import Any
import os


class DestructiveOperationRefused(RuntimeError):
    """Raised when a schema-wide destructive operation targets a permanent database."""

    code = "DATABASE_DESTRUCTIVE_OPERATION_REFUSED"
    message_key = "database.safety.destructive_operation_refused"

    def __init__(self, operation: str, database: str, environment: str, reason: str | None = None) -> None:
        """Build the refusal.

        Args:
            operation: The refused operation, e.g. `drop_all_tables`.
            database: The target database name.
            environment: The application environment at refusal time.
            reason: Optional context beyond the environment, e.g. "the query
                builder is scoped to a tenant" for a refusal that has nothing
                to do with which environment is running.
        """
        detail = reason if reason is not None else environment
        super().__init__(f"{self.code}: {operation} on '{database}' ({detail})")
        self.params = {"operation": operation, "database": database, "environment": environment, "reason": reason}


def is_disposable_database(driver: str, database: str, allowlist: Iterable[str] = ()) -> bool:
    """Return false: database names and allowlists never authorize a wipe.

    Args:
        driver: Normalized driver name (`sqlite`, `postgresql`, `mysql`).
        database: The configured database name or SQLite path.
        allowlist: Extra database names declared disposable.

    Returns:
        Always false under the absolute persistence policy.
    """
    return False


def _config_value(app: Any, key: str, default: Any) -> Any:
    try:
        return app.make("config").get(key, default)
    except (AttributeError, KeyError):
        return default


def assert_disposable(app: Any, db: Any, operation: str) -> None:
    """Refuse a destructive schema operation regardless of database name.

    Args:
        app: The application container, used to read configuration.
        db: The database manager whose write connection is the target.
        operation: Name of the operation being attempted.

    Raises:
        DestructiveOperationRefused: Always.
    """
    environment = str(_config_value(app, "app.APP_ENV", os.environ.get("APP_ENV", "local")))
    database = str(db.write_connection.config.get("database") or "")
    raise DestructiveOperationRefused(operation, database, environment)
