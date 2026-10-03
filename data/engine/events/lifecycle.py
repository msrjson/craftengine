"""
Framework lifecycle events — emitted by the framework itself, not by app code.
Category: Core Framework (Events).
Relations:
  - Dispatched through `engine/events/dispatcher.py` via `fire()` below.
  - Emitted from `engine/orm/model.py` (writes) and `engine/auth/manager.py`
    (authentication).
  - Reach plugin hooks through the bridge in `engine/plugins/manager.py`, which
    listens on the wildcard and re-dispatches by `name`.
References:
  - Guide: `documentation/queues_events.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import logging
from typing import Any

from engine.events.event import Event


class ModelEvent(Event):
    """Base for the three model write events — lets a listener catch all
    writes with a single `Event.listen(ModelEvent, ...)`."""

    def __init__(self, model: Any):
        self.model = model
        self.table = model.get_table_name()


class ModelCreated(ModelEvent):
    name = "model.created"


class ModelUpdated(ModelEvent):
    name = "model.updated"


class ModelDeleted(ModelEvent):
    name = "model.deleted"


class AuthEvent(Event):
    """Base for authentication events that carry a user."""

    def __init__(self, user: Any):
        self.user = user


class UserAuthenticated(AuthEvent):
    name = "auth.login"


class UserLoggedOut(AuthEvent):
    name = "auth.logout"


class UserLoginFailed(AuthEvent):
    """A failed credential check.

    Carries the identifier only — never the submitted password, which would
    otherwise reach every listener, every plugin, and any log they write.

    `user` is None rather than absent: a listener registered on `AuthEvent` to
    catch every authentication event would otherwise hit an `AttributeError`
    here, since nothing was authenticated. None is also the honest answer.
    """

    name = "auth.failed"

    def __init__(self, email: Any):
        super().__init__(None)
        self.email = email


class RequestTerminated(Event):
    """An HTTP request finished, emitted on the worker thread that served it.

    The kernel names no subsystem: each one that holds per-request resources
    (the database's pooled connection first) listens for this and releases
    them itself. Delivered with `EventDispatcher.notify`, so one failing
    listener never stops the others.

    Args:
        request: The request that finished.
    """

    name = "request.terminated"

    def __init__(self, request: Any):
        self.request = request


def fire(event: Event) -> None:
    """Emit a framework lifecycle event without ever breaking the caller.

    Two deliberate guarantees, both of which the plain `Event` facade does not
    make and should not:

    1. **No container, no event.** Models and the auth manager are used in unit
       tests with no booted application. Emitting must degrade to a no-op there
       rather than forcing every such test to build a container.
    2. **A broken listener cannot fail a write.** These events fire from inside
       INSERT/UPDATE/DELETE paths, so an exception raised by a listener would
       roll a successful database write into a request error. Failures are
       logged — the same contract `PluginManager.trigger_hook` already applies
       to plugin callbacks — never silently swallowed.

    App-level events dispatched through the `Event` facade keep the strict
    behaviour: there, a listener raising is the app's own bug and should surface.
    """
    try:
        from engine.container.application import Container

        container = Container.getInstance()
        dispatcher = container.make("events") if container is not None else None
    except Exception:
        return

    if dispatcher is None:
        return

    try:
        dispatcher.dispatch(event)
    except Exception:
        logging.getLogger("craft").warning(
            "Listener raised while handling lifecycle event %s",
            getattr(event, "name", type(event).__name__),
            exc_info=True,
        )


__all__ = [
    "ModelEvent",
    "ModelCreated",
    "ModelUpdated",
    "ModelDeleted",
    "AuthEvent",
    "UserAuthenticated",
    "UserLoggedOut",
    "UserLoginFailed",
    "fire",
]
