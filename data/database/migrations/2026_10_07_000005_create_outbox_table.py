"""Migration: the transactional outbox table.

A state change and the message it must emit cannot be two writes to two
systems: the crash between them either loses the message or emits one for work
that rolled back. The outbox puts the message in the same table space as the
change, in the same transaction, and a relay publishes it afterwards. Delivery
is therefore at-least-once, and a message for a rolled-back change is never
sent.

Forward-only, like every framework table.

Category: Framework schema (events).
References:
  - `engine/events/outbox.py` (the relay).
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.migrations import Schema


def up():
    Schema.create_table("outbox_messages", lambda t: (
        t.id(),
        t.string("topic"),
        t.jsonb("payload").nullable(),
        t.datetime("available_at").nullable(),
        t.integer("attempts").default(0),
        t.text("last_error").nullable(),
        t.datetime("published_at").nullable(),
        # The tenant the message belongs to, so the relay delivers it under the
        # same isolation the write had.
        t.uuid("tenant_id").nullable(),
        t.timestamps(),
        t.index_on(["published_at", "available_at"], name="idx_outbox_due"),
    ))


def down():
    raise RuntimeError("This migration is forward-only.")
