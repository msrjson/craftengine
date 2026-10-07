"""The transactional outbox: emit a message with the change that caused it.

A service that changes state and then publishes an event performs two writes to
two systems, and the failure between them is silent: the process dies after the
commit and before the publish, and the event is lost, or it publishes and the
transaction rolls back, and the event describes work that never happened. The
outbox narrows both cases to one write — the message goes into
`outbox_messages` on the caller's own connection, inside the caller's
transaction — and a relay publishes what committed.

Delivery is at-least-once: a relay that dies after publishing and before
marking the row published sends it again, so a handler must be idempotent.

Category: Core Framework (Events).
Relations:
  - Reads and writes the `outbox_messages` table
    (`database/migrations/2026_10_07_000005_create_outbox_table.py`).
References:
  - Guide: `documentation/queues_events.md#transactional-outbox`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

_logger = logging.getLogger("craft.outbox")

#: How long to wait before retrying a message, by attempt count, capped.
MAX_BACKOFF_SECONDS = 3600


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _iso(moment: datetime) -> str:
    return moment.isoformat()


class OutboxMessage:
    """One queued message as a handler receives it."""

    __slots__ = ("id", "topic", "payload", "attempts", "tenant_id")

    def __init__(self, id: Any, topic: str, payload: Any, attempts: int = 0, tenant_id: Optional[str] = None):
        self.id = id
        self.topic = topic
        self.payload = payload
        self.attempts = attempts
        self.tenant_id = tenant_id

    def __repr__(self) -> str:
        return f"<OutboxMessage id={self.id} topic={self.topic!r} attempts={self.attempts}>"


class Outbox:
    """Writes messages transactionally and a relay that publishes them."""

    #: topic -> handlers, process-wide. A project registers at boot.
    _handlers: Dict[str, List[Callable[[OutboxMessage], Any]]] = {}

    def __init__(self, app: Optional[Any] = None):
        self.app = app

    @property
    def db(self) -> Any:
        if self.app is not None:
            return self.app.make("db")
        from engine.container.application import Container

        return Container.getInstance().make("db")

    def _driver(self) -> str:
        try:
            return str(getattr(self.db, "driver", "sqlite"))
        except Exception:
            return "sqlite"

    # -- registry --------------------------------------------------------------

    @classmethod
    def on(cls, topic: str, handler: Callable[[OutboxMessage], Any]) -> None:
        """Register `handler` for `topic`. More than one handler may listen."""
        cls._handlers.setdefault(topic, []).append(handler)

    @classmethod
    def clear_handlers(cls) -> None:
        """Forget every handler; used by tests."""
        cls._handlers.clear()

    # -- writing ---------------------------------------------------------------

    def publish(self, topic: str, payload: Optional[Any] = None) -> Any:
        """Record a message to emit once the caller's transaction commits.

        Called on the caller's connection: a rollback discards the row with the
        rest of the transaction, which is the whole point.
        """
        from engine.orm.tenancy import current_tenant_id

        values: Dict[str, Any] = {
            "topic": topic,
            "payload": self._encode(payload),
            "available_at": _iso(_now()),
            "attempts": 0,
        }
        tenant = current_tenant_id()
        if tenant:
            values["tenant_id"] = tenant
        return self.db.table("outbox_messages").insert(values)

    def _encode(self, payload: Any) -> Any:
        payload = {} if payload is None else payload
        if self._driver() == "postgresql":
            from psycopg2.extras import Json

            return Json(payload)
        return json.dumps(payload, default=str)

    def _decode(self, stored: Any) -> Any:
        if isinstance(stored, (dict, list)):
            return stored
        if not stored:
            return {}
        try:
            return json.loads(stored)
        except (TypeError, ValueError):
            return stored

    # -- relaying --------------------------------------------------------------

    def due(self, limit: int = 100) -> List[Any]:
        """The unpublished messages whose retry time has arrived, oldest first."""
        return (
            self.db.table("outbox_messages")
            .where_null("published_at")
            .where("available_at", "<=", _iso(_now()))
            .order_by("id")
            .limit(limit)
            .get()
        )

    def relay(self, limit: int = 100) -> int:
        """Publish every due message; return how many were delivered.

        A handler that raises leaves its message unpublished and schedules a
        retry with exponential backoff, so one bad message never blocks the
        queue behind it.
        """
        delivered = 0
        for row in self.due(limit):
            if self._deliver(row):
                delivered += 1
        return delivered

    def _deliver(self, row: Any) -> bool:
        message = OutboxMessage(
            id=row["id"],
            topic=str(row["topic"]),
            payload=self._decode(row["payload"]),
            attempts=int(row["attempts"] or 0),
            tenant_id=row["tenant_id"] if "tenant_id" in row else None,
        )
        handlers = self._handlers.get(message.topic, [])
        if not handlers:
            # Nobody listens: mark it published rather than retry forever, and
            # leave the reason on the row for diagnosis.
            self._mark_published(message.id, note="no_handler")
            return False

        try:
            with self._tenant_scope(message.tenant_id):
                for handler in handlers:
                    handler(message)
        except Exception as exc:  # noqa: BLE001 - a handler may raise anything
            self._reschedule(message, exc)
            return False

        self._mark_published(message.id)
        return True

    def _tenant_scope(self, tenant_id: Optional[str]) -> Any:
        """Bind the message's tenant for the handler, when it has one."""
        if not tenant_id:
            return _NullScope()
        from engine.orm.tenancy import TenantManager

        return _TenantScope(TenantManager(self.app), tenant_id)

    def _mark_published(self, identifier: Any, note: Optional[str] = None) -> None:
        values: Dict[str, Any] = {"published_at": _iso(_now())}
        if note:
            values["last_error"] = note
        self.db.table("outbox_messages").where("id", identifier).update(values)

    def _reschedule(self, message: OutboxMessage, exc: Exception) -> None:
        attempts = message.attempts + 1
        delay = min(2 ** attempts, MAX_BACKOFF_SECONDS)
        self.db.table("outbox_messages").where("id", message.id).update({
            "attempts": attempts,
            "available_at": _iso(_now() + timedelta(seconds=delay)),
            "last_error": str(exc)[:1000],
        })
        _logger.warning(
            "outbox.delivery_failed topic=%s id=%s attempts=%s retry_in=%ss",
            message.topic, message.id, attempts, delay,
        )


class _TenantScope:
    def __init__(self, manager: Any, tenant_id: str):
        self.manager = manager
        self.tenant_id = tenant_id

    def __enter__(self) -> None:
        self.manager.bind(self.tenant_id, local=True)

    def __exit__(self, *exc: Any) -> None:
        self.manager.bind(None)


class _NullScope:
    def __enter__(self) -> None:
        return None

    def __exit__(self, *exc: Any) -> None:
        return None


__all__ = ["Outbox", "OutboxMessage"]
