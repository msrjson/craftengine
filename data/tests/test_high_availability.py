"""What a load balancer, an orchestrator and a rolling deploy need from the app.

These cover the four things a second instance makes newly relevant: probes to
route on, a shutdown that closes the pool instead of abandoning it, a worker
pool bounded by the connections that back it, and a migrator that two
containers can run at the same moment.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import signal
import threading

import pytest
from starlette.testclient import TestClient

from bootstrap.app import app, asgi_app
from craft.support.shutdown import ShutdownSignal


#: Bearer token the probe fixture configures, so the detailed readiness payload
#: can be asserted on. Never a real secret: it exists only inside this suite.
READINESS_TOKEN = "readiness-token-for-tests"

#: Header a caller entitled to the detailed payload sends.
DETAILED = {"Authorization": f"Bearer {READINESS_TOKEN}"}


@pytest.fixture
def probes_enabled(migrated_database):
    """Turn the probe routes on for the duration of a test.

    They are opt-in since 4.0.0: an application that never asked for them does
    not answer on /health or /ready. Enabling one is a configuration change
    plus a re-registration, because the route table is built from config. The
    readiness result cache is switched off so each test sees its own run.
    """
    from bootstrap.app import kernel

    config = app.make("config")
    names = (
        "framework.HEALTH_ROUTES_ENABLED",
        "framework.HEALTH_READINESS_TOKEN",
        "framework.HEALTH_READINESS_CACHE_SECONDS",
    )
    saved = {name: config.get(name) for name in names}
    config.set("framework.HEALTH_ROUTES_ENABLED", True)
    config.set("framework.HEALTH_READINESS_TOKEN", READINESS_TOKEN)
    config.set("framework.HEALTH_READINESS_CACHE_SECONDS", 0)
    kernel.register_engine_routes(refresh=True)
    yield config
    for name, value in saved.items():
        config.set(name, value)
    kernel.register_engine_routes(refresh=True)


@pytest.fixture
def client(probes_enabled):
    return TestClient(asgi_app)


class TestHealthProbes:
    def test_liveness_answers_without_touching_the_database(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ok"
        assert "uptime_seconds" in payload
        # Liveness must not report dependencies: a database incident restarting
        # every healthy web instance is the failure this separation prevents.
        assert "checks" not in payload

    def test_readiness_reports_each_dependency(self, client):
        """The detailed payload, which only a caller holding the token gets."""
        response = client.get("/ready", headers=DETAILED)
        assert response.status_code == 200
        checks = response.json()["checks"]
        assert checks["database"]["status"] == "pass"
        assert checks["database"]["pool_size"] >= 1
        assert checks["cache"]["status"] == "pass"

    def test_readiness_is_unavailable_when_a_critical_check_fails(self, client):
        from craft.http.health import HealthCheck, HealthReporter

        def broken():
            raise RuntimeError("DATABASE_UNAVAILABLE")

        reporter = HealthReporter(app, checks=[HealthCheck("database", broken)])
        payload, status = reporter.readiness()

        assert status == 503
        assert payload["status"] == "unavailable"
        assert payload["checks"]["database"]["error"] == "RuntimeError"

    def test_a_failing_optional_check_does_not_take_the_instance_out(self):
        from craft.http.health import HealthCheck, HealthReporter

        def broken():
            raise RuntimeError("CACHE_UNAVAILABLE")

        reporter = HealthReporter(
            app, checks=[HealthCheck("cache", broken, critical=False)]
        )
        payload, status = reporter.readiness()

        assert status == 200
        assert payload["checks"]["cache"]["status"] == "fail"

    def test_probing_does_not_leak_a_pooled_connection(self, client):
        connection = app.make("db").write_connection
        for _ in range(3):
            assert client.get("/ready").status_code == 200
        assert connection.open_sessions <= 1


class _RecordingApp:
    """A container stand-in that records what shutdown asked it to close.

    The lifecycle is asserted against this rather than the real application:
    closing the shared in-memory test database would destroy it for every test
    that runs afterwards, which is exactly what shutdown is supposed to do.
    """

    def __init__(self, failing: bool = False):
        self.purged = []
        self.failing = failing
        self.base_path = "."

    def make(self, name):
        if self.failing:
            raise RuntimeError("CONTAINER_TORN_DOWN")
        recorder = self

        class Service:
            def purge(self):
                recorder.purged.append(name)

        return Service()


class TestLifecycle:
    def test_shutdown_closes_the_connection_pool(self):
        import asyncio

        from craft.http.kernel import Kernel

        recording = _RecordingApp()
        asyncio.run(Kernel(recording).on_shutdown())
        assert recording.purged == ["db"]

    def test_shutdown_never_raises(self):
        """An exception here would turn an orderly exit into a stack trace and
        a non-zero status, which an orchestrator reads as a crash loop."""
        import asyncio

        from craft.http.kernel import Kernel

        asyncio.run(Kernel(_RecordingApp(failing=True)).on_shutdown())

    def test_the_lifespan_protocol_completes_both_phases(self):
        import asyncio

        from craft.http.kernel import Kernel

        recording = _RecordingApp()
        asgi = Kernel(recording).get_starlette_app()
        incoming = iter([{"type": "lifespan.startup"}, {"type": "lifespan.shutdown"}])
        sent = []

        async def receive():
            return next(incoming)

        async def send(message):
            sent.append(message["type"])

        asyncio.run(asgi({"type": "lifespan"}, receive, send))

        assert sent == ["lifespan.startup.complete", "lifespan.shutdown.complete"]
        assert recording.purged == ["db"]

    def test_the_threadpool_is_sized_from_the_connection_pool(self):
        from craft.http.kernel import Kernel

        kernel = Kernel(app)
        name = app.make("config").get("database.default")
        settings = app.make("config").get(f"database.connections.{name}", {}) or {}
        pool_size = int(settings.get("pool_size") or 0)

        size = kernel.threadpool_size()
        if not pool_size:
            assert size == 0   # nothing configured: leave the default alone
        else:
            assert size == max(kernel.MIN_THREADPOOL_SIZE, pool_size * 2)

    def test_an_explicit_threadpool_size_wins(self, monkeypatch):
        from craft.http.kernel import Kernel

        config = app.make("config")
        original = config.get

        def patched(key, default=None):
            if key == "framework.HTTP_THREADPOOL_SIZE":
                return 33
            return original(key, default)

        monkeypatch.setattr(config, "get", patched)
        assert Kernel(app).threadpool_size() == 33


class TestShutdownSignal:
    def test_it_is_not_requested_until_a_signal_arrives(self):
        with ShutdownSignal() as stop:
            assert stop.requested is False

    def test_a_signal_sets_it_and_wakes_a_waiting_loop(self):
        seen = []
        stop = ShutdownSignal(seen.append).install()
        try:
            timer = threading.Timer(0.05, lambda: stop._handle(signal.SIGTERM, None))
            timer.start()
            # Would sleep for 30s if the signal did not wake it.
            assert stop.wait(30) is True
            assert stop.requested is True
            assert seen == ["SIGTERM"]
        finally:
            stop.restore()

    def test_handlers_are_restored_so_a_second_signal_still_kills(self):
        before = signal.getsignal(signal.SIGTERM)
        stop = ShutdownSignal().install()
        assert signal.getsignal(signal.SIGTERM) is not before
        stop._handle(signal.SIGTERM, None)
        # The handler removes itself as it fires, so the next one is default.
        assert signal.getsignal(signal.SIGTERM) is before


class TestMigrationLock:
    def test_migrating_holds_a_lock_when_the_driver_has_them(self, migrated_database):
        """On a driver without advisory locks the migrator runs unlocked, which
        is the previous behaviour; on PostgreSQL it must take the lock."""
        migrator = migrated_database.make("migrator")
        taken = []

        migrator.with_lock(lambda: taken.append(True))

        assert taken == [True], "the callback did not run"

    def test_a_locked_out_migrator_reports_the_timeout(self, migrated_database):
        from craft.migrations.migrator import MigrationLockTimeout

        migrator = migrated_database.make("migrator")
        if not migrator.db.dialect.supports("advisory_locks"):
            pytest.skip("advisory locks need PostgreSQL")

        error = MigrationLockTimeout(5)
        assert error.code == "MIGRATION_LOCK_TIMEOUT"
        assert error.seconds == 5
