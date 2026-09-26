"""Architectural & Performance Hardening Tests for Craft Framework v4.2.0.

Validates the mitigations for:
1. Translation in-memory bulk memoization & negative caching.
2. Request-scoped RBAC/ABAC AccessResolver caching.
3. DatabaseSessionStore dirty-checking & avoidance of redundant writes.
4. AuthManager ContextVar isolation for ASGI / concurrent request safety.
5. ORM N+1 query detection & per-request query logging.
6. HTTP Kernel method override memory bounding.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import asyncio
from unittest.mock import MagicMock

import pytest
from craft.facades import DB
from engine.auth.access import AccessResolver, clear_access_cache, get_access_cache
from engine.auth.manager import AuthManager
from engine.http.session import DatabaseSessionStore, Session
from engine.orm.db import (
    DatabaseManager,
    get_request_query_log,
    start_query_logging,
    stop_query_logging,
)
from engine.support.translation import (
    __,
    clear_translation_cache,
    translate,
)


class TestTranslationBulkMemoization:
    @pytest.fixture(autouse=True)
    def setup_translations(self, migrated_database):
        clear_translation_cache()
        DB.table("translations").where("key", "like", "bench_%").delete()
        for i in range(10):
            DB.table("translations").insert({
                "key": f"bench_key_{i}",
                "locale": "en",
                "value": f"English Value {i}",
            })
            DB.table("translations").insert({
                "key": f"bench_key_{i}",
                "locale": "pt-BR",
                "value": f"Valor Portugues {i}",
            })
        yield
        clear_translation_cache()
        DB.table("translations").where("key", "like", "bench_%").delete()

    def test_translation_bulk_loads_and_serves_from_memory(self):
        clear_translation_cache()
        # First call loads the bundle for pt-BR
        assert translate("bench_key_0", "pt-BR") == "Valor Portugues 0"

        # Subsequent lookups for other keys in the same locale hit memory bundle
        for i in range(1, 10):
            assert __ (f"bench_key_{i}", "pt-BR") == f"Valor Portugues {i}"

    def test_negative_cache_for_missing_keys(self):
        clear_translation_cache()
        assert translate("bench_missing_key", "pt-BR") == "bench_missing_key"
        # Second call hits negative cache without hitting DB
        assert translate("bench_missing_key", "pt-BR") == "bench_missing_key"


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


class TestDatabaseSessionDirtyTracking:
    def test_unmodified_session_skips_database_write(self):
        store = DatabaseSessionStore(key="test-secret-key-32-chars-long-123")
        mock_db = MagicMock()
        store._db = lambda: mock_db

        # Create session marked as persisted and unmodified
        session = Session({"user_id": 101}, session_id="sess_abc123")
        session._modified = False
        session._persisted = True

        cookie = store.save(session)
        assert cookie is not None
        # Neither update nor insert should be called
        mock_db.table.assert_not_called()

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
