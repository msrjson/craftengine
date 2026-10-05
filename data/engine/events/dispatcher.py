"""
EventDispatcher - Registers listeners (by class or string name) and dispatches
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
import itertools
from typing import Any, Callable, Dict, List, Tuple, Union

_LOG = logging.getLogger("craft.events")

Listener = Union[type, Callable[[Any], Any]]

#: Priority of a listener or filter registered without one. Lower runs first;
#: equal priorities run in registration order.
DEFAULT_PRIORITY = 10

#: (priority, registration sequence, callable) - sorts into execution order.
_Entry = Tuple[int, int, Any]


class EventDispatcher:
    """Registers listeners and dispatches events to them."""

    def __init__(self, app: Any = None):
        self.app = app
        self._sequence = itertools.count()
        self._listeners: Dict[Any, List[_Entry]] = {}
        self._filters: Dict[str, List[_Entry]] = {}
        self._wildcard: List[Listener] = []
        #: Resource-release listeners: run after every other listener, wildcard
        #: included, and kept by `forget`/`flush`, so nothing can reopen what
        #: they release or remove them by accident.
        self._last: Dict[Any, List[Listener]] = {}

    # -- registration ----------------------------------------------------------

    def listen(
        self, event: Any, listeners: Union[Listener, List[Listener]], priority: int = DEFAULT_PRIORITY
    ) -> None:
        """Register one listener, or several.

        Both forms work - requiring a list meant the obvious
        `Event.listen(PostPublished, NotifySubscribers)` raised
        "'type' object is not iterable".

        Args:
            event: Event class, event name, or `"*"` for every event.
            listeners: One listener or a list of them.
            priority: Lower runs first; equal priorities keep registration
                order. Ignored for `"*"`, which always runs after the rest.
        """
        if not isinstance(listeners, (list, tuple)):
            listeners = [listeners]

        if event == "*":
            self._wildcard.extend(listeners)
            return

        entries = self._listeners.setdefault(event, [])
        entries.extend((priority, next(self._sequence), listener) for listener in listeners)

    def remove_listener(self, event: Any, listener: Listener) -> bool:
        """Unregister one listener of `event` (or of `"*"`).

        Returns:
            Whether the listener was registered.
        """
        if event == "*":
            kept = [registered for registered in self._wildcard if registered is not listener]
            removed = len(kept) != len(self._wildcard)
            self._wildcard[:] = kept
            return removed
        entries = self._listeners.get(event, [])
        kept = [entry for entry in entries if entry[2] is not listener]
        if len(kept) == len(entries):
            return False
        self._listeners[event] = kept
        return True

    # -- filters ---------------------------------------------------------------

    def add_filter(self, name: str, callback: Callable[..., Any], priority: int = DEFAULT_PRIORITY) -> None:
        """Register a callback that receives a value and returns it transformed.

        Args:
            name: The filter point, e.g. `"crm.contact.display_name"`.
            callback: Called as `callback(value, *args, **kwargs)`; returns the
                new value.
            priority: Lower runs first; equal priorities keep registration order.
        """
        self._filters.setdefault(name, []).append((priority, next(self._sequence), callback))

    def remove_filter(self, name: str, callback: Callable[..., Any]) -> bool:
        """Unregister one filter callback; return whether it was registered."""
        entries = self._filters.get(name, [])
        kept = [entry for entry in entries if entry[2] is not callback]
        self._filters[name] = kept
        return len(kept) != len(entries)

    def apply_filters(self, name: str, value: Any, *args: Any, **kwargs: Any) -> Any:
        """Pass `value` through every filter of `name`, in priority order.

        Returns:
            The value the last filter returned, or `value` with no filters.
        """
        for _priority, _sequence, callback in sorted(self._filters.get(name, [])[:], key=_order):
            value = callback(value, *args, **kwargs)
        return value

    def has_filters(self, name: str) -> bool:
        """Return whether anything filters `name`."""
        return bool(self._filters.get(name))

    def listen_last(self, event: Any, listener: Listener) -> None:
        """Register a listener that runs after every other listener of `event`.

        For releasing per-request resources such as a pooled connection: a
        listener running after the release could otherwise check out a new one.
        `forget` and `flush` keep these listeners.
        """
        self._last.setdefault(event, []).append(listener)

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
            entries and self._matches(registered, event) for registered, entries in self._listeners.items()
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
        matching: List[_Entry] = []
        for registered, entries in list(self._listeners.items()):
            if self._matches(registered, event):
                matching.extend(entries)
        found: List[Listener] = [entry[2] for entry in sorted(matching, key=_order)]
        found.extend(self._wildcard)
        for registered, listeners in self._last.items():
            if self._matches(registered, event):
                found.extend(listeners)
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

        With `halt=True`, the first non-None response stops the chain - useful
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


def _order(entry: _Entry) -> Tuple[int, int]:
    """Sort key of a listener or filter entry: priority, then registration."""
    return entry[0], entry[1]


__all__ = ["DEFAULT_PRIORITY", "EventDispatcher"]
