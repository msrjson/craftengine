"""Pytest bootstrap for the Craft Framework test-suite.

By default the suite runs against an in-memory SQLite database whose schema is
built by the real migrator, so migrations are exercised on every run instead of
relying on hand-maintained fixture tables.

On PostgreSQL (`CRAFT_TEST_DB=pgsql`) the suite never points at an existing
database: it creates one for the session, named `craft_test_<utc>_<id>_<worker>`,
through the database named in `DB_DATABASE`, and never drops it. The run is
refused while any test still deletes, truncates or drops
(`tests/test_fixture_safety.py`), because NR-02 holds in the test environment
too.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

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


def _refuse_destructive_tests() -> None:
    """Stop a PostgreSQL run while any test still deletes, truncates or drops."""
    from tests.test_fixture_safety import _offending_lines

    offending = list(_offending_lines())
    if offending:
        pytest.exit("NR-02: destructive statements in tests: " + ", ".join(offending), returncode=4)


def _create_session_database() -> str:
    """Create an empty database for this session and return its name.

    Connects to the database `DB_DATABASE` names only to issue `CREATE
    DATABASE`; the tests never run there. The new database is not dropped
    afterwards: nothing is ever deleted, and a CI service container is thrown
    away with everything in it.
    """
    from datetime import datetime, timezone

    import psycopg2

    name = "_".join((
        "craft_test", datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
        uuid.uuid4().hex[:8], _WORKER_ID.replace("-", "_"),
    ))
    connection = psycopg2.connect(
        host=os.environ.get("DB_HOST", "127.0.0.1"), port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ.get("DB_DATABASE", "postgres"), user=os.environ.get("DB_USERNAME", "postgres"),
        password=os.environ.get("DB_PASSWORD", ""), sslmode=os.environ.get("DB_SSLMODE", "prefer"),
    )
    connection.autocommit = True
    with connection.cursor() as cursor:
        cursor.execute("CREATE DATABASE " + name)
    connection.close()
    return name


if TEST_DB == "sqlite":
    os.environ["DB_DATABASE"] = ":memory:"
else:
    _refuse_destructive_tests()
    os.environ["DB_DATABASE"] = _create_session_database()

import engine  # noqa: F401,E402  installs the `craft.*` import alias

@pytest.fixture
def is_postgres() -> bool:
    """Return whether tests are running against PostgreSQL."""
    return TEST_DB in ("pgsql", "postgres", "postgresql")


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> Generator[Any, None, None]:
    """Build the test schema with the real migrator, once per session.

    Every session and every xdist worker has a database of its own, so no
    lock is needed around the schema.
    """
    from bootstrap.app import app
    from craft.migrations.migrator import Migrator

    Migrator(app).run()
    yield app


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
