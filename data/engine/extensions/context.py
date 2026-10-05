"""What an extension receives at load time, and the error boundary around it.

An extension never registers on the global objects directly. It goes through
its `ExtensionContext`, which:

- wraps every listener and filter in the extension's error boundary, so a
  failure is logged with the slug, counted by the circuit breaker and contained;
- records every contribution, so deactivation undoes all of them in the
  running process.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from typing import Any, Protocol

from engine.events.dispatcher import DEFAULT_PRIORITY
from engine.extensions.manifest import Manifest

_LOG = logging.getLogger("craft.extensions")

#: Returned by a skipped listener: the extension did not run.
SKIPPED = None


class Guard(Protocol):
    """The circuit-breaker side of the manager, as the context sees it."""

    def allow(self, slug: str) -> bool:
        """Return whether a call into the extension may run now."""

    def succeeded(self, slug: str) -> None:
        """Record a successful call."""

    def failed(self, slug: str, error: BaseException) -> bool:
        """Record a failure; return True when the caller must re-raise it."""


class ExtensionContext:
    """The handle an extension's `provider.register(context)` works through.

    Args:
        app: The application container (bind services, read configuration).
        manifest: The extension's manifest.
        guard: The error boundary deciding whether calls run.
    """

    def __init__(self, app: Any, manifest: Manifest, guard: Guard) -> None:
        self.app = app
        self.manifest = manifest
        self.slug = manifest.slug
        self._guard = guard
        self._undo: list[Callable[[], Any]] = []

    def listen(self, event: Any, listener: Any, priority: int = DEFAULT_PRIORITY) -> None:
        """Register a listener that runs only while the extension can serve."""
        wrapped = self.guarded(listener)
        events = self.app.make("events")
        events.listen(event, wrapped, priority=priority)
        self.on_unload(lambda: events.remove_listener(event, wrapped))

    def filter(self, name: str, callback: Callable[..., Any], priority: int = DEFAULT_PRIORITY) -> None:
        """Register a filter; on failure the value passes through unchanged."""
        events = self.app.make("events")

        def wrapped(value: Any, *args: Any, **kwargs: Any) -> Any:
            return self.call(callback, value, *args, fallback=value, **kwargs)

        events.add_filter(name, wrapped, priority=priority)
        self.on_unload(lambda: events.remove_filter(name, wrapped))

    def expose(self, alias: str, abstract: Any, methods: Iterable[str]) -> None:
        """Expose service methods on the internal proxy, owned by this extension."""
        proxy = self.app.make("proxy")
        proxy.expose(alias, abstract, methods, owner=self.slug)
        self.on_unload(lambda: proxy.unexpose(alias))

    def on_unload(self, undo: Callable[[], Any]) -> None:
        """Register a callable that reverts a contribution on deactivation."""
        self._undo.append(undo)

    def guarded(self, listener: Any) -> Callable[[Any], Any]:
        """Wrap a listener (function or class with `handle`) in the error boundary."""

        def wrapped(event: Any) -> Any:
            return self.call(self._handler(listener), event, fallback=SKIPPED)

        wrapped.__qualname__ = f"{self.slug}:{getattr(listener, '__qualname__', repr(listener))}"
        return wrapped

    def call(self, function: Callable[..., Any], *args: Any, fallback: Any = SKIPPED, **kwargs: Any) -> Any:
        """Run `function` inside the extension's error boundary.

        Returns:
            What `function` returned, or `fallback` when the extension may not
            run or failed unexpectedly.

        Raises:
            Exception: A typed domain error (status below 500) is the extension
                working, so it propagates to the caller unchanged.
        """
        if not self._guard.allow(self.slug):
            return fallback
        try:
            result = function(*args, **kwargs)
        except Exception as error:  # noqa: BLE001 - the extension's error boundary
            if self._guard.failed(self.slug, error):
                raise
            return fallback
        self._guard.succeeded(self.slug)
        return result

    def unload(self) -> None:
        """Revert every contribution, newest first; one failing undo never stops the rest."""
        while self._undo:
            undo = self._undo.pop()
            try:
                undo()
            except Exception:  # noqa: BLE001 - unloading must finish
                _LOG.warning("extension_unload_step_failed slug=%s", self.slug, exc_info=True)

    def _handler(self, listener: Any) -> Callable[[Any], Any]:
        """Return the callable behind a listener, building a class through the container."""
        if isinstance(listener, type):
            instance = self.app.make(listener)
            return getattr(instance, "handle", instance)
        return listener


__all__ = ["ExtensionContext", "Guard", "SKIPPED"]
