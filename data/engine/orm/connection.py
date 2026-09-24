"""Database connection layer for Craft Framework.

Provides a driver-agnostic connection wrapper over sqlite3, psycopg2 (PostgreSQL)
and PyMySQL/mysqlclient (MySQL), normalising placeholders and row access so the
rest of the framework can speak a single dialect-neutral SQL flavour.

Category: Core Framework (ORM).
Relations:
  - Wrapped by `DatabaseManager` (`engine/orm/db.py`), which owns
    read/write splitting and multi-tenant schema switching.
  - No SQLAlchemy or other ORM layer sits underneath this - it talks to the
    driver libraries directly.
References:
  - Guide: `documentation/orm.md`, `documentation/configuration.md#database-connections`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import logging
import os
import re
import sqlite3
import threading
import time
import weakref
from typing import Any, Dict, List, Optional, Sequence, Union

Bindings = Union[Sequence[Any], Dict[str, Any], None]

_SCHEMA_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def assert_schema_identifier(name: str) -> str:
    """Reject schema names that could break out of the quoted identifier.

    Postgres schema/search_path values here are built with an f-string, not a
    bound parameter (`SET search_path` cannot take one) - so a tenant name
    such as `a", public; DROP SCHEMA public CASCADE; --` must be rejected
    before it ever reaches the string, not just quoted.
    """
    if not isinstance(name, str) or not _SCHEMA_IDENTIFIER_RE.match(name):
        raise ValueError(f"Invalid schema identifier [{name!r}].")
    return name


class Row:
    """Dict-like row supporting attribute, key and positional access."""

    __slots__ = ("_data",)

    def __init__(self, data: Dict[str, Any]):
        object.__setattr__(self, "_data", dict(data))

    def __getattr__(self, name: str) -> Any:
        data = object.__getattribute__(self, "_data")
        if name in data:
            return data[name]
        raise AttributeError(f"'Row' object has no attribute '{name}'")

    def __getitem__(self, item: Any) -> Any:
        if isinstance(item, str):
            return self._data[item]
        return list(self._data.values())[item]

    def __contains__(self, item: Any) -> bool:
        return item in self._data

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()

    def to_dict(self) -> Dict[str, Any]:
        return dict(self._data)

    def __iter__(self):
        return iter(self._data.items())

    def __len__(self) -> int:
        return len(self._data)

    def __repr__(self) -> str:
        return f"Row({self._data!r})"


class StatementResult:
    """Result of an executed statement."""

    def __init__(self, rows: List[Row], rowcount: int = 0, lastrowid: Any = None):
        self._rows = rows
        self.rowcount = rowcount
        self.lastrowid = lastrowid
        self._cursor_pos = 0

    def fetchall(self) -> List[Row]:
        rows = self._rows[self._cursor_pos:]
        self._cursor_pos = len(self._rows)
        return rows

    def fetchone(self) -> Optional[Row]:
        if self._cursor_pos < len(self._rows):
            row = self._rows[self._cursor_pos]
            self._cursor_pos += 1
            return row
        return None

    def __iter__(self):
        return iter(self._rows)

    def __len__(self) -> int:
        return len(self._rows)


class ConnectionError_(Exception):
    """Raised when a database connection cannot be established."""


class TransactionRolledBackError(Exception):
    """Raised by the outermost `commit()` after an inner level rolled back."""

    code = "DB_TRANSACTION_ROLLED_BACK"
    message_key = "database.transaction.rolled_back"

    def __init__(self) -> None:
        super().__init__(self.code)


# --- placeholder normalisation -------------------------------------------------

_NAMED_RE = re.compile(r"(?<![:\w]):([a-zA-Z_]\w*)")
_STRING_RE = re.compile(r"'(?:[^']|'')*'")


def _protect_strings(sql: str):
    """Replace string literals with tokens so placeholder rewriting skips them."""
    literals: List[str] = []

    def _stash(match: "re.Match[str]") -> str:
        literals.append(match.group(0))
        return f"\x00{len(literals) - 1}\x00"

    return _STRING_RE.sub(_stash, sql), literals


def _restore_strings(sql: str, literals: List[str]) -> str:
    for index, literal in enumerate(literals):
        sql = sql.replace(f"\x00{index}\x00", literal)
    return sql


def normalize_placeholders(sql: str, bindings: Bindings, paramstyle: str):
    """Translate `?` / `:name` placeholders into the driver's paramstyle.

    Returns the rewritten SQL and the bindings shaped for that driver.
    """
    if paramstyle == "qmark":  # sqlite3 understands both forms natively
        return sql, bindings if bindings is not None else []

    if bindings:
        # With parameters the driver formats the query, so every literal `%`
        # (`LIKE 'a%'`, `id % 2`) must be doubled or it is read as a
        # placeholder. Without parameters the query is sent verbatim.
        sql = sql.replace("%", "%%")
    protected, literals = _protect_strings(sql)

    if isinstance(bindings, dict):
        if paramstyle == "pyformat":
            protected = _NAMED_RE.sub(lambda m: f"%({m.group(1)})s", protected)
            return _restore_strings(protected, literals), bindings
        # format-style drivers need positional args in appearance order
        order: List[str] = []

        def _to_pos(match: "re.Match[str]") -> str:
            order.append(match.group(1))
            return "%s"

        protected = _NAMED_RE.sub(_to_pos, protected)
        return _restore_strings(protected, literals), [bindings[name] for name in order]

    protected = protected.replace("?", "%s")
    return _restore_strings(protected, literals), list(bindings or [])


class _Session:
    """The state that belongs to one physical database connection.

    Transaction depth and the active tenant schema are properties *of a
    connection*, not of the `Connection` object - which is shared by every
    thread. Keeping them together here is what makes one session per thread
    possible: two requests running concurrently get two raw connections, two
    transaction counters and two `search_path`s, instead of trampling one.
    """

    __slots__ = (
        "_box", "in_transaction", "rolled_back",
        "requested_schema", "applied_schema",
        "requested_tenant", "applied_tenant",
        "__weakref__",
    )

    def __init__(self) -> None:
        #: The raw connection lives in a one-slot box rather than directly on
        #: the session, so a finalizer can still reach it after the session
        #: itself has been collected (see `Connection._session`).
        self._box: List[Any] = [None]
        self.in_transaction: int = 0
        #: Set when an inner transaction level rolled back, so the outermost
        #: `commit()` refuses instead of pretending the work was persisted.
        self.rolled_back: bool = False
        #: Tenant schema this session was asked for, or None for the one in the
        #: connection config. Per-session on purpose - see `Connection`.
        self.requested_schema: Optional[str] = None
        self.applied_schema: Optional[str] = None
        #: Tenant id bound to the session variable row-level security policies
        #: read. Per-session for exactly the same reason as the schema, and with
        #: a sharper failure mode: a leaked schema serves the wrong tables, a
        #: leaked tenant id serves another customer's rows out of the right ones.
        self.requested_tenant: Optional[str] = None
        self.applied_tenant: Optional[str] = None

    @property
    def pdo(self) -> Any:
        return self._box[0]

    @pdo.setter
    def pdo(self, value: Any) -> None:
        self._box[0] = value


class Connection:
    """A driver-dialect connection backed by a bounded pool.

    A `Connection` used to hold one raw DB-API connection plus mutable
    per-request state. That is safe only while the process handles exactly one
    request at a time - which is precisely the ~30 req/s ceiling this design
    removes. Two threads sharing a cursor corrupt each other's results, so the
    connection layer had to come first, before any thread offloading.

    The model is: **a thread checks a connection out on first use and gives it
    back at the end of the request** (`release()`, called by the HTTP kernel).
    Between those points the thread owns it outright, so transaction depth and
    tenant `search_path` are unambiguous. Handing every thread its own
    permanent connection instead - the obvious shortcut - is what exhausts
    `max_connections` the moment the thread pool grows.

    `pool_size` (per connection config, default 10) caps how many physical
    connections exist. A thread that needs one while all are checked out waits
    up to `pool_timeout` seconds and then raises, rather than blocking forever.

    **Exception - SQLite `:memory:`**: an in-memory database exists only inside
    the connection that created it, so pooling would hand each thread a
    different empty database. In that one configuration (development and the
    test-suite) every thread shares a single connection, which `sqlite3` allows
    via `check_same_thread=False`.
    """

    DEFAULT_POOL_SIZE = 10
    DEFAULT_POOL_TIMEOUT = 30.0
    #: Seconds an idle connection may sit in the pool before it is reopened
    #: instead of reused. Kept under the idle timeout managed PostgreSQL
    #: providers enforce server-side, so the pool drops a connection before the
    #: server does.
    DEFAULT_POOL_RECYCLE = 900.0
    #: Idle seconds after which a pooled connection is pinged before reuse.
    DEFAULT_POOL_PING_AFTER = 30.0

    def __init__(self, config: Dict[str, Any], base_path: Optional[str] = None):
        self.config = dict(config or {})
        self.base_path = base_path or os.getcwd()
        self.driver = (self.config.get("driver") or "sqlite").lower()
        if self.driver in ("pgsql", "postgres"):
            self.driver = "postgresql"
        self.paramstyle = "qmark" if self.driver == "sqlite" else "pyformat"

        #: Built on first use - see the `dialect` property.
        self._dialect: Any = None

        self._shares_one_session = self._is_memory_sqlite()
        self._shared_session = _Session() if self._shares_one_session else None
        self._thread_sessions = threading.local()
        #: Guards the pool bookkeeping and wakes threads waiting for a slot.
        self._cond = threading.Condition()
        #: `(raw connection, checked-in at)` pairs, so checkout can tell how
        #: long one has been idle and recycle it instead of reusing it.
        self._idle: List[tuple] = []
        self._open = 0
        #: Every live session handed out, so `close()` reaches sessions of
        #: threads still running. Weak on purpose: a session's only strong
        #: owner is its thread, so a thread that dies drops the session and the
        #: finalizer registered in `_session()` gives its connection back.
        self._sessions: "weakref.WeakSet[_Session]" = weakref.WeakSet()
        if self._shared_session is not None:
            self._sessions.add(self._shared_session)

        self.pool_size = max(1, int(self.config.get("pool_size") or self.DEFAULT_POOL_SIZE))
        self.pool_timeout = float(self.config.get("pool_timeout") or self.DEFAULT_POOL_TIMEOUT)
        self.pool_recycle = float(self.config.get("pool_recycle") or self.DEFAULT_POOL_RECYCLE)

    # -- capabilities ----------------------------------------------------------

    @property
    def dialect(self) -> Any:
        """What this connection can be asked to do (`engine/orm/dialect.py`).

        Built lazily and cached, because on PostgreSQL it has to *ask*: pgvector
        and pg_trgm are extensions, and a dialect that claims them from the
        server version alone lets a query compile, travel to the server and fail
        there with `type "vector" does not exist` - a runtime error in exactly
        the place the capability check exists to avoid.
        """
        if self._dialect is None:
            from engine.orm.dialect import PostgresDialect, dialect_for

            if self.driver == "postgresql":
                self._dialect = PostgresDialect(
                    self._installed_extensions(), self.server_version()
                )
            else:
                self._dialect = dialect_for(self.driver)
        return self._dialect

    def server_version(self) -> Optional[tuple]:
        """`(major, minor)` of the server, or None if it cannot be asked.

        Read from the driver's own `server_version` integer rather than parsing
        `version()`, which is a human-readable string that has changed shape
        between releases.
        """
        if self.driver != "postgresql":
            return None
        try:
            raw = int(getattr(self.pdo, "server_version", 0))
        except Exception:
            return None
        if not raw:
            return None
        # 150018 -> (15, 18); 180004 -> (18, 4). PostgreSQL 10 dropped the
        # three-part scheme, and every version this framework supports is after
        # that, so two parts is the whole answer.
        return (raw // 10000, raw % 100)

    def _installed_extensions(self) -> set:
        """Extension names present on this database.

        An unreachable server answers "none". That is the conservative
        direction: a feature wrongly refused raises a clear message at the call
        site, while one wrongly offered fails deep inside the driver.
        """
        try:
            rows = self.statement("SELECT extname FROM pg_extension").fetchall()
        except Exception:
            return set()
        return {row["extname"] for row in rows}

    def forget_dialect(self) -> None:
        """Re-probe capabilities - call after installing an extension."""
        self._dialect = None

    def _is_memory_sqlite(self) -> bool:
        if self.driver != "sqlite":
            return False
        database = self.config.get("database") or ":memory:"
        return database in (":memory:", "") or "mode=memory" in str(database)

    # -- sessions --------------------------------------------------------------

    def _session(self) -> _Session:
        if self._shared_session is not None:
            return self._shared_session
        session = getattr(self._thread_sessions, "session", None)
        if session is None:
            session = _Session()
            self._thread_sessions.session = session
            # A thread that dies still holding a connection never reaches
            # `release()`; reclaim its slot when the session is collected.
            weakref.finalize(session, self._reclaim, session._box)
            with self._cond:
                self._sessions.add(session)
        return session

    def _reclaim(self, box: List[Any]) -> None:
        """Discard a connection whose owning thread vanished without `release()`."""
        pdo, box[0] = box[0], None
        if pdo is not None:
            self._discard(pdo)

    @property
    def _in_transaction(self) -> int:
        """Transaction depth of the calling thread's session."""
        return self._session().in_transaction

    @_in_transaction.setter
    def _in_transaction(self, value: int) -> None:
        self._session().in_transaction = value

    @property
    def open_sessions(self) -> int:
        """Physical connections currently checked out by a thread."""
        with self._cond:
            return sum(1 for s in self._sessions if s.pdo is not None)

    @property
    def pool_stats(self) -> Dict[str, int]:
        """`{"open": physical connections, "idle": waiting in the pool}`."""
        with self._cond:
            return {"open": self._open, "idle": len(self._idle)}

    # -- pool ------------------------------------------------------------------

    def _checkout(self) -> Any:
        """Take a connection from the pool, applying per-checkout session setup.

        Delegates to `_checkout_raw()` for the pool bookkeeping, then applies
        `statement_timeout` (every checkout: a pooled connection's session
        state was reset at check-in) and, once per process, probes for a
        transaction-mode pooler in front of this connection.
        """
        pdo = self._checkout_raw()
        self._apply_statement_timeout(pdo)
        self._probe_pooler_mode(pdo)
        return pdo

    def _checkout_raw(self) -> Any:
        """Take a connection from the pool, opening one if the cap allows.

        An idle connection is reused only if it is younger than `pool_recycle`
        and still answers; otherwise it is discarded and the loop goes round
        again. A managed server drops idle sessions on its own schedule, and
        handing out one it already closed fails the first statement of a
        request for nothing.
        """
        deadline = time.monotonic() + self.pool_timeout
        while True:
            with self._cond:
                while True:
                    if self._idle:
                        pdo, checked_in_at = self._idle.pop()
                        break
                    if self._open < self.pool_size:
                        self._open += 1
                        pdo, checked_in_at = None, 0.0
                        break
                    remaining = deadline - time.monotonic()
                    if remaining <= 0 or not self._cond.wait(timeout=remaining):
                        raise ConnectionError_(
                            f"All {self.pool_size} pooled connections are in use and "
                            f"none came free within {self.pool_timeout:g}s. Raise "
                            f"`pool_size` for this connection, or look for a request "
                            f"that never releases (an unclosed transaction)."
                        )
            if pdo is None:
                try:
                    return self._connect()
                except Exception:
                    self._discard(None)
                    raise
            idle_for = time.monotonic() - checked_in_at
            if idle_for > self.pool_recycle:
                self._discard(pdo)
                continue
            # A connection handed back moments ago is almost certainly alive;
            # pinging it would add a round-trip to every request. Only ask
            # after it has sat long enough for the server to have dropped it.
            if idle_for > self.DEFAULT_POOL_PING_AFTER and not self._ping(pdo):
                self._discard(pdo)
                continue
            return pdo

    #: Set once per process by `_probe_pooler_mode`; class-level like
    #: `TenantManager._enforcement` (`engine/orm/tenancy.py`), since the
    #: answer does not change between requests on the same deployment.
    _pooler_probed: bool = False

    def _apply_statement_timeout(self, pdo: Any) -> None:
        """Apply `database.tenancy.statement_timeout_ms` to a freshly checked-out connection.

        Every checkout, not just a brand-new connection: `release()` issues
        `RESET ALL` at check-in (`_reset_session_state`), which clears this
        along with the tenant/schema GUCs, so a connection coming back out of
        the idle pool needs it re-applied too.
        """
        timeout_ms = int(self.config.get("statement_timeout_ms") or 0)
        if self.driver != "postgresql" or timeout_ms <= 0:
            return
        cursor = pdo.cursor()
        try:
            cursor.execute("SELECT set_config('statement_timeout', %s, %s)", (str(timeout_ms), False))
            if not self._session().in_transaction:
                pdo.commit()
        finally:
            try:
                cursor.close()
            except Exception:
                pass

    def _probe_pooler_mode(self, pdo: Any) -> None:
        """Warn, once per process, if this connection looks transaction-pooled.

        A transaction-mode pooler (PgBouncer's `pool_mode = transaction`) does
        not guarantee session state - a `SET`, this connection's tenant GUC -
        survives from one statement to the next, because the physical backend
        behind the pooler can be handed to a different client between them.
        Two `pg_backend_pid()` reads issued as separate statements, with no
        explicit transaction wrapping them, land on a different backend under
        such a pooler; on an ordinary session-mode connection they always
        match. Detection only, never enforcement (per the project's own
        conservative default): a false positive here must not degrade or
        refuse to serve a legitimate session-mode connection.
        """
        if self.driver != "postgresql" or Connection._pooler_probed:
            return
        Connection._pooler_probed = True
        try:
            cursor = pdo.cursor()
            try:
                cursor.execute("SELECT pg_backend_pid()")
                first_pid = cursor.fetchone()[0]
                if not self._session().in_transaction:
                    pdo.commit()
                cursor.execute("SELECT pg_backend_pid()")
                second_pid = cursor.fetchone()[0]
                if not self._session().in_transaction:
                    pdo.commit()
            finally:
                cursor.close()
        except Exception:
            logging.getLogger("craft").debug("Pooler-mode probe failed", exc_info=True)
            return
        if first_pid != second_pid:
            logging.getLogger("craft").warning(
                "PostgreSQL backend pid changed between two statements on what "
                "should be the same session (%s -> %s). This connection is "
                "likely behind a transaction-mode pooler (e.g. PgBouncer "
                "pool_mode=transaction), which does not guarantee SET/session "
                "state - including tenant binding - persists across "
                "statements. Use a session-mode pool, or bind the tenant with "
                "`local=True` (transaction-scoped) instead.",
                first_pid, second_pid,
            )

    def _ping(self, pdo: Any) -> bool:
        """Whether an idle connection still answers; only PostgreSQL is asked."""
        if self.driver != "postgresql":
            return True
        if getattr(pdo, "closed", 0):
            return False
        try:
            cursor = pdo.cursor()
            try:
                cursor.execute("SELECT 1")
            finally:
                cursor.close()
            pdo.rollback()
            return True
        except Exception:
            return False

    def _is_connection_failure(self, exc: BaseException) -> bool:
        """Whether `exc` means the physical connection can no longer be trusted."""
        if self.driver != "postgresql":
            return False
        import psycopg2

        return isinstance(exc, (psycopg2.InterfaceError, psycopg2.OperationalError))

    def release(self) -> None:
        """Return this thread's connection to the pool.

        Called at the end of each request by the HTTP kernel. Without it the
        pool is not a pool: connections accumulate one per thread and the
        server eventually gets "too many clients already" from the database.
        A no-op for shared-session SQLite, and for a thread holding nothing.
        """
        session = getattr(self._thread_sessions, "session", None) or self._shared_session
        if session is not None:
            # Forget the tenant before anything else, and whether or not there
            # is a physical connection to give back. It is per-request state on
            # a long-lived object, so a driver without pooling (shared-session
            # SQLite) must still start the next request unbound.
            session.requested_tenant = None

        if self._shared_session is not None:
            return
        if session is None or session.pdo is None:
            return

        pdo, session.pdo = session.pdo, None
        session.rolled_back = False
        if session.in_transaction:
            # A request that opened a transaction and never closed it would
            # otherwise poison the next borrower with its uncommitted work.
            session.in_transaction = 0
            try:
                pdo.rollback()
            except Exception:
                pass
        if session.applied_schema is not None or session.applied_tenant is not None:
            # The single most consequential line in the tenancy design. Both
            # the tenant search_path and the tenant id GUC live on the
            # *physical* connection: hand this one back still carrying them
            # and the next borrower, a request that never bound a tenant, a
            # background job, an admin task, reads that tenant's rows through
            # the policy, correctly and invisibly. A connection that cannot be
            # cleared is discarded rather than reused.
            try:
                self._reset_session_state(pdo)
            except Exception:
                self._discard(pdo)
                return
        session.applied_schema = None
        session.applied_tenant = None

        with self._cond:
            self._idle.append((pdo, time.monotonic()))
            self._cond.notify()

    def dedicated(self) -> Any:
        """Open a raw connection that the pool neither owns nor reclaims.

        For work that holds a connection for the life of the process - a
        `LISTEN` loop, above all. Taking one of those from the pool would lose
        a slot permanently: `release()` is never reached, so `_open` stays
        raised and the pool shrinks by one for every listener started.

        The caller owns it and must `close()` it. Nothing here tracks it.
        """
        return self._connect()

    def _discard(self, pdo: Any) -> None:
        """Drop a connection that cannot be trusted back into the pool.

        `pdo` may be None when the slot was reserved but `_connect()` failed;
        the slot is freed either way.
        """
        if pdo is not None:
            try:
                pdo.close()
            except Exception:
                pass
        with self._cond:
            self._open -= 1
            self._cond.notify()

    # -- lifecycle -------------------------------------------------------------

    @property
    def pdo(self) -> Any:
        session = self._session()
        if session.pdo is None:
            session.pdo = self._checkout()
            session.applied_schema = None
        if session.requested_schema != session.applied_schema:
            # A borrowed connection arrives on the default search_path, so a
            # session that asked for a tenant schema must (re)apply it.
            self._apply_schema(session)
        if session.requested_tenant != session.applied_tenant:
            # Same contract for the tenant id: a connection comes out of the
            # pool with none set, so a session that asked for one re-binds it.
            self._apply_tenant(session)
        return session.pdo

    def _connect(self) -> Any:
        if self.driver == "sqlite":
            return self._connect_sqlite()
        if self.driver == "postgresql":
            return self._connect_postgres()
        if self.driver == "mysql":
            return self._connect_mysql()
        raise ConnectionError_(f"Unsupported database driver [{self.driver}].")

    def _connect_sqlite(self) -> Any:
        database = self.config.get("database") or ":memory:"
        if database not in (":memory:", ""):
            if not os.path.isabs(database):
                database = os.path.join(self.base_path, database)
            directory = os.path.dirname(database)
            if directory:
                os.makedirs(directory, exist_ok=True)
        else:
            database = ":memory:"
        is_file = database != ":memory:"
        # `timeout` is the busy timeout: how long a statement waits for a lock
        # another connection holds before giving up with "database is locked".
        # A file-backed database is pooled per thread, so a threaded server
        # does have several connections contending for it; an in-memory one
        # shares a single session and never contends.
        conn = sqlite3.connect(database, check_same_thread=False, timeout=15.0 if is_file else 5.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        # Write-ahead logging was tried here and removed. It was added to fix
        # `migrate` failing with "database is locked" on a fresh project, and
        # it did not: the cause was the console booting two applications, and
        # therefore two connections, against one file. What WAL did do was
        # create sibling `-wal` and `-shm` files, which broke read/write
        # replica handling with a disk I/O error. A change that did not solve
        # the problem it was written for, and caused another, is not kept.
        return conn

    def _connect_postgres(self) -> Any:
        try:
            import psycopg2
            import psycopg2.extras
        except ImportError as exc:  # pragma: no cover - depends on environment
            raise ConnectionError_(
                "PostgreSQL driver not installed. Run `pip install psycopg2-binary`."
            ) from exc

        connect_kwargs = {
            "host": self.config.get("host", "127.0.0.1"),
            "port": int(self.config.get("port", 5432) or 5432),
            "dbname": self.config.get("database"),
            "user": self.config.get("username"),
            "password": self.config.get("password") or None,
            "connect_timeout": int(self.config.get("timeout", 10) or 10),
        }
        if "sslmode" in self.config:
            connect_kwargs["sslmode"] = self.config["sslmode"]
        if self.config.get("sslrootcert"):
            connect_kwargs["sslrootcert"] = self.config["sslrootcert"]
        # Shown in `pg_stat_activity`, so a leaking process can be told apart
        # from the other clients of a shared managed database.
        connect_kwargs["application_name"] = str(self.config.get("application_name") or "craft")

        search_path = self._default_search_path()
        if search_path:
            # As a startup option rather than a SET after connecting: it costs
            # no round-trip, and it becomes the *session default*, which is
            # what `RESET ALL` restores when the connection goes back to the
            # pool. Validated by `_default_search_path`, so quoting is safe.
            connect_kwargs["options"] = f'-c search_path="{search_path}",public'

        conn = psycopg2.connect(**connect_kwargs)
        conn.autocommit = False
        return conn


    def _connect_mysql(self) -> Any:
        try:
            import pymysql
            import pymysql.cursors
        except ImportError as exc:  # pragma: no cover - depends on environment
            raise ConnectionError_(
                "MySQL driver not installed. Run `pip install pymysql`."
            ) from exc

        return pymysql.connect(
            host=self.config.get("host", "127.0.0.1"),
            port=int(self.config.get("port", 3306) or 3306),
            database=self.config.get("database"),
            user=self.config.get("username"),
            password=self.config.get("password") or "",
            charset=self.config.get("charset", "utf8mb4"),
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,
        )

    def close(self) -> None:
        """Close the whole pool: checked-out connections and idle ones alike."""
        with self._cond:
            sessions = list(self._sessions)
            idle = [pdo for pdo, _ in self._idle]
            self._idle = []
            self._sessions = weakref.WeakSet(
                s for s in (self._shared_session,) if s is not None
            )

        for session in sessions:
            if session.pdo is not None:
                idle.append(session.pdo)
                session.pdo = None
            session.in_transaction = 0
            session.rolled_back = False
            session.applied_schema = None

        for pdo in idle:
            try:
                pdo.close()
            except Exception:
                pass

        with self._cond:
            self._open = 0
            self._cond.notify_all()

        # The calling thread's own session object may have been dropped from the
        # registry; forget it so the next use checks out a fresh connection.
        if self._shared_session is None:
            self._thread_sessions = threading.local()

    # -- execution -------------------------------------------------------------

    def _cursor(self) -> Any:
        if self.driver == "postgresql":
            import psycopg2.extras

            return self.pdo.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        return self.pdo.cursor()

    #: Savepoint wrapped around each statement inside a PostgreSQL transaction.
    STATEMENT_SAVEPOINT = "craft_statement"

    def _execute(self, cursor: Any, query: str, params: Any, guarded: bool) -> None:
        """Run one statement, under a savepoint when inside a PostgreSQL transaction.

        Without it, one failed statement a caller catches (a unique violation
        answered with "already exists") aborts the whole PostgreSQL transaction:
        every later statement fails with "current transaction is aborted".
        """
        if guarded:
            cursor.execute(f"SAVEPOINT {self.STATEMENT_SAVEPOINT}")
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

    def _rollback_statement(self, cursor: Any) -> None:
        """Undo only the failed statement, keeping the transaction usable."""
        try:
            cursor.execute(f"ROLLBACK TO SAVEPOINT {self.STATEMENT_SAVEPOINT}")
        except Exception:  # noqa: BLE001 - the original error is re-raised by the caller
            pass

    def statement(self, sql: str, bindings: Bindings = None) -> StatementResult:
        sql = sql.strip()
        query, params = normalize_placeholders(sql, bindings, self.paramstyle)
        cursor = self._cursor()
        guarded = self.driver == "postgresql" and bool(self._in_transaction)
        try:
            self._execute(cursor, query, params, guarded)
            rows = self._fetch(cursor)
            result = StatementResult(rows, cursor.rowcount, self._last_id(cursor))
            if guarded:
                # After the result is read: RELEASE replaces the cursor's result.
                cursor.execute(f"RELEASE SAVEPOINT {self.STATEMENT_SAVEPOINT}")
            if not self._in_transaction:
                self.pdo.commit()
            return result
        except Exception as exc:
            session = self._session()
            if self._is_connection_failure(exc) and session.pdo is not None:
                # The socket is gone: rolling back would fail too, and handing
                # the connection back to the pool would make every later
                # borrower fail the same way. Drop it and start clean next time.
                pdo, session.pdo = session.pdo, None
                session.in_transaction = 0
                session.applied_schema = session.applied_tenant = None
                self._discard(pdo)
                raise
            if guarded:
                self._rollback_statement(cursor)
            if not session.in_transaction:
                try:
                    self.pdo.rollback()
                except Exception:
                    pass
            raise
        finally:
            try:
                cursor.close()
            except Exception:
                pass

    def _fetch(self, cursor: Any) -> List[Row]:
        if cursor.description is None:
            return []
        try:
            raw = cursor.fetchall()
        except Exception:
            return []
        rows: List[Row] = []
        columns = [d[0] for d in cursor.description]
        for item in raw:
            if isinstance(item, Row):
                rows.append(item)
            elif isinstance(item, dict):
                rows.append(Row(item))
            elif isinstance(item, sqlite3.Row):
                rows.append(Row({key: item[key] for key in item.keys()}))
            else:
                # strict: a row whose arity disagrees with cursor.description is
                # a driver bug - pairing them off silently would drop columns.
                rows.append(Row(dict(zip(columns, item, strict=True))))
        return rows

    def _last_id(self, cursor: Any) -> Any:
        return getattr(cursor, "lastrowid", None)

    # -- transactions ----------------------------------------------------------

    def begin(self) -> None:
        if self._in_transaction == 0 and self.driver == "sqlite":
            # sqlite3 in its default mode never issues BEGIN itself, so without
            # this the "transaction" would not actually be atomic.
            try:
                self.pdo.execute("BEGIN IMMEDIATE")
            except sqlite3.OperationalError:
                pass  # already inside an implicit transaction
        self._in_transaction += 1

    def commit(self) -> None:
        """Commit the outermost transaction; inner levels only unwind depth.

        Raises `TransactionRolledBackError` when an inner level rolled back:
        the work is already gone, and returning silently would let the outer
        caller believe it was persisted.
        """
        session = self._session()
        if session.in_transaction:
            session.in_transaction -= 1
        if session.in_transaction:
            return
        if session.rolled_back:
            session.rolled_back = False
            raise TransactionRolledBackError()
        self.pdo.commit()

    def rollback(self) -> None:
        session = self._session()
        # Rolling back from an inner level discards the outer levels' work too
        # (there are no savepoints); make their commit fail loudly. From the
        # outermost level there is nobody left to warn, so the flag clears.
        session.rolled_back = session.in_transaction > 1
        session.in_transaction = 0
        try:
            self.pdo.rollback()
        except Exception:
            pass

    # -- schema helpers --------------------------------------------------------

    def use_schema(self, schema: Optional[str]) -> None:
        """Switch the active PostgreSQL schema (multi-tenancy).

        **Scoped to the calling thread.** The tenant is a property of the
        request being served, so making it process-wide would mean one tenant's
        request could repoint the search_path while another tenant's request is
        mid-flight - a cross-tenant read, not merely a race. Every request sets
        its own schema on its own session.
        """
        if schema:
            assert_schema_identifier(schema)
        session = self._session()
        session.requested_schema = schema
        if self.driver != "postgresql":
            return
        self._apply_schema(session)

    @property
    def schema(self) -> Optional[str]:
        """Tenant schema active for the calling thread."""
        return self._session().requested_schema

    def _apply_schema(self, session: _Session) -> None:
        """Point one session at the schema it asked for."""
        if self.driver != "postgresql" or session.pdo is None:
            return
        schema = session.requested_schema
        # Mark first: `statement()` goes back through `pdo`, and an unmarked
        # session would recurse straight back into here.
        previous, session.applied_schema = session.applied_schema, schema
        try:
            if schema:
                self.statement(f'SET search_path TO "{schema}", public')
            else:
                self._reset_schema(session.pdo)
        except Exception:
            session.applied_schema = previous
            raise

    def _default_search_path(self) -> Optional[str]:
        default = self.config.get("search_path") or self.config.get("schema")
        if default:
            assert_schema_identifier(default)
        return default

    def _reset_session_state(self, pdo: Any) -> None:
        """Drop every per-request setting in one round-trip at check-in.

        `RESET ALL` restores the session defaults, which include the startup
        `search_path` from the config and an unset tenant GUC. Run in
        autocommit so it is a single round-trip, rather than the SET + COMMIT
        pairs it replaces (two per setting, up to four per request).
        """
        if self.driver != "postgresql":
            return
        pdo.autocommit = True
        try:
            cursor = pdo.cursor()
            try:
                cursor.execute("RESET ALL")
            finally:
                cursor.close()
        finally:
            pdo.autocommit = False

    def _reset_schema(self, pdo: Any) -> None:
        """Put a connection back on the search_path its config asks for."""
        if self.driver != "postgresql":
            return
        default = self._default_search_path()
        sql = f'SET search_path TO "{default}", public' if default else "SET search_path TO public"
        cursor = pdo.cursor()
        try:
            cursor.execute(sql)
            pdo.commit()
        finally:
            try:
                cursor.close()
            except Exception:
                pass

    # -- tenant session variable -----------------------------------------------

    #: The setting row-level security policies read. A namespaced (dotted) name
    #: is what makes it settable at all - PostgreSQL only accepts custom
    #: settings under a prefix it does not own.
    TENANT_GUC = "app.current_tenant_id"

    def use_tenant(self, tenant_id: Optional[str], *, local: bool = False) -> None:
        """Bind `tenant_id` to this session's `app.current_tenant_id`.

        Scoped to the calling thread, like `use_schema`, because the tenant is a
        property of the request being served.

        `local=True` scopes the setting to the open transaction, which
        PostgreSQL unwinds at COMMIT or ROLLBACK - the right choice inside
        `DB.transaction()` and in a queue worker, where there is no request end
        to hang a reset on. `local=False` scopes it to the session and relies on
        `release()` to clear it.
        """
        session = self._session()
        if self.driver != "postgresql":
            # Nothing to bind, but remember the request so `tenant` still reports
            # what the caller asked for on drivers used in development.
            session.requested_tenant = tenant_id or None
            return

        if local:
            # Not tracked on the session: the transaction owns the lifetime, and
            # marking it applied would make `release()` try to clear a setting
            # the COMMIT already dropped.
            self._set_tenant(self.pdo, tenant_id, local=True)
            return

        session.requested_tenant = tenant_id or None
        self._apply_tenant(session)

    @property
    def tenant(self) -> Optional[str]:
        """Tenant id bound for the calling thread."""
        return self._session().requested_tenant

    def _apply_tenant(self, session: _Session) -> None:
        if self.driver != "postgresql" or session.pdo is None:
            return
        tenant_id = session.requested_tenant
        # Mark first: `_set_tenant` goes back through `pdo`, and an unmarked
        # session would recurse straight back into here.
        previous, session.applied_tenant = session.applied_tenant, tenant_id
        try:
            self._set_tenant(session.pdo, tenant_id, local=False)
        except Exception:
            session.applied_tenant = previous
            raise

    def _set_tenant(self, pdo: Any, tenant_id: Optional[str], *, local: bool) -> None:
        """Set the GUC through `set_config`, which takes bindings.

        `SET LOCAL app.current_tenant_id = :id` is not an option: `SET` is not
        parameterizable, so the value would have to be interpolated - the same
        hole `assert_schema_identifier` exists to close, but on a value that
        comes straight from a request. `set_config(name, value, is_local)` is an
        ordinary function call and binds cleanly.
        """
        cursor = pdo.cursor()
        try:
            cursor.execute(
                "SELECT set_config(%s, %s, %s)",
                (self.TENANT_GUC, tenant_id or "", bool(local)),
            )
            if not local and not self._session().in_transaction:
                pdo.commit()
        finally:
            try:
                cursor.close()
            except Exception:
                pass

    def _reset_tenant(self, pdo: Any) -> None:
        """Clear the GUC on a connection going back to the pool.

        Empty rather than absent, because `current_setting(name, true)` cannot
        un-set a value once set. The policies treat `''` and NULL alike - see
        the `NULLIF` in the generated policy - so both mean "no tenant", and no
        tenant matches nothing.
        """
        if self.driver != "postgresql":
            return
        self._set_tenant(pdo, None, local=False)

    def table_exists(self, table: str) -> bool:
        if self.driver == "sqlite":
            sql = "SELECT name FROM sqlite_master WHERE type='table' AND name = ?"
        elif self.driver == "postgresql":
            sql = (
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_name = ? AND table_schema = ANY (current_schemas(false))"
            )
        else:
            sql = "SELECT table_name FROM information_schema.tables WHERE table_name = ? AND table_schema = DATABASE()"
        return self.statement(sql, [table]).fetchone() is not None
