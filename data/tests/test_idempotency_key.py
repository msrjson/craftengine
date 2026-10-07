"""The `Idempotency-Key` middleware: a retried write runs its handler once."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from types import SimpleNamespace

import pytest
from starlette.responses import JSONResponse

from craft.cache.manager import CacheManager
from craft.http.middleware import IdempotencyKey


class _Request:
    """Only the surface the middleware touches."""

    def __init__(self, method="POST", path="/payments", key=None, user=None):
        self.method = method
        self.url = SimpleNamespace(path=path)
        self.headers = {} if key is None else {"idempotency-key": key}
        self._session = {"auth_user_id": user} if user is not None else {}

    def has_session(self):
        return bool(self._session)

    def session(self):
        return self._session


class _App:
    """A container stand-in: the middleware only asks for cache and config."""

    def __init__(self):
        self._cache = CacheManager()
        self._config = {
            "framework.IDEMPOTENCY_TTL": 3600,
            "framework.IDEMPOTENCY_LOCK_TTL": 30,
        }

    def make(self, name):
        if name == "cache":
            return self._cache
        if name == "config":
            return SimpleNamespace(get=lambda key, default=None: self._config.get(key, default))
        raise KeyError(name)


class _Counter:
    def __init__(self, status=200):
        self.calls = 0
        self.status = status

    def __call__(self, request):
        self.calls += 1
        return JSONResponse({"call": self.calls}, status_code=self.status)


@pytest.fixture
def middleware():
    return IdempotencyKey(app=_App())


def test_a_retried_write_is_replayed_not_run_twice(middleware):
    handler = _Counter()
    request = _Request(key="k-1")

    first = middleware.handle(request, handler)
    second = middleware.handle(request, handler)

    assert handler.calls == 1
    assert second.body == first.body
    assert second.headers["Idempotency-Replayed"] == "true"
    assert "Idempotency-Replayed" not in first.headers


def test_a_different_key_runs_the_handler_again(middleware):
    handler = _Counter()
    middleware.handle(_Request(key="k-1"), handler)
    middleware.handle(_Request(key="k-2"), handler)
    assert handler.calls == 2


def test_a_write_without_the_header_is_untouched(middleware):
    handler = _Counter()
    middleware.handle(_Request(), handler)
    middleware.handle(_Request(), handler)
    assert handler.calls == 2


def test_a_safe_method_is_never_replayed(middleware):
    handler = _Counter()
    middleware.handle(_Request(method="GET", key="k-1"), handler)
    middleware.handle(_Request(method="GET", key="k-1"), handler)
    assert handler.calls == 2


def test_an_in_flight_key_is_refused_with_409(middleware):
    handler = _Counter()
    request = _Request(key="k-1")
    # Simulate the first request still running: it holds the key with no
    # stored response yet.
    key = middleware._cache_key(request, "k-1")
    middleware._cache().add(f"{key}:lock", True, 30)

    with pytest.raises(Exception) as error:
        middleware.handle(request, handler)

    assert getattr(error.value, "status_code", None) == 409
    assert handler.calls == 0


def test_the_key_is_scoped_to_the_user(middleware):
    handler = _Counter()
    request = _Request(key="shared")
    middleware.handle(request, handler)

    other = _Request(key="shared", user="7")
    middleware.handle(other, handler)
    # A different user cannot replay the first user's response.
    assert handler.calls == 2


def test_a_server_error_is_not_stored(middleware):
    handler = _Counter(status=500)
    request = _Request(key="k-1")
    middleware.handle(request, handler)
    middleware.handle(request, handler)
    assert handler.calls == 2


def test_a_successful_status_is_replayed_even_when_not_200(middleware):
    handler = _Counter(status=202)
    request = _Request(key="k-1")
    first = middleware.handle(request, handler)
    second = middleware.handle(request, handler)
    assert handler.calls == 1
    assert first.status_code == 202 and second.status_code == 202


def test_the_lock_is_released_after_a_failure(middleware):
    def boom(request):
        raise RuntimeError("handler blew up")

    with pytest.raises(RuntimeError):
        middleware.handle(_Request(key="k-1"), boom)

    # The key is free again, so a retry runs rather than being told 409.
    handler = _Counter()
    middleware.handle(_Request(key="k-1"), handler)
    assert handler.calls == 1
