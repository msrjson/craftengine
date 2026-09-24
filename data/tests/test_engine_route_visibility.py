"""Nothing answers a request without being declared and listed.

The framework used to append its own routes straight onto the ASGI route
table: the health probes, the metrics scrape, the MSR manifest and the static
mount answered requests that `route:list` - which reads the router - could not
see. A freshly generated project declaring one route answered on three paths,
and the developer had no way to find that out short of reading the engine.

Two guarantees are covered here. Visibility: every route the framework
attaches is recorded on the router, marked with its origin and the module that
registered it. Opt-in: the probes and the manifest do not answer until the
application's configuration says so.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from typing import Any, Dict, Generator, List

import pytest
from starlette.testclient import TestClient

from bootstrap.app import app, asgi_app, kernel
from craft.http.router import APP_ORIGIN, ENGINE_ORIGIN
from craft.support.msr import MANIFEST_PATH

#: Configuration flags that govern the opt-in engine routes.
FLAGS = (
    "framework.HEALTH_ROUTES_ENABLED",
    "framework.METRICS_ENABLED",
    "framework.HEALTH_READINESS_TOKEN",
    "framework.HEALTH_READINESS_CACHE_SECONDS",
    "msr.ENABLED",
)

#: Bearer token the readiness tests configure. Never a real secret.
READINESS_TOKEN = "readiness-token-for-tests"

#: Keys the detailed readiness payload carries and the reduced one must not.
DISCLOSED_KEYS = ("driver", "pool_open", "pool_idle", "pool_size", "store")


def set_flags(**values: bool) -> None:
    """Apply configuration flags and rebuild the engine route table.

    Args:
        values: Flag names with dots replaced by double underscores, mapped to
            the value to set.
    """
    config = app.make("config")
    for name, value in values.items():
        config.set(name.replace("__", "."), value)
    kernel.register_engine_routes(refresh=True)


@pytest.fixture
def default_configuration(migrated_database) -> Generator[Any, None, None]:
    """Run a test with every opt-in engine route off, and restore afterwards."""
    config = app.make("config")
    saved = {name: config.get(name) for name in FLAGS}
    set_flags(
        framework__HEALTH_ROUTES_ENABLED=False,
        framework__METRICS_ENABLED=False,
        framework__HEALTH_READINESS_TOKEN="",
        framework__HEALTH_READINESS_CACHE_SECONDS=0,
        msr__ENABLED=False,
    )
    yield config
    for name, value in saved.items():
        config.set(name, value)
    kernel.register_engine_routes(refresh=True)


def engine_table() -> List[Dict[str, Any]]:
    """Return the engine routes as the mappings a listing renders."""
    return [route.describe() for route in kernel.engine_routes()]


class TestNothingAnswersUndeclared:
    """A project that asked for nothing answers only what it declared."""

    def test_the_liveness_probe_is_not_served(self, default_configuration):
        assert TestClient(asgi_app).get("/health").status_code == 404

    def test_the_readiness_probe_is_not_served(self, default_configuration):
        assert TestClient(asgi_app).get("/ready").status_code == 404

    def test_the_metrics_endpoint_is_not_served(self, default_configuration):
        assert TestClient(asgi_app).get("/metrics").status_code == 404

    def test_the_manifest_is_not_served(self, default_configuration):
        """404 because the route does not exist, not because it is incomplete."""
        assert TestClient(asgi_app).get(MANIFEST_PATH).status_code == 404
        assert MANIFEST_PATH not in {route["uri"] for route in engine_table()}

    def test_the_declared_route_still_answers(self, default_configuration):
        # "/" is the one route this application declares (routes/web.py).
        assert TestClient(asgi_app).get("/").status_code == 200


class TestTurningThemOn:
    """The flag in `config/` is the whole switch."""

    def test_the_probes_answer_once_enabled(self, default_configuration):
        set_flags(framework__HEALTH_ROUTES_ENABLED=True)
        client = TestClient(asgi_app)

        assert client.get("/health").json()["status"] == "ok"
        # The verdict, which is what an orchestrator routes on. The detail
        # behind it needs the token; `TestReadinessDisclosesNothingByDefault`
        # covers both sides of that.
        assert client.get("/ready").json() == {"status": "ok"}

    def test_the_manifest_answers_once_enabled(self, default_configuration):
        default_configuration.set("msr.DOMAIN", "shop.example.com")
        default_configuration.set("lang.en.msr.entity.summary", "An application summary.")
        try:
            set_flags(msr__ENABLED=True)
            response = TestClient(asgi_app).get(MANIFEST_PATH)
        finally:
            default_configuration.set("msr.DOMAIN", "")
            default_configuration.set("lang.en.msr.entity.summary", None)

        assert response.status_code == 200
        assert response.json()["entity"]["domain"] == "shop.example.com"

    def test_turning_one_off_again_removes_the_route(self, default_configuration):
        set_flags(framework__HEALTH_ROUTES_ENABLED=True)
        assert TestClient(asgi_app).get("/health").status_code == 200

        set_flags(framework__HEALTH_ROUTES_ENABLED=False)
        assert TestClient(asgi_app).get("/health").status_code == 404


class TestEngineRoutesAreListable:
    """Whatever answers is on the router, attributed to whoever attached it."""

    def test_the_static_mount_is_recorded_even_though_it_never_opts_out(self, default_configuration):
        mounts = [route for route in engine_table() if route["mount"]]

        assert [route["uri"] for route in mounts] == ["/"]
        assert mounts[0]["name"] == "static"
        assert mounts[0]["provider"] == "engine.http.kernel"
        assert mounts[0]["origin"] == ENGINE_ORIGIN

    def test_an_enabled_probe_names_the_module_that_attached_it(self, default_configuration):
        set_flags(framework__HEALTH_ROUTES_ENABLED=True)
        probes = {route["uri"]: route for route in engine_table()}

        assert probes["/health"]["name"] == "health.liveness"
        assert probes["/health"]["method"] == "GET"
        assert probes["/health"]["provider"] == "engine.http.health"
        assert probes["/ready"]["name"] == "health.readiness"

    def test_the_manifest_route_is_attributed(self, default_configuration):
        set_flags(msr__ENABLED=True)
        manifest = {route["uri"]: route for route in engine_table()}[MANIFEST_PATH]

        assert manifest["name"] == "msr.manifest"
        assert manifest["provider"] == "engine.http.msr"
        assert manifest["method"] == "GET|HEAD"

    def test_application_routes_are_not_confused_with_engine_ones(self, default_configuration):
        router = app.make("router")

        assert all(route.origin == APP_ORIGIN for route in router.application_routes())
        assert all(route.origin == ENGINE_ORIGIN for route in router.engine_routes())
        assert len(router.routes) == len(router.application_routes()) + len(router.engine_routes())

    def test_registering_twice_does_not_duplicate_the_table(self, default_configuration):
        set_flags(framework__HEALTH_ROUTES_ENABLED=True)
        before = len(kernel.engine_routes())

        kernel.register_engine_routes()
        kernel.register_engine_routes()

        assert len(kernel.engine_routes()) == before


class TestApplicationRoutesWin:
    """A project that declares the path keeps its own handler."""

    def test_a_declared_probe_path_takes_precedence(self, default_configuration):
        from craft.facades import Route

        router = app.make("router")
        Route.get("/health", lambda: {"status": "mine"}).name("app.health")
        try:
            set_flags(framework__HEALTH_ROUTES_ENABLED=True)
            assert "/health" not in {route.uri for route in router.engine_routes()}
            assert TestClient(asgi_app).get("/health").json() == {"status": "mine"}
        finally:
            router.routes = [route for route in router.routes if route._name != "app.health"]
            router._version += 1


def disclosed(payload: Dict[str, Any]) -> List[str]:
    """Return the infrastructure facts a payload exposes, at any depth.

    Args:
        payload: A readiness response body.

    Returns:
        The names of the disclosing keys found anywhere in it.
    """
    found: List[str] = []
    for name, value in payload.items():
        if name in DISCLOSED_KEYS:
            found.append(name)
        if isinstance(value, dict):
            found.extend(disclosed(value))
    return found


class TestReadinessDisclosesNothingByDefault:
    """The verdict is public; the map of the installation is not.

    The detailed payload names the database driver, the cache store class and
    the connection-pool census - what the installation runs on and how close it
    is to exhaustion - to anyone who found the path.
    """

    def test_without_a_configured_token_nobody_gets_the_detail(self, default_configuration):
        set_flags(framework__HEALTH_ROUTES_ENABLED=True)
        payload = TestClient(asgi_app).get("/ready").json()

        assert payload == {"status": "ok"}
        assert disclosed(payload) == []

    def test_a_caller_without_the_token_gets_the_verdict_only(self, default_configuration):
        set_flags(
            framework__HEALTH_ROUTES_ENABLED=True,
            framework__HEALTH_READINESS_TOKEN=READINESS_TOKEN,
        )
        payload = TestClient(asgi_app).get("/ready").json()

        assert payload == {"status": "ok"}
        assert "checks" not in payload

    def test_a_wrong_token_is_answered_not_hidden(self, default_configuration):
        """404 would break the probe for the orchestrator that needs it."""
        set_flags(
            framework__HEALTH_ROUTES_ENABLED=True,
            framework__HEALTH_READINESS_TOKEN=READINESS_TOKEN,
        )
        response = TestClient(asgi_app).get("/ready", headers={"Authorization": "Bearer wrong"})

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_the_token_unlocks_the_detailed_payload(self, default_configuration):
        set_flags(
            framework__HEALTH_ROUTES_ENABLED=True,
            framework__HEALTH_READINESS_TOKEN=READINESS_TOKEN,
        )
        response = TestClient(asgi_app).get(
            "/ready", headers={"Authorization": f"Bearer {READINESS_TOKEN}"}
        )
        payload = response.json()

        assert response.status_code == 200
        assert payload["checks"]["database"]["status"] == "pass"
        assert set(disclosed(payload)) == set(DISCLOSED_KEYS)

    def test_liveness_never_touched_a_dependency_to_begin_with(self, default_configuration):
        set_flags(framework__HEALTH_ROUTES_ENABLED=True)
        payload = TestClient(asgi_app).get("/health").json()

        assert disclosed(payload) == []
        assert "checks" not in payload


class TestProbingIsNotALoadAmplifier:
    """One probe result serves every request behind it, for a few seconds.

    Each readiness run issues a database round-trip and a cache write, so
    without this an unauthenticated path converts request rate into dependency
    load at whatever rate the caller picks.
    """

    def counting_reporter(self, cache_seconds: float):
        """Build a reporter whose single check records how often it ran."""
        from craft.http.health import HealthCheck, HealthReporter

        runs: List[int] = []

        def probe() -> Dict[str, Any]:
            runs.append(1)
            return {"healthy": True}

        reporter = HealthReporter(app, checks=[HealthCheck("probe", probe)], cache_seconds=cache_seconds)
        return reporter, runs

    def test_repeated_probes_share_one_run(self, default_configuration):
        reporter, runs = self.counting_reporter(cache_seconds=30)

        for _ in range(25):
            payload, status = reporter.readiness()

        assert status == 200
        assert payload["status"] == "ok"
        assert len(runs) == 1

    def test_zero_seconds_runs_the_checks_every_time(self, default_configuration):
        """The cache is a cap on cost, never a way to miss a state change."""
        reporter, runs = self.counting_reporter(cache_seconds=0)

        for _ in range(3):
            reporter.readiness()

        assert len(runs) == 3

    def test_an_expired_result_is_collected_again(self, default_configuration):
        reporter, runs = self.counting_reporter(cache_seconds=30)
        reporter.readiness()
        reporter._cached_at -= 31

        reporter.readiness()

        assert len(runs) == 2
