"""
EventDispatcher — Registers listeners (by class or string name) and dispatches
events to them synchronously.
Category: Core Framework (Events).
Relations:
  - Bound as `events`, exposed via the `Event` facade; typically wired in
    `app/Providers/EventServiceProvider.py`.
References:
  - Guide: `documentation/queues_events.md#events--listeners`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Union

_LOG = logging.getLogger("craft.events")

Listener = Union[type, Callable[[Any], Any]]


class EventDispatcher:
    """Registers listeners and dispatches events to them."""

    def __init__(self, app: Any = None):
        self.app = app
        self._listeners: Dict[Any, List[Listener]] = {}
        self._wildcard: List[Listener] = []

    # -- registration ----------------------------------------------------------

    def listen(self, event: Any, listeners: Union[Listener, List[Listener]]) -> None:
        """Register one listener, or several.

        Both forms work — requiring a list meant the obvious
        `Event.listen(PostPublished, NotifySubscribers)` raised
        "'type' object is not iterable".
        """
        if not isinstance(listeners, (list, tuple)):
            listeners = [listeners]

        if event == "*":
            self._wildcard.extend(listeners)
            return

        self._listeners.setdefault(event, []).extend(listeners)

    def subscribe(self, subscriber: Any) -> None:
        """Let a class register its own listeners via `subscribe(dispatcher)`."""
        instance = subscriber() if isinstance(subscriber, type) else subscriber
        instance.subscribe(self)

    def forget(self, event: Any) -> None:
        self._listeners.pop(event, None)

    def flush(self) -> None:
        self._listeners.clear()
        self._wildcard.clear()

    def has_listeners(self, event: Any) -> bool:
        return bool(self._wildcard) or any(
            self._matches(registered, event) for registered in self._listeners
        )

    # -- dispatching -----------------------------------------------------------

    @staticmethod
    def _matches(registered: Any, event: Any) -> bool:
        """A listener on a base class should also hear its subclasses.

        A listener registered under a string name matches when the dispatched
        event is that string, or exposes it via a `name` attribute.
        """
        if isinstance(registered, str):
            return registered == event or registered == getattr(event, "name", None)
        event_class = event if isinstance(event, type) else type(event)
        if isinstance(registered, type):
            return issubclass(event_class, registered)
        return registered == event_class

    def listeners_for(self, event: Any) -> List[Listener]:
        found: List[Listener] = []
        for registered, listeners in self._listeners.items():
            if self._matches(registered, event):
                found.extend(listeners)
        found.extend(self._wildcard)
        return found

    def _resolve(self, listener: Listener) -> Any:
        """Build a listener class, using the container so it can be autowired."""
        if not isinstance(listener, type):
            return listener
        if self.app is not None:
            try:
                return self.app.make(listener)
            except Exception:
                pass
        return listener()

    def dispatch(self, event: Any, halt: bool = False) -> List[Any]:
        """Send an event to its listeners and return what they returned.

        With `halt=True`, the first non-None response stops the chain — useful
        for "does anything veto this?" checks.
        """
        responses: List[Any] = []

        for listener in self.listeners_for(event):
            instance = self._resolve(listener)

            # A listener object exposes `handle`; a plain function is called
            # directly. `handle` wins so a callable class still works.
            if hasattr(instance, "handle"):
                handler = instance.handle
            elif callable(instance):
                handler = instance
            else:
                continue

            response = handler(event)
            if halt and response is not None:
                return [response]
            responses.append(response)

        return responses

    def notify(self, event: Any) -> None:
        """Deliver `event` to every listener; a failing listener never stops the rest.

        For cleanup events such as `RequestTerminated`, where skipping a later
        listener would leak a resource. Each failure is logged with its traceback.
        """
        for listener in self.listeners_for(event):
            try:
                instance = self._resolve(listener)
                handler = getattr(instance, "handle", instance)
                handler(event)
            except Exception:
                _LOG.exception("event_listener_failed event=%s listener=%r", type(event).__name__, listener)

    # Alias.
    def fire(self, event: Any) -> List[Any]:
        return self.dispatch(event)

    def until(self, event: Any) -> Any:
        """Dispatch until a listener returns something."""
        responses = self.dispatch(event, halt=True)
        return responses[0] if responses else None


__all__ = ["EventDispatcher"]
