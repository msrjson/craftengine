"""Database Manager for Craft Framework ORM.

Config-driven, multi-driver (SQLite / PostgreSQL / MySQL) connection manager with
read-write splitting, transactions and PostgreSQL schema-based multi-tenancy.

Category: Core Framework (ORM).
Relations:
  - Bound in the container as `db`, exposed via the `DB` facade; used by
    `engine/orm/model.py`, `engine/orm/query_builder.py`, and
    `engine/migrations/migrator.py`.
  - Wraps `engine/orm/connection.py` per configured connection.
References:
  - Guide: `documentation/orm.md#read-write-database-replicas`,
    `documentation/orm.md#multi-tenant-database-schema-isolation`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import os
import threading
from contextvars import ContextVar
from typing import Any, Callable, Dict, List, Optional

from engine.orm.connection import (
    Bindings,
    Connection,
    Row,
    StatementResult,
    assert_schema_identifier,
)

# Backwards-compatible aliases (previous sqlite-only API).
RowWrapper = Row
DatabaseStatementResult = StatementResult

_current_tenant_schema: ContextVar[Optional[str]] = ContextVar("_current_tenant_schema", default=None)
_request_query_log: ContextVar[Optional[List[str]]] = ContextVar("_request_query_log", default=None)


def get_request_query_log() -> Optional[List[str]]:
    return _request_query_log.get()


def start_query_logging() -> None:
    _request_query_log.set([])


def stop_query_logging() -> Optional[List[str]]:
    log = _request_query_log.get()
    _request_query_log.set(None)
    return log


class DatabaseManager:
    """Resolves and manages database connections from the application config."""

    def __init__(self, app: Optional[Any] = None, config: Optional[Dict[str, Any]] = None):
        self.app = app
        self.base_path = getattr(app, "base_path", None) or os.getcwd()
        self._connections: Dict[str, Connection] = {}
        self._default: Optional[str] = None
        self._write: Optional[Connection] = None
        self._read: Optional[Connection] = None
        self._explicit_config = config
        self._boot_lock = threading.RLock()
        self._booted = False
        #: table -> set of columns, invalidated whenever the connection changes.
        self._column_cache: Dict[str, set] = {}
        #: Known tenant schemas already validated/created in database
        self._known_tenant_schemas: set[str] = set()

    # -- configuration ---------------------------------------------------------

    def _config(self) -> Any:
        if self.app is not None:
            try:
                return self.app.make("config")
            except Exception:
                return None
        return None

    def _resolve_config(self, name: Optional[str] = None) -> Dict[str, Any]:
        if self._explicit_config is not None:
            return self._explicit_config

        config = self._config()
        if config is None:
            return {"driver": "sqlite", "database": ":memory:"}

        name = name or config.get("database.default") or "sqlite"
        self._default = name
        resolved = config.get(f"database.connections.{name}")
        if not isinstance(resolved, dict):
            return {"driver": "sqlite", "database": ":memory:"}
        return resolved

    @property
    def _tenant_schema(self) -> Optional[str]:
        return _current_tenant_schema.get()

    @_tenant_schema.setter
    def _tenant_schema(self, value: Optional[str]) -> None:
        _current_tenant_schema.set(value)

    def boot(self, name: Optional[str] = None) -> "DatabaseManager":
        """(Re)build the read/write connections from the current config."""
        with self._boot_lock:
            return self._boot(name)

    def _boot(self, name: Optional[str] = None) -> "DatabaseManager":
        self.forget_schema_cache()
        conn_config = dict(self._resolve_config(name))

        write_config = dict(conn_config)
        write_config.pop("read", None)
        write_config.pop("write", None)
        if isinstance(conn_config.get("write"), dict):
            write_config.update(conn_config["write"])

        self._write = Connection(write_config, self.base_path)

        if isinstance(conn_config.get("read"), dict):
            read_config = dict(conn_config)
            read_config.pop("read", None)
            read_config.pop("write", None)
            read_config.update(conn_config["read"])
            self._read = Connection(read_config, self.base_path)
        else:
            self._read = None

        self._booted = True
        if self._tenant_schema:
            self.set_tenant_schema(self._tenant_schema)
        return self

    # -- connections -----------------------------------------------------------

    @property
    def write_connection(self) -> Connection:
        # Double-checked under the boot lock: two threads arriving together
        # would otherwise each build a connection and one would be discarded
        # while already in use.
        if self._write is None:
            with self._boot_lock:
                if self._write is None:
                    self._boot()
        assert self._write is not None
        return self._write

    @property
    def read_connection(self) -> Connection:
        if not self._booted:
            with self._boot_lock:
                if not self._booted:
                    self._boot()
        return self._read or self.write_connection

    @property
    def driver(self) -> str:
        return self.write_connection.driver

    @property
    def dialect(self) -> Any:
        """What the active driver can be asked to do (`engine/orm/dialect.py`)."""
        return self.write_connection.dialect

    def connection(self, name: Optional[str] = None) -> Connection:
        """Get (and cache) a named connection from the config."""
        if name is None:
            return self.write_connection
        if name not in self._connections:
            with self._boot_lock:
                if name not in self._connections:
                    self._connections[name] = Connection(
                        self._resolve_config(name), self.base_path
                    )
        return self._connections[name]

    def release(self) -> None:
        """Return this thread's pooled connections at the end of a request.

        Called by the HTTP kernel once the response is built. Skipping it turns
        the pool into one permanent connection per thread, which is how a
        threaded server runs the database out of `max_connections`.
        """
        for connection in (self._write, self._read, *self._connections.values()):
            if connection is not None:
                connection.release()
        # The tenant schema is per-request state; leaving it set would let the
        # next request served by this thread inherit the previous tenant.
        self._tenant_schema = None

    def purge(self) -> None:
        """Close every open connection."""
        for connection in list(self._connections.values()):
            connection.close()
        self._connections.clear()
        if self._write is not None:
            self._write.close()
        if self._read is not None:
            self._read.close()
        self._write = self._read = None
        self._booted = False

    # -- statements ------------------------------------------------------------

    def statement(self, query: str, bindings: Bindings = None, read: bool = False) -> StatementResult:
        query_log = _request_query_log.get()
        if query_log is not None:
            query_log.append(query)
            count = query_log.count(query)
            if count == 10:
                import logging

                logging.getLogger("craft.orm").warning(
                    "Potential N+1 query detected (%d executions): %s", count, query
                )

        write = self.write_connection
        # Inside an open transaction, reads must see the transaction's own
        # writes — which are invisible to a separate read connection.
        if read and getattr(write, "_in_transaction", 0):
            read = False
        connection = self.read_connection if read else write
        return connection.statement(query, bindings)

    def select(self, query: str, bindings: Bindings = None) -> List[Row]:
        return self.statement(query, bindings, read=True).fetchall()

    def select_one(self, query: str, bindings: Bindings = None) -> Optional[Row]:
        return self.statement(query, bindings, read=True).fetchone()

    def insert(self, query: str, bindings: Bindings = None) -> StatementResult:
        return self.statement(query, bindings)

    def update(self, query: str, bindings: Bindings = None) -> int:
        return self.statement(query, bindings).rowcount

    def delete(self, query: str, bindings: Bindings = None) -> int:
        return self.statement(query, bindings).rowcount

    def insert_get_id(self, table: str, values: Dict[str, Any], key: str = "id") -> Any:
        """Insert a row and return its primary key across all supported drivers."""
        from engine.orm.query_builder import _assert_identifier

        _assert_identifier(table)
        _assert_identifier(key)
        columns = [_assert_identifier(c) for c in values.keys()]
        column_sql = ", ".join(f'"{c}"' if self.driver != "mysql" else f"`{c}`" for c in columns)
        placeholders = ", ".join(["?"] * len(columns))
        params = [values[c] for c in columns]
        table_sql = f'"{table}"' if self.driver != "mysql" else f"`{table}`"

        if self.driver == "postgresql":
            result = self.statement(
                f"INSERT INTO {table_sql} ({column_sql}) VALUES ({placeholders}) RETURNING {key}",
                params,
            )
            row = result.fetchone()
            return row[key] if row is not None else None

        result = self.statement(
            f"INSERT INTO {table_sql} ({column_sql}) VALUES ({placeholders})", params
        )

        # An explicitly supplied key wins. SQLite hands out a rowid even for a
        # table whose primary key is a UUID, so trusting lastrowid first
        # replaced the caller's UUID with an integer.
        if values.get(key) is not None:
            return values[key]
        if result.lastrowid:
            return result.lastrowid
        return None

    def table(self, table_name: str) -> Any:
        from engine.orm.query_builder import QueryBuilder

        return QueryBuilder(table_name=table_name, db=self)

    def table_exists(self, table: str) -> bool:
        return self.write_connection.table_exists(table)

    def table_has_column(self, table: str, column: str) -> bool:
        """Whether a table declares a column, cached per connection.

        The cache belongs here rather than on the model: a schema describes the
        connection, so swapping connections — a replica, a tenant schema, a test
        database — must invalidate it.
        """
        cache = self._column_cache.get(table)
        if cache is None:
            try:
                from engine.migrations.schema import SchemaBuilder

                cache = set(SchemaBuilder(self).column_listing(table))
            except Exception:
                # Do NOT cache the failure. A transient probe error — the table
                # not created yet, a connection blip mid-boot — used to be
                # memoised as "this table has no columns" for the life of the
                # process, which silently switched off every column-conditional
                # feature: `has_uuid_column()` stayed False, so the public UUID
                # the ORM advertises simply stopped being filled in.
                import logging

                logging.getLogger("craft").debug(
                    "Could not read the column list for %r; not caching the "
                    "result so a later call can retry.", table, exc_info=True,
                )
                return False

            self._column_cache[table] = cache
        return column in cache

    def forget_schema_cache(self, table: Optional[str] = None) -> None:
        if table is None:
            self._column_cache.clear()
        else:
            self._column_cache.pop(table, None)

    # -- transactions ----------------------------------------------------------

    def transaction(self, callback: Callable[[], Any]) -> Any:
        connection = self.write_connection
        connection.begin()
        try:
            result = callback()
            connection.commit()
            return result
        except Exception:
            connection.rollback()
            raise

    def begin_transaction(self) -> None:
        self.write_connection.begin()

    def commit(self) -> None:
        self.write_connection.commit()

    def rollback(self) -> None:
        self.write_connection.rollback()

    # -- multi-tenancy ---------------------------------------------------------

    def set_tenant_schema(self, schema_name: Optional[str] = None) -> None:
        """Point the connection at a tenant schema (PostgreSQL `search_path`)."""
        self._tenant_schema = schema_name
        # Each tenant schema has its own tables, so the column cache is stale.
        self.forget_schema_cache()
        if self.driver != "postgresql":
            return
        self.write_connection.use_schema(schema_name)
        if self._read is not None:
            self._read.use_schema(schema_name)

    def create_tenant_schema(self, schema_name: str) -> None:
        if self.driver != "postgresql":
            raise RuntimeError("Tenant schemas require the PostgreSQL driver.")
        assert_schema_identifier(schema_name)
        self.statement(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"')

    def ensure_tenant_schema(self, schema_name: str, owner: Any = None) -> bool:
        """Create the tenant schema and migrate it if it is new.

        Returns True when the schema was provisioned by this call. A no-op on
        drivers without schema support, so tenant-aware middleware can run
        unchanged against SQLite in development and tests.
        """
        if self.driver != "postgresql" or not schema_name:
            return False

        if schema_name in self._known_tenant_schemas:
            self.set_tenant_schema(schema_name)
            return False

        existing = self.statement(
            "SELECT schema_name FROM information_schema.schemata WHERE schema_name = ?",
            [schema_name],
            read=True,
        ).fetchone()
        if existing is not None:
            self._known_tenant_schemas.add(schema_name)
            self.set_tenant_schema(schema_name)
            return False

        self.create_tenant_schema(schema_name)
        self._known_tenant_schemas.add(schema_name)
        self.set_tenant_schema(schema_name)

        if self.app is not None:
            from engine.migrations.migrator import Migrator

            Migrator(self.app).run()
        return True

    # -- test / swap helpers ---------------------------------------------------

    def _swap(self, db_mgr: "DatabaseManager") -> None:
        self._write = db_mgr.write_connection
        self._read = db_mgr._read
        self._booted = True
        self.forget_schema_cache()

    def _clear_resolved(self) -> None:
        self._connections.clear()
