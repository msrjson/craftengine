"""Architectural & Performance Hardening Tests for Craft Framework v4.2.0.

Validates the mitigations for:
1. Translation bundles loaded once per request, never shared by the process.
2. Request-scoped RBAC/ABAC AccessResolver caching.
3. DatabaseSessionStore dirty-checking without freezing idle tracking.
4. AuthManager ContextVar isolation for ASGI / concurrent request safety.
5. ORM N+1 query detection & per-request query logging.
6. HTTP Kernel method override memory bounding.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import asyncio
import json
import time
import uuid
from unittest.mock import MagicMock

import pytest
from craft.facades import DB
from engine.auth.access import AccessResolver, clear_access_cache, get_access_cache
from engine.auth.manager import AuthManager
from engine.container.application import Container
from engine.http.session import DatabaseSessionStore, Session
from engine.orm.db import (
    DatabaseManager,
    get_request_query_log,
    start_query_logging,
    stop_query_logging,
)
from engine.support.translation import clear_translation_cache, translate


def _translation_queries(log: list) -> int:
    """Count the statements in `log` that read the translations table."""
    return sum(1 for query in log if "FROM translations" in query)


class TestTranslationRequestBundles:
    """Bundles are request-scoped: fresh per request, never shared by the process."""

    @pytest.fixture(autouse=True)
    def seed_translations(self, migrated_database):
        self.prefix = f"bundle_{uuid.uuid4().hex[:8]}"
        for i in range(10):
            DB.table("translations").insert(
                {"key": f"{self.prefix}_{i}", "locale": "pt-BR", "value": f"valor {i}"}
            )
        clear_translation_cache()
        yield
        clear_translation_cache()

    def test_one_bundle_query_serves_every_key_of_the_request(self):
        token = Container.begin_request_scope()
        start_query_logging()
        try:
            for i in range(10):
                assert translate(f"{self.prefix}_{i}", "pt-BR") == f"valor {i}"
            assert _translation_queries(stop_query_logging()) == 1
        finally:
            Container.end_request_scope(token)

    def test_an_edited_translation_shows_in_the_next_request(self):
        key = f"{self.prefix}_0"
        assert _translate_in_request(key) == "valor 0"
        DB.table("translations").where("key", key).where("locale", "pt-BR").update({"value": "editado"})
        assert _translate_in_request(key) == "editado"

    def test_a_key_missing_in_one_request_is_found_after_it_is_added(self):
        key = f"{self.prefix}_late"
        assert _translate_in_request(key) == key
        DB.table("translations").insert({"key": key, "locale": "pt-BR", "value": "chegou"})
        assert _translate_in_request(key) == "chegou"

    def test_nothing_is_cached_outside_a_request(self):
        key = f"{self.prefix}_1"
        assert translate(key, "pt-BR") == "valor 1"
        DB.table("translations").where("key", key).where("locale", "pt-BR").update({"value": "fora"})
        assert translate(key, "pt-BR") == "fora"


def _translate_in_request(key: str) -> str:
    """Translate `key` inside its own request scope, as one HTTP request would."""
    token = Container.begin_request_scope()
    try:
        return translate(key, "pt-BR")
    finally:
        Container.end_request_scope(token)


class TestAccessResolverRequestCache:
    def test_access_resolver_caches_within_request_and_clears(self):
        clear_access_cache()
        mock_db = MagicMock()
        mock_stmt = MagicMock()
        mock_stmt.fetchall.return_value = [{"source": "direct", "conditions": None}]
        mock_db.statement.return_value = mock_stmt

        app = MagicMock()
        app.make.return_value = mock_db

        resolver = AccessResolver(app=app)
        user = {"id": 42}

        # First check triggers DB statement
        allowed_1 = resolver.has_permission(user, "edit-posts")
        assert allowed_1 is True
        assert mock_db.statement.call_count == 1

        # Second check within the same request hits ContextVar cache
        allowed_2 = resolver.has_permission(user, "edit-posts")
        assert allowed_2 is True
        assert mock_db.statement.call_count == 1

        # Clearing cache forces next check to query again
        clear_access_cache()
        allowed_3 = resolver.has_permission(user, "edit-posts")
        assert allowed_3 is True
        assert mock_db.statement.call_count == 2
        clear_access_cache()


def _persisted_session(seconds_since_activity: float) -> Session:
    """Return an unmodified, persisted session last active that long ago."""
    session = Session({"user_id": 101}, session_id="sess_abc123")
    session._modified = False
    session._persisted = True
    session._last_activity = time.time() - seconds_since_activity
    session._loaded_payload = {"user_id": 101}  # the payload as the store wrote it
    return session


class TestDatabaseSessionDirtyTracking:
    def _store(self) -> tuple:
        store = DatabaseSessionStore(key="test-secret-key-32-chars-long-123", idle_timeout=900)
        mock_db = MagicMock()
        store._db = lambda: mock_db
        return store, mock_db

    def test_recently_active_unmodified_session_skips_database_write(self):
        store, mock_db = self._store()
        assert store.save(_persisted_session(5)) is not None
        mock_db.table.assert_not_called()

    def test_stale_unmodified_session_touches_only_its_activity(self):
        store, mock_db = self._store()
        store.save(_persisted_session(120))
        update = mock_db.table.return_value.where.return_value.update
        update.assert_called_once()
        assert set(update.call_args.args[0]) == {"last_activity_at", "updated_at"}

    def test_reading_user_is_not_logged_out_by_idle_timeout(self):
        store, _ = self._store()
        session = _persisted_session(120)
        store.save(session)
        assert time.time() - session._last_activity < 5

    def test_modified_session_performs_update(self):
        store = DatabaseSessionStore(key="test-secret-key-32-chars-long-123")
        mock_db = MagicMock()
        mock_table = MagicMock()
        mock_where = MagicMock()
        mock_db.table.return_value = mock_table
        mock_table.where.return_value = mock_where
        store._db = lambda: mock_db

        session = Session({"user_id": 101}, session_id="sess_abc123")
        session._persisted = True
        session.put("theme", "dark")  # Marks session._modified = True

        store.save(session)
        mock_db.table.assert_called_with("sessions")
        mock_where.update.assert_called_once()


class TestAuthManagerContextVarIsolation:
    def test_auth_manager_isolates_users_across_async_tasks(self):
        auth = AuthManager()

        user_a = MagicMock()
        user_a.get_attribute.return_value = "user_A"
        user_b = MagicMock()
        user_b.get_attribute.return_value = "user_B"

        results = {}

        async def task_a():
            auth.set_user(user_a)
            await asyncio.sleep(0.01)
            results["task_a"] = auth.user().get_attribute("id")

        async def task_b():
            auth.set_user(user_b)
            await asyncio.sleep(0.01)
            results["task_b"] = auth.user().get_attribute("id")

        async def run_concurrent():
            await asyncio.gather(task_a(), task_b())

        asyncio.run(run_concurrent())

        assert results["task_a"] == "user_A"
        assert results["task_b"] == "user_B"
        auth.reset()


class TestOrmQueryLoggingAndNPlusOne:
    def test_query_logging_and_n_plus_one_detection(self, caplog):
        start_query_logging()
        log = get_request_query_log()
        assert log == []

        db = DatabaseManager(config={"driver": "sqlite", "database": ":memory:"})
        db.statement("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT)")

        # Execute 12 identical queries
        query = "SELECT * FROM items WHERE id = ?"
        for i in range(12):
            db.statement(query, [i])

        recorded = stop_query_logging()
        assert len(recorded) >= 12
        assert "Potential N+1 query detected" in caplog.text


class TestMethodOverrideMemoryLimit:
    def test_method_override_bounds_body_buffering(self):
        from engine.http.kernel import DynamicStarletteApp

        app_mock = MagicMock()
        dynamic_app = DynamicStarletteApp(app_mock)

        # 100KB payload
        chunk = b"x" * 10240
        received_chunks = [
            {"type": "http.request", "body": chunk, "more_body": True}
            for _ in range(9)
        ]
        received_chunks.append({"type": "http.request", "body": chunk, "more_body": False})

        chunk_iter = iter(received_chunks)

        async def mock_receive():
            return next(chunk_iter)

        scope = {
            "type": "http",
            "method": "POST",
            "headers": [(b"content-type", b"application/x-www-form-urlencoded")],
        }

        async def run_override():
            return await dynamic_app._apply_method_override(scope, mock_receive)

        new_scope, replaying_receive = asyncio.run(run_override())
        assert new_scope["method"] == "POST"

        # Verify we can still read all chunks via replaying_receive
        async def drain():
            total = 0
            while True:
                msg = await replaying_receive()
                total += len(msg.get("body", b""))
                if not msg.get("more_body", False):
                    break
            return total

        total_bytes = asyncio.run(drain())
        assert total_bytes == 102400


class TestKernelHoldsNoSubsystemCleanup:
    """The kernel serves HTTP; subsystems keep their own state per request."""

    def test_kernel_does_not_import_or_call_auth(self):
        import ast
        import pathlib

        source = pathlib.Path("engine/http/kernel.py").read_text()
        imported = {
            node.module
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.ImportFrom) and node.module
        }
        assert not any(module.startswith("engine.auth") for module in imported)
        assert 'make("auth")' not in source

    def test_request_state_does_not_leak_between_thread_pool_requests(self):
        from starlette.concurrency import run_in_threadpool

        auth = AuthManager()
        user = MagicMock()

        def first_request() -> None:
            auth.set_user(user)
            get_access_cache()["rows:1:x"] = ["granted"]

        def second_request() -> tuple:
            return auth.user(), dict(get_access_cache())

        async def serve_two() -> tuple:
            await run_in_threadpool(first_request)
            return await run_in_threadpool(second_request)

        seen_user, seen_cache = asyncio.run(serve_two())
        assert seen_user is None
        assert seen_cache == {}


def test_n_plus_one_warning_fires_once_per_query(caplog):
    start_query_logging()
    db = DatabaseManager(config={"driver": "sqlite", "database": ":memory:"})
    db.statement("CREATE TABLE things (id INTEGER PRIMARY KEY)")
    for i in range(25):
        db.statement("SELECT * FROM things WHERE id = ?", [i])
    stop_query_logging()
    assert caplog.text.count("Potential N+1 query detected") == 1


class TestDatabaseSessionRoundTrip:
    """Read-only requests still persist what the request itself changed."""

    @pytest.fixture
    def store(self, migrated_database):
        store = DatabaseSessionStore("test-secret-key-32-chars-long-123", migrated_database, idle_timeout=900)
        store.created = []
        yield store
        for session_id in store.created:
            store.destroy(session_id)

    def _first_request(self, store) -> Session:
        session = store.load(None)
        store.created.append(session.id)
        return session

    def test_a_flash_is_shown_once_then_gone(self, store):
        first = self._first_request(store)
        first.flash("notice", "saved")
        second = store.load(store.save(first))
        assert second.get("notice") == "saved"
        third = store.load(store.save(second))
        assert third.get("notice") is None

    def test_an_in_place_change_is_persisted(self, store):
        first = self._first_request(store)
        first.put("cart", [])
        second = store.load(store.save(first))
        second.get("cart").append("sku-1")
        assert store.load(store.save(second)).get("cart") == ["sku-1"]

    def test_a_short_idle_timeout_is_touched_before_it_expires(self):
        store = DatabaseSessionStore(key="test-secret-key-32-chars-long-123", idle_timeout=30)
        mock_db = MagicMock()
        store._db = lambda: mock_db
        store.save(_persisted_session(20))
        mock_db.table.return_value.where.return_value.update.assert_called_once()
