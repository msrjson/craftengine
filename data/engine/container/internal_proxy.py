"""Internal proxy: module-to-module calls in memory, never through the HTTP kernel.

External traffic enters through the HTTP kernel and its full middleware stack.
Internal traffic - one module calling another module's service - goes through
this proxy instead: the target is resolved from the container and its method
runs in-process, with no request building, serialization, socket or middleware.

The proxy is routing infrastructure and nothing more. It holds no tenant,
authorization or business rule: the caller's context (tenant, connection,
user, locale, request id) lives in context variables and travels with the
call unchanged, including onto the worker thread a synchronous target runs on.
Tenant isolation stays with its two barriers - the modules and controllers,
and the database.

Only what a module exposes can be called. A provider declares it at boot:

    proxy.expose("billing", BillingService, {"generate_invoice"})

and any module calls it:

    invoice = await proxy.dispatch("billing", "generate_invoice", order_id)
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Iterable, Mapping
from types import MappingProxyType
from typing import Any


class InternalProxyError(RuntimeError):
    """A call the proxy refuses: a programming error, never a user-facing one.

    Args:
        code: Machine code naming the refusal.
        target: The alias that was called.
        method: The method that was called, when there is one.
    """

    message_key = "internal_proxy.error.refused"

    def __init__(self, code: str, target: str, method: str = "") -> None:
        super().__init__(code, target, method)
        self.code = code
        self.target = target
        self.method = method


class InternalProxy:
    """Resolve an exposed service from the container and call it in memory.

    Args:
        container: The application container the targets are resolved from.
    """

    def __init__(self, container: Any) -> None:
        self._container = container
        self._exposed: dict[str, tuple[Any, frozenset[str]]] = {}

    def expose(self, alias: str, abstract: Any, methods: Iterable[str]) -> None:
        """Allow `methods` of the service bound as `abstract` to be called as `alias`.

        Everything not exposed is refused. Private or empty method names are
        refused here, and so is a method the target class does not define, so
        a typo fails at boot instead of on the first call.

        Raises:
            InternalProxyError: A method name is private, empty or undefined.
        """
        allowed = frozenset(methods)
        for method in allowed:
            if not method or method.startswith("_"):
                raise InternalProxyError("INTERNAL_EXPOSE_PRIVATE_OR_EMPTY_METHOD", alias, method)
            target_class = abstract if inspect.isclass(abstract) else None
            if target_class is not None and not callable(getattr(target_class, method, None)):
                raise InternalProxyError("INTERNAL_EXPOSE_UNKNOWN_METHOD", alias, method)
        self._exposed[alias] = (abstract, allowed)

    def exposed(self) -> Mapping[str, tuple[Any, frozenset[str]]]:
        """Return a read-only view of every exposed alias and its methods."""
        return MappingProxyType(dict(self._exposed))

    def call(self, alias: str, method: str, /, *args: Any, **kwargs: Any) -> Any:
        """Call a synchronous exposed method on the caller's thread.

        Raises:
            InternalProxyError: The target is not exposed, or it is a coroutine
                (use `dispatch`; running it here would block an event loop).
        """
        handler = self._handler(alias, method)
        if inspect.iscoroutinefunction(handler):
            raise InternalProxyError("INTERNAL_ASYNC_HANDLER_FROM_SYNC_CALL", alias, method)
        return handler(*args, **kwargs)

    async def dispatch(self, alias: str, method: str, /, *args: Any, **kwargs: Any) -> Any:
        """Call an exposed method from async code without blocking the event loop.

        A coroutine is awaited. A synchronous method runs on a worker thread
        with a copy of the caller's context, so the tenant, the connection and
        the request id travel with it.

        Raises:
            InternalProxyError: The target is not exposed.
        """
        handler = self._handler(alias, method)
        if inspect.iscoroutinefunction(handler):
            return await handler(*args, **kwargs)
        return await _until_the_thread_ends(asyncio.to_thread(handler, *args, **kwargs))

    def emit(self, event: Any) -> list[Any]:
        """Deliver an in-memory event to its listeners and return their results.

        Events marked `durable = True` (money, anything that must survive a
        crash) are refused: they belong to the queue or an outbox.

        Raises:
            InternalProxyError: The event is durable.
        """
        if getattr(event, "durable", False):
            raise InternalProxyError("INTERNAL_DURABLE_EVENT", type(event).__name__)
        return self._container.make("events").dispatch(event)

    def _handler(self, alias: str, method: str) -> Any:
        """Return the bound method `alias.method`, refusing anything not exposed."""
        exposed = self._exposed.get(alias)
        if exposed is None:
            raise InternalProxyError("INTERNAL_TARGET_NOT_EXPOSED", alias, method)
        abstract, methods = exposed
        if method not in methods:
            raise InternalProxyError("INTERNAL_METHOD_NOT_EXPOSED", alias, method)
        return getattr(self._container.make(abstract), method)


async def _until_the_thread_ends(work: Any) -> Any:
    """Await `work`; if the caller is cancelled, wait for the thread before re-raising.

    A cancelled await does not stop the worker thread. Returning early would
    let the request end - and its pooled connection be released - while that
    thread still runs a transaction on it.
    """
    task = asyncio.ensure_future(work)
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        await asyncio.wait({task})
        raise


__all__ = ["InternalProxy", "InternalProxyError"]
