"""The internal proxy routes module-to-module calls in memory.

External traffic goes through the HTTP kernel; internal calls resolve an
exposed service from the container and run in-process. The proxy is routing
infrastructure: it carries the caller's context unchanged and holds no
tenant, authorization or business rule.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import asyncio
import threading
import time

import pytest
from starlette.testclient import TestClient

from bootstrap.app import app, asgi_app
from craft.facades import Proxy, Route
from engine.container.application import Container
from engine.container.internal_proxy import InternalProxy, InternalProxyError
from engine.events.lifecycle import RequestTerminated
from engine.orm import tenancy
from engine.support import context as request_context


class Ledger:
    """A stand-in for another module's service."""

    def echo(self, payload: dict) -> dict:
        return payload

    def snapshot(self) -> dict:
        return {
            "tenant": tenancy.current_tenant_id(),
            "request_id": request_context.request_id(),
            "thread": threading.current_thread().name,
        }

    def slow_mark(self, marks: list) -> None:
        time.sleep(0.2)
        marks.append("finished")

    async def fetch(self, value: int) -> int:
        await asyncio.sleep(0)
        return value * 2

    def _secret(self) -> str:
        return "hidden"


class DurablePayment:
    durable = True


@pytest.fixture
def proxy() -> InternalProxy:
    container = Container()
    container.bind(Ledger)
    exposed = InternalProxy(container)
    exposed.expose("ledger", Ledger, {"echo", "snapshot", "slow_mark", "fetch"})
    return exposed


def _refusal(code_holder: pytest.ExceptionInfo) -> str:
    return code_holder.value.code


class TestWiring:
    def test_the_proxy_is_one_singleton_by_key_class_and_facade(self, migrated_database):
        proxy = app.make("proxy")
        assert isinstance(proxy, InternalProxy)
        assert app.make(InternalProxy) is proxy
        assert Proxy.exposed() == proxy.exposed()


class TestAllowlist:
    @pytest.mark.parametrize("method,code", [
        ("_secret", "INTERNAL_EXPOSE_PRIVATE_OR_EMPTY_METHOD"),
        ("", "INTERNAL_EXPOSE_PRIVATE_OR_EMPTY_METHOD"),
        ("missing", "INTERNAL_EXPOSE_UNKNOWN_METHOD"),
    ])
    def test_expose_refuses_what_must_never_be_callable(self, proxy, method, code):
        with pytest.raises(InternalProxyError) as refused:
            proxy.expose("ledger.bad", Ledger, {method})
        assert _refusal(refused) == code

    def test_an_unexposed_alias_is_refused(self, proxy):
        with pytest.raises(InternalProxyError) as refused:
            proxy.call("events", "dispatch")
        assert _refusal(refused) == "INTERNAL_TARGET_NOT_EXPOSED"

    def test_an_unexposed_method_is_refused(self, proxy):
        with pytest.raises(InternalProxyError) as refused:
            proxy.call("ledger", "_secret")
        assert _refusal(refused) == "INTERNAL_METHOD_NOT_EXPOSED"

    def test_the_manifest_is_read_only(self, proxy):
        with pytest.raises(TypeError):
            proxy.exposed()["ledger"] = None


class TestCalls:
    def test_call_passes_arguments_by_reference(self, proxy):
        payload = {"amount_cents": 1000}
        assert proxy.call("ledger", "echo", payload) is payload

    def test_call_refuses_a_coroutine(self, proxy):
        with pytest.raises(InternalProxyError) as refused:
            proxy.call("ledger", "fetch", 2)
        assert _refusal(refused) == "INTERNAL_ASYNC_HANDLER_FROM_SYNC_CALL"

    def test_dispatch_awaits_a_coroutine(self, proxy):
        assert asyncio.run(proxy.dispatch("ledger", "fetch", 21)) == 42

    def test_dispatch_runs_a_sync_target_off_the_event_loop_thread(self, proxy):
        async def run() -> tuple:
            seen = await proxy.dispatch("ledger", "snapshot")
            return seen["thread"], threading.current_thread().name

        target_thread, loop_thread = asyncio.run(run())
        assert target_thread != loop_thread

    def test_a_cancelled_caller_waits_for_the_thread_to_finish(self, proxy):
        marks: list = []

        async def run() -> None:
            task = asyncio.create_task(proxy.dispatch("ledger", "slow_mark", marks))
            await asyncio.sleep(0.05)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

        asyncio.run(run())
        assert marks == ["finished"]


class TestContextTravelsUnchanged:
    """Barrier 2 (the database) still sees the caller's tenant on the worker thread."""

    def test_each_concurrent_caller_keeps_its_own_tenant_and_request_id(self, proxy):
        async def as_tenant(tenant: str) -> dict:
            token = tenancy._current.set(tenant)
            try:
                with request_context.bind(request_id=f"req-{tenant}"):
                    return await proxy.dispatch("ledger", "snapshot")
            finally:
                tenancy._current.reset(token)

        async def run() -> list:
            return await asyncio.gather(as_tenant("tenant-a"), as_tenant("tenant-b"), as_tenant("owner"))

        seen = asyncio.run(run())
        assert [(s["tenant"], s["request_id"]) for s in seen] == [
            ("tenant-a", "req-tenant-a"),
            ("tenant-b", "req-tenant-b"),
            ("owner", "req-owner"),
        ]

    def test_the_proxy_never_invents_a_tenant(self, proxy):
        assert asyncio.run(proxy.dispatch("ledger", "snapshot"))["tenant"] is None


class TestEvents:
    def test_emit_delivers_an_in_memory_event(self, migrated_database):
        delivered = []

        class OrderPlaced:
            pass

        app.make("events").listen(OrderPlaced, lambda event: delivered.append(event))
        event = OrderPlaced()
        app.make("proxy").emit(event)
        assert delivered == [event]

    def test_emit_refuses_a_durable_event(self, proxy):
        with pytest.raises(InternalProxyError) as refused:
            proxy.emit(DurablePayment())
        assert _refusal(refused) == "INTERNAL_DURABLE_EVENT"


class TestKernelBypass:
    """An external request crosses the kernel once; the internal call never does."""

    @pytest.fixture(autouse=True)
    def route_calling_a_module(self, migrated_database):
        proxy = app.make("proxy")
        app.bind(Ledger)
        proxy.expose("tests.ledger", Ledger, {"echo"})

        def checkout(request):
            return proxy.call("tests.ledger", "echo", {"status": "invoiced"})

        Route.get("/t/proxy-checkout", checkout).name("t.proxy.checkout")
        yield

    def test_one_kernel_pass_for_a_request_that_calls_another_module(self):
        passes = []
        app.make("events").listen(RequestTerminated, lambda event: passes.append(event))
        try:
            response = TestClient(asgi_app).get("/t/proxy-checkout")
        finally:
            app.make("events").forget(RequestTerminated)
            _restore_database_listener()
        assert response.json() == {"status": "invoiced"}
        assert len(passes) == 1

    def test_a_proxy_call_is_far_cheaper_than_loopback_http(self):
        proxy = app.make("proxy")
        client = TestClient(asgi_app)
        in_memory = _seconds_per_call(lambda: proxy.call("tests.ledger", "echo", {}), 200)
        loopback = _seconds_per_call(lambda: client.get("/t/proxy-checkout"), 20)
        print(f"proxy_call_seconds={in_memory:.7f} loopback_http_seconds={loopback:.7f}")
        assert in_memory * 10 < loopback


def _seconds_per_call(work, repeat: int) -> float:
    started = time.perf_counter()
    for _ in range(repeat):
        work()
    return (time.perf_counter() - started) / repeat


def _restore_database_listener() -> None:
    """Re-register the database's listener that `forget` removed with the probe."""
    from engine.providers.service_providers import DatabaseServiceProvider

    DatabaseServiceProvider(app).listen_for_request_end()
