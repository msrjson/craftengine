"""Internal proxy: module-to-module calls in memory, never through the HTTP kernel.

External traffic enters through the HTTP kernel and its full middleware stack.
Internal traffic - one module calling another module's service - goes through
this proxy instead: the target is resolved from the container and its method
runs in-process, with no request building, serialization, socket or middleware.

The proxy is routing infrastructure and nothing more. It holds no tenant,
authorization or business rule. Every target runs on the caller's own thread,
so it shares the caller's context (tenant, user, locale, request id), its
pooled database connection and any transaction the caller has open. Tenant
isolation stays with its two barriers - the modules and controllers, and the
database.

Only what a module exposes can be called. A provider declares it at boot:

    proxy.expose("billing", BillingService, {"generate_invoice"})

and any module calls it:

    invoice = await proxy.dispatch("billing", "generate_invoice", order_id)
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import inspect
from collections.abc import Iterable, Mapping
from types import MappingProxyType
from typing import Any, Protocol


class OwnerGate(Protocol):
    """Decides whether an extension owning exposed methods may be called.

    The extension manager installs itself as the gate; without one, owned
    exposures behave like unowned ones.
    """

    def allow(self, owner: str) -> bool:
        """Return whether a call into `owner` may run now."""

    def succeeded(self, owner: str) -> None:
        """Record a successful call into `owner`."""

    def failed(self, owner: str, error: BaseException) -> bool:
        """Record a failure of `owner`; True when it is a domain error."""


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
        self._owners: dict[str, str] = {}
        self._gate: OwnerGate | None = None

    def set_gate(self, gate: OwnerGate | None) -> None:
        """Install the gate that decides whether an owned target may run."""
        self._gate = gate

    def expose(self, alias: str, abstract: Any, methods: Iterable[str], owner: str = "") -> None:
        """Allow `methods` of the service bound as `abstract` to be called as `alias`.

        Everything not exposed is refused. Private or empty method names are
        refused here, and so is a method the target class does not define, so
        a typo fails at boot instead of on the first call.

        `owner` names the extension the target belongs to. While the owner
        cannot serve (deactivated, failed, circuit open) calls are refused with
        `INTERNAL_TARGET_UNAVAILABLE` and the target never runs.

        Raises:
            InternalProxyError: The alias is already exposed (one module cannot
                take over another's), or a method name is private, empty or
                undefined.
        """
        if alias in self._exposed:
            raise InternalProxyError("INTERNAL_ALIAS_ALREADY_EXPOSED", alias)
        allowed = frozenset(methods)
        for method in allowed:
            if not method or method.startswith("_"):
                raise InternalProxyError("INTERNAL_EXPOSE_PRIVATE_OR_EMPTY_METHOD", alias, method)
            target_class = abstract if inspect.isclass(abstract) else None
            if target_class is not None and not callable(getattr(target_class, method, None)):
                raise InternalProxyError("INTERNAL_EXPOSE_UNKNOWN_METHOD", alias, method)
        self._exposed[alias] = (abstract, allowed)
        if owner:
            self._owners[alias] = owner

    def unexpose(self, alias: str) -> bool:
        """Withdraw an alias, e.g. when its extension is deactivated.

        Returns:
            Whether the alias was exposed.
        """
        self._owners.pop(alias, None)
        return self._exposed.pop(alias, None) is not None

    def owner(self, alias: str) -> str:
        """Return the extension owning `alias`, or an empty string."""
        return self._owners.get(alias, "")

    def exposed(self) -> Mapping[str, tuple[Any, frozenset[str]]]:
        """Return a read-only view of every exposed alias and its methods."""
        return MappingProxyType(dict(self._exposed))

    def call(self, alias: str, method: str, /, *args: Any, **kwargs: Any) -> Any:
        """Call a synchronous exposed method on the caller's thread.

        Raises:
            InternalProxyError: The target is not exposed, or it is asynchronous
                - a coroutine function or a method returning an awaitable (use
                `dispatch`).
        """
        handler = self._handler(alias, method)
        if inspect.iscoroutinefunction(handler):
            raise InternalProxyError("INTERNAL_ASYNC_HANDLER_FROM_SYNC_CALL", alias, method)
        owner = self._admit(alias, method)
        try:
            result = handler(*args, **kwargs)
        except Exception as error:
            self._report(owner, error)
            raise
        if inspect.isawaitable(result):
            _discard(result)
            raise InternalProxyError("INTERNAL_ASYNC_HANDLER_FROM_SYNC_CALL", alias, method)
        self._succeeded(owner)
        return result

    async def dispatch(self, alias: str, method: str, /, *args: Any, **kwargs: Any) -> Any:
        """Call an exposed method from async code, awaiting whatever it returns.

        A synchronous target runs inline on the caller's thread - never on a
        worker thread, where it would borrow a second pooled connection outside
        the caller's transaction and never return it. The engine runs async
        actions on the request's own worker thread, so this does not block the
        server's event loop.

        Raises:
            InternalProxyError: The target is not exposed.
        """
        handler = self._handler(alias, method)
        owner = self._admit(alias, method)
        try:
            result = handler(*args, **kwargs)
            if inspect.isawaitable(result):
                result = await result
        except Exception as error:
            self._report(owner, error)
            raise
        self._succeeded(owner)
        return result

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

    def _admit(self, alias: str, method: str) -> str:
        """Return the owner of `alias` when its call may run.

        Raises:
            InternalProxyError: `INTERNAL_TARGET_UNAVAILABLE` - the owner cannot
                serve, so the target is not run at all.
        """
        owner = self._owners.get(alias, "")
        if owner and self._gate is not None and not self._gate.allow(owner):
            raise InternalProxyError("INTERNAL_TARGET_UNAVAILABLE", alias, method)
        return owner

    def _report(self, owner: str, error: BaseException) -> None:
        """Count an exception of an owned target toward its owner's health."""
        if owner and self._gate is not None:
            self._gate.failed(owner, error)

    def _succeeded(self, owner: str) -> None:
        """Record a successful call of an owned target."""
        if owner and self._gate is not None:
            self._gate.succeeded(owner)

    def _handler(self, alias: str, method: str) -> Any:
        """Return the bound method `alias.method`, refusing anything not exposed."""
        exposed = self._exposed.get(alias)
        if exposed is None:
            raise InternalProxyError("INTERNAL_TARGET_NOT_EXPOSED", alias, method)
        abstract, methods = exposed
        if method not in methods:
            raise InternalProxyError("INTERNAL_METHOD_NOT_EXPOSED", alias, method)
        return getattr(self._container.make(abstract), method)


def _discard(awaitable: Any) -> None:
    """Close a coroutine that will never be awaited, so it leaves no warning."""
    close = getattr(awaitable, "close", None)
    if callable(close):
        close()


__all__ = ["InternalProxy", "InternalProxyError", "OwnerGate"]
