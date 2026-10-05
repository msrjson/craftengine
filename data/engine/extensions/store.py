"""Persisted lifecycle state of every extension: the `extensions` table.

The database is the source of truth, so a state set from the CLI or the
management panel is seen by every worker. Each write is mirrored in memory, so
an environment without the table yet (before `migrate`, a bare test) keeps
working for the life of the process instead of failing at boot.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

_LOG = logging.getLogger("craft.extensions")

TABLE = "extensions"


class ExtensionState(StrEnum):
    """Lifecycle state of an extension, as persisted."""

    DISCOVERED = "discovered"
    INSTALLED = "installed"
    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"
    UNINSTALLED = "uninstalled"


class ExtensionStore:
    """Read and write extension rows, falling back to memory without a table.

    Args:
        db: Zero-argument callable returning the database manager; called on
            each access so the store never holds a connection. None keeps the
            state in memory only (an isolated test, a dry run).
    """

    def __init__(self, db: Callable[[], Any] | None) -> None:
        self._db = db
        self._memory: dict[str, dict[str, Any]] = {}

    def get(self, slug: str) -> dict[str, Any] | None:
        """Return the row of `slug`, or None when it was never recorded."""
        if self._db is None:
            return self._memory.get(slug)
        try:
            row = self._db().table(TABLE).where("slug", slug).first()
        except Exception:  # noqa: BLE001 - no table yet: memory is the answer
            _LOG.debug("extension_store_read_fallback slug=%s", slug, exc_info=True)
            row = None
        return _as_dict(row) if row is not None else self._memory.get(slug)

    def all(self) -> dict[str, dict[str, Any]]:
        """Return every recorded extension, keyed by slug."""
        rows = dict(self._memory)
        if self._db is None:
            return rows
        try:
            rows.update({str(_as_dict(row)["slug"]): _as_dict(row) for row in self._db().table(TABLE).get()})
        except Exception:  # noqa: BLE001 - no table yet: memory is the answer
            _LOG.debug("extension_store_list_fallback", exc_info=True)
        return rows

    def state(self, slug: str) -> ExtensionState:
        """Return the persisted state of `slug`, `DISCOVERED` when unrecorded."""
        row = self.get(slug)
        return ExtensionState(row["state"]) if row else ExtensionState.DISCOVERED

    def save(self, slug: str, kind: str, version: str, state: ExtensionState, path: str = "") -> None:
        """Insert or update the row of `slug` with its new state."""
        now = datetime.now(UTC).isoformat()
        values = {"kind": kind, "version": version, "state": state.value, "path": path, "updated_at": now}
        self._memory[slug] = {"slug": slug, **values}
        if self._db is None:
            return
        try:
            table = self._db().table(TABLE)
            if table.where("slug", slug).first() is None:
                self._db().table(TABLE).insert({"slug": slug, "created_at": now, **values})
            else:
                self._db().table(TABLE).where("slug", slug).update(values)
        except Exception:  # noqa: BLE001 - kept in memory; logged so it is not silent
            _LOG.warning("extension_state_not_persisted slug=%s state=%s (has migrate run?)", slug, state.value, exc_info=True)


def _as_dict(row: Any) -> dict[str, Any]:
    """Return a database row as a plain dict, whatever the driver returned."""
    return dict(row) if not isinstance(row, dict) else row


__all__ = ["ExtensionState", "ExtensionStore", "TABLE"]
