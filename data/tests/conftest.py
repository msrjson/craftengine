"""Pytest bootstrap for the Craft Framework test-suite.

By default the suite runs against an in-memory SQLite database whose schema is
built by the real migrator, so migrations are exercised on every run instead of
relying on hand-maintained fixture tables.

PostgreSQL test execution remains disabled until legacy physical-delete tests
have been converted to non-destructive isolation. A `_test` suffix does not
authorize wiping a database.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import hashlib
import os
import sys
import uuid
from typing import Any, Generator

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Must be set before `bootstrap.app` builds the config repository.
os.environ.setdefault("APP_ENV", "testing")
os.environ.setdefault("QUEUE_CONNECTION", "sync")
os.environ.setdefault("CACHE_DRIVER", "array")

TEST_DB = os.environ.get("CRAFT_TEST_DB", "sqlite").lower()
os.environ["DB_CONNECTION"] = TEST_DB

_WORKER_ID = os.environ.get("PYTEST_XDIST_WORKER", "master")
if TEST_DB == "sqlite":
    os.environ["DB_DATABASE"] = ":memory:"
else:
    pytest.exit("Persistent database tests are disabled until fixtures preserve every record.")

import engine  # noqa: F401,E402  installs the `craft.*` import alias

@pytest.fixture
def is_postgres() -> bool:
    """Return whether tests are running against PostgreSQL."""
    return TEST_DB in ("pgsql", "postgres", "postgresql")


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> Generator[Any, None, None]:
    """Build the test schema with the real migrator, once per session.

    For PostgreSQL, acquires an advisory lock to coordinate parallel pytest
    workers (pytest-xdist) so schema mutations do not race.
    """
    from bootstrap.app import app
    from craft.migrations.migrator import Migrator

    is_pg = TEST_DB in ("pgsql", "postgres", "postgresql")
    lock_id = None

    try:
        # Acquire lock for parallel-safe schema mutation on PostgreSQL.
        if is_pg:
            db = app.make("db")
            lock_id = int(
                hashlib.md5(os.environ.get("DB_DATABASE", "craft_test").encode()).hexdigest()[:8],
                16
            )
            db.statement("SELECT pg_advisory_lock(?)", [lock_id])

        migrator = Migrator(app)
        migrator.run()
        yield app

    finally:
        # Release the advisory lock if it was acquired.
        if is_pg and lock_id is not None:
            try:
                db = app.make("db")
                db.statement("SELECT pg_advisory_unlock(?)", [lock_id])
            except Exception:
                pass  # Lock already released or connection closed; no error needed.


#: Where the suite's own identity models live, by configuration key. The
#: engine resolves identity through `engine/auth/registry.py` and the guard's
#: provider, so pointing those keys here is all it takes for the whole stack —
#: login, RBAC middleware, console commands — to act on the test models.
_IDENTITY_CONFIG = {
    "auth.providers.users.model": "tests.support.models.User",
    "auth.models.user": "tests.support.models.User",
    "auth.models.role": "tests.support.models.Role",
    "auth.models.permission": "tests.support.models.Permission",
    "auth.models.group": "tests.support.models.Group",
}


@pytest.fixture(scope="session", autouse=True)
def identity_models(migrated_database) -> Generator[Any, None, None]:
    """Give the suite identity models and tables of its own.

    The tests exercise the engine, so they must not depend on the application
    that ships beside it owning a `User`. The schema is completed where a
    migration did not already build it, and the auth configuration is pointed
    at `tests/support/models.py` for the whole session.
    """
    from tests.support.schema import ensure_identity_schema

    ensure_identity_schema()

    config = migrated_database.make("config")
    previous = {key: config.get(key) for key in _IDENTITY_CONFIG}
    for key, path in _IDENTITY_CONFIG.items():
        config.set(key, path)

    yield migrated_database

    for key, path in previous.items():
        config.set(key, path)


@pytest.fixture
def two_tenants(migrated_database) -> Generator[tuple[str, str], None, None]:
    """Create two test tenant records and return their IDs.

    Yields:
        A tuple of (tenant_a_id, tenant_b_id), two UUIDs for distinct tenants.

    Cleans up both tenants after the test.
    """
    from craft.facades import DB

    tenant_a_id = str(uuid.uuid4())
    tenant_b_id = str(uuid.uuid4())

    # Insert both tenants into the database (is_active defaults to True).
    DB.table("tenants").insert({"id": tenant_a_id})
    DB.table("tenants").insert({"id": tenant_b_id})

    yield tenant_a_id, tenant_b_id

    # Clean up.
    DB.table("tenants").where_in("id", [tenant_a_id, tenant_b_id]).delete()


@pytest.fixture
def client_for_host(migrated_database):
    """Return a test client factory that sets the Host header.

    Returns:
        A callable that takes a hostname string and returns a TestClient
        with the Host header pre-set, for testing ScopeTenant.resolve()
        and host-based tenant resolution end-to-end.
    """
    from starlette.testclient import TestClient
    from bootstrap.app import asgi_app

    def _make_client(host: str) -> TestClient:
        """Create a TestClient with a specific Host header."""
        client = TestClient(asgi_app)
        client.headers["Host"] = host
        return client

    return _make_client


@pytest.fixture
def unprivileged_postgres_role(migrated_database, is_postgres) -> Generator[str, None, None]:
    """Create a PostgreSQL role without BYPASSRLS for testing RLS enforcement.

    Yields:
        The role name (username).

    On SQLite, this is a no-op — the fixture yields a dummy value.
    """
    if not is_postgres:
        yield "sqlite_unprivileged"
        return

    from craft.facades import DB

    role_name = f"craft_unprivileged_{_WORKER_ID}_{os.getpid()}"

    try:
        # Drop the role if it already exists (from a previous run).
        DB.statement(f"DROP ROLE IF EXISTS {role_name}")
    except Exception:
        pass

    # Create a new role without superuser or BYPASSRLS privileges.
    try:
        DB.statement(f"CREATE ROLE {role_name} WITH LOGIN PASSWORD 'test'")
    except Exception as e:
        pytest.skip(f"Cannot create PostgreSQL role for unprivileged testing: {e}")

    yield role_name

    # Clean up.
    try:
        DB.statement(f"DROP ROLE IF EXISTS {role_name}")
    except Exception:
        pass  # Role already dropped or owned by other sessions; ignore.
