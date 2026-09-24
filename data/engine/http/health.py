"""Liveness and readiness probes for Craft Framework.

Two questions a load balancer and an orchestrator ask, and they are not the
same one. Liveness asks "is this process wedged, should it be killed" and must
touch nothing external: a probe that fails because the database is down gets
every healthy web instance restarted during a database incident, turning one
outage into two. Readiness asks "can this instance serve traffic right now"
and does check dependencies, so an instance whose pool is exhausted is taken
out of rotation instead of returning errors.

Readiness answers its verdict to everyone and its detail to no one, unless
`HEALTH_READINESS_TOKEN` is configured and presented: the detailed payload
names the database driver, the cache store and the pool census, which is a map
of the installation and of how close it is to exhaustion. The result is also
shared for a few seconds across requests, so probing costs a bounded amount of
dependency work rather than one query and one cache write per hit.

Category: Core Framework (HTTP).
Relations:
  - Routes are registered on `engine/http/router.py` as engine routes and
    dispatched by `engine/http/kernel.py` outside the middleware stack, so a
    probe costs no session load, no CSRF check and no user lookup - and still
    appears in every route listing.
  - Reads pool statistics from `engine/orm/connection.py`.
References:
  - Guide: `documentation/deployment.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

#: Wall-clock start of this process, for the uptime the liveness probe reports.
_STARTED_AT = time.time()

#: The two states readiness reports, in both its detailed and its reduced form.
#: One vocabulary on purpose: an orchestrator that parses `status` must not read
#: a different word depending on whether it holds the token.
READY_STATUS = "ok"
NOT_READY_STATUS = "unavailable"


class HealthCheck:
    """One named dependency probe returning `(healthy, details)`."""

    __slots__ = ("name", "probe", "critical")

    def __init__(self, name: str, probe: Callable[[], Dict[str, Any]], *, critical: bool = True):
        self.name = name
        self.probe = probe
        #: A non-critical failure is reported but does not fail readiness, for
        #: dependencies the application degrades around rather than needs.
        self.critical = critical

    def run(self) -> Tuple[bool, Dict[str, Any]]:
        started = time.monotonic()
        try:
            details = self.probe() or {}
            healthy = bool(details.pop("healthy", True))
        except Exception as exc:
            return False, {
                "status": "fail",
                "error": type(exc).__name__,
                "duration_ms": round((time.monotonic() - started) * 1000, 2),
            }
        details["status"] = "pass" if healthy else "fail"
        details["duration_ms"] = round((time.monotonic() - started) * 1000, 2)
        return healthy, details


class HealthReporter:
    """Builds the liveness and readiness payloads.

    The checks are resolved lazily from the container, so a probe never boots a
    service that the request path has not booted yet.
    """

    def __init__(
        self,
        app: Any,
        checks: Optional[List[HealthCheck]] = None,
        *,
        cache_seconds: float = 0.0,
    ):
        """Build a reporter.

        Args:
            app: The application container the checks resolve services from.
            checks: The dependency probes to run; the defaults when omitted.
            cache_seconds: How long one readiness result is reused by every
                request that arrives behind it. Zero runs the checks on every
                call.
        """
        self.app = app
        self._checks = checks if checks is not None else self.default_checks()
        self._cache_seconds = max(0.0, float(cache_seconds))
        self._lock = threading.Lock()
        self._cached: Optional[Tuple[Dict[str, Any], int]] = None
        self._cached_at: float = 0.0

    # -- checks ----------------------------------------------------------------

    def default_checks(self) -> List[HealthCheck]:
        return [
            HealthCheck("database", self._check_database),
            HealthCheck("cache", self._check_cache, critical=False),
        ]

    def add_check(self, check: HealthCheck) -> "HealthReporter":
        self._checks.append(check)
        return self

    def _check_database(self) -> Dict[str, Any]:
        """A real round-trip plus the pool census.

        `SELECT 1` rather than an ORM call on purpose: it proves the socket and
        the server, not the schema. The pool numbers ride along because an
        instance whose pool is fully checked out is the one a load balancer
        should stop sending work to, and that is invisible from the outside.
        """
        db = self.app.make("db")
        db.statement("SELECT 1")
        connection = db.write_connection
        stats = connection.pool_stats
        return {
            "driver": connection.driver,
            "pool_open": stats["open"],
            "pool_idle": stats["idle"],
            "pool_size": connection.pool_size,
        }

    def _check_cache(self) -> Dict[str, Any]:
        cache = self.app.make("cache")
        key = "health.probe"
        cache.put(key, "1", 10)
        return {"healthy": cache.get(key) == "1", "store": type(cache.store).__name__}

    # -- payloads --------------------------------------------------------------

    def liveness(self) -> Tuple[Dict[str, Any], int]:
        """Is the process itself alive. Touches nothing external, never fails."""
        return {
            "status": "ok",
            "uptime_seconds": round(time.time() - _STARTED_AT, 1),
        }, 200

    def readiness(self) -> Tuple[Dict[str, Any], int]:
        """Can this instance serve traffic. 503 when a critical check fails.

        Every call used to issue a database round-trip and a cache write, which
        made an unauthenticated path a load amplifier: one request in, two
        dependency operations out, at whatever rate the caller chose. One
        result is now shared for `cache_seconds`, so the cost of being probed
        is bounded by time rather than by traffic.

        Returns:
            The detailed payload and the HTTP status. The payload is shared
            between the callers served from one result and must not be mutated;
            `summarise()` returns a new mapping.
        """
        cached = self._cached_readiness()
        if cached is not None:
            return cached

        result = self._collect_readiness()
        if self._cache_seconds:
            with self._lock:
                self._cached, self._cached_at = result, time.monotonic()
        return result

    def _collect_readiness(self) -> Tuple[Dict[str, Any], int]:
        """Run every check and assemble the detailed payload."""
        results: Dict[str, Any] = {}
        ready = True
        for check in self._checks:
            healthy, details = check.run()
            results[check.name] = details
            if not healthy and check.critical:
                ready = False
        payload = {"status": READY_STATUS if ready else NOT_READY_STATUS, "checks": results}
        return payload, 200 if ready else 503

    def _cached_readiness(self) -> Optional[Tuple[Dict[str, Any], int]]:
        """Return the stored result while it is still fresh, otherwise None."""
        if not self._cache_seconds:
            return None
        with self._lock:
            if self._cached is None:
                return None
            if time.monotonic() - self._cached_at >= self._cache_seconds:
                return None
            return self._cached

    @staticmethod
    def summarise(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Reduce a readiness payload to what an unauthenticated caller may see.

        The detailed payload names the database driver, the cache store class
        and the connection-pool census. That is a map of the installation and
        of how close it is to exhaustion, so it is returned only to a caller
        holding the readiness token. Everyone else gets the decision itself,
        which is all a load balancer needs to route on.

        Args:
            payload: The detailed readiness payload.

        Returns:
            A new mapping carrying only the status.
        """
        return {"status": payload.get("status", NOT_READY_STATUS)}


#: Dotted module recorded as the attribution of the routes below.
PROVIDER = "engine.http.health"

#: Seconds one readiness result serves every request behind it. Five is short
#: enough that an orchestrator polling every ten seconds still sees each run,
#: and long enough that a flood costs one round-trip instead of thousands.
DEFAULT_READINESS_CACHE_SECONDS = 5.0


def _probe_endpoint(producer: Callable[[], Tuple[Dict[str, Any], int]]) -> Callable:
    """Wrap a payload producer in an ASGI endpoint.

    Args:
        producer: Returns the payload and the HTTP status to answer with.

    Returns:
        An endpoint that runs the probe off the event loop.
    """
    from starlette.responses import JSONResponse

    async def endpoint(request: Any) -> Any:
        payload, status = await _run_probe(producer)
        return JSONResponse(payload, status_code=status)

    return endpoint


def _readiness_endpoint(reporter: "HealthReporter", token: str) -> Callable:
    """Wrap the readiness reporter in an ASGI endpoint that guards its detail.

    The route answers for everyone - hiding it behind a 404 would defeat the
    probe it exists to be - but the detailed payload is for a caller holding
    the token. Without a configured token nobody gets the detail, so a probe
    works out of the box without anyone being made to configure a secret.

    Args:
        reporter: The reporter producing the payload.
        token: The expected bearer token; empty disables the detailed form.

    Returns:
        An endpoint that runs the probe off the event loop.
    """
    from starlette.responses import JSONResponse

    async def endpoint(request: Any) -> Any:
        payload, status = await _run_probe(reporter.readiness)
        if not token or not _token_matches(request, token):
            payload = HealthReporter.summarise(payload)
        return JSONResponse(payload, status_code=status)

    return endpoint


def register_health_routes(app: Any, router: Any) -> None:
    """Register the probe routes on the router, if the application asked for them.

    Off unless `framework.HEALTH_ROUTES_ENABLED` says otherwise: a probe is an
    unauthenticated path into the installation, and one an application should
    acquire deliberately. Readiness is further reduced to its verdict unless
    `HEALTH_READINESS_TOKEN` is set and presented, and its result is shared for
    `HEALTH_READINESS_CACHE_SECONDS` so being probed costs a bounded amount of
    database and cache work whatever the request rate. They are registered as
    engine routes, which the kernel dispatches outside the middleware stack: no
    session, no CSRF check, no user lookup.

    Args:
        app: The application container.
        router: The router the routes are recorded on.
    """
    config = app.make("config")
    if not config.get("framework.HEALTH_ROUTES_ENABLED", False):
        return

    live_path = str(config.get("framework.HEALTH_LIVENESS_PATH", "/health"))
    ready_path = str(config.get("framework.HEALTH_READINESS_PATH", "/ready"))
    reporter = HealthReporter(app, cache_seconds=_readiness_cache_seconds(config))
    token = str(config.get("framework.HEALTH_READINESS_TOKEN", "") or "")
    claimed = router.claimed_uris()

    probes = (
        (live_path, _probe_endpoint(reporter.liveness), "health.liveness"),
        (ready_path, _readiness_endpoint(reporter, token), "health.readiness"),
    )
    for path, endpoint, name in probes:
        if path not in claimed:
            router.add_engine_route(["GET"], path, endpoint, name=name, provider=PROVIDER)

    register_metrics_route(app, router)


def _readiness_cache_seconds(config: Any) -> float:
    """Read how long one readiness result is reused, defaulting when unusable.

    Args:
        config: The configuration repository.

    Returns:
        A non-negative number of seconds; zero runs the checks on every hit.
    """
    try:
        return max(0.0, float(config.get("framework.HEALTH_READINESS_CACHE_SECONDS", DEFAULT_READINESS_CACHE_SECONDS)))
    except (TypeError, ValueError):
        return DEFAULT_READINESS_CACHE_SECONDS


def register_metrics_route(app: Any, router: Any) -> None:
    """Register the scrape endpoint, off by default.

    Off unless asked for, because the payload names every route the
    application serves and how often each is hit, which is reconnaissance if
    the endpoint is reachable from outside. Enable it and keep it on an
    internal network, or set `METRICS_TOKEN` and have the scraper send it as a
    bearer token.

    Args:
        app: The application container.
        router: The router the route is recorded on.
    """
    from starlette.responses import PlainTextResponse, Response

    config = app.make("config")
    if not config.get("framework.METRICS_ENABLED", False):
        return

    path = str(config.get("framework.METRICS_PATH", "/metrics"))
    token = str(config.get("framework.METRICS_TOKEN", "") or "")
    if path in router.claimed_uris():
        return

    async def endpoint(request: Any) -> Any:
        if token and not _token_matches(request, token):
            return Response(status_code=404)
        from engine.support.metrics import registry

        body = await _render_metrics(registry)
        return PlainTextResponse(body, media_type="text/plain; version=0.0.4")

    router.add_engine_route(["GET"], path, endpoint, name="metrics", provider=PROVIDER)


def _token_matches(request: Any, expected: str) -> bool:
    """Compare the bearer token without leaking its length through timing.

    What a failed comparison costs the caller differs by route, deliberately.
    The metrics endpoint answers 404, because the whole route is a secret and
    one that admits it exists is worth guessing at. Readiness answers its
    reduced payload, because an orchestrator has to be able to probe it: a
    health check that 404s without a token is a health check nobody can use.

    Args:
        request: The incoming request.
        expected: The configured token.

    Returns:
        True when the request carries exactly that bearer token.
    """
    import hmac

    header = request.headers.get("authorization", "")
    scheme, _, presented = header.partition(" ")
    if scheme.lower() != "bearer":
        return False
    return hmac.compare_digest(presented.strip(), expected)


async def _render_metrics(registry: Any) -> str:
    """Render on a worker thread: the pool gauge issues no query, but a
    registry-wide render walks every series and a custom gauge may block."""
    from starlette.concurrency import run_in_threadpool

    from engine.container.application import Container

    def run() -> str:
        try:
            return registry.render()
        finally:
            try:
                Container.getInstance().make("db").release()
            except Exception:
                pass

    return await run_in_threadpool(run)


async def _run_probe(producer: Callable[[], Tuple[Dict[str, Any], int]]) -> Tuple[Dict[str, Any], int]:
    """Run a probe off the event loop, and release the connection it borrowed.

    The readiness check issues a blocking query, so it belongs on a worker
    thread like every other database call in this framework. The `release()` is
    the same request boundary the kernel applies: without it a probe every ten
    seconds would hold a pooled connection per probing thread forever.
    """
    from starlette.concurrency import run_in_threadpool

    from engine.container.application import Container

    def run() -> Tuple[Dict[str, Any], int]:
        try:
            return producer()
        finally:
            try:
                Container.getInstance().make("db").release()
            except Exception:
                pass

    return await run_in_threadpool(run)
