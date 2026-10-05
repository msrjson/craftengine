"""Migration: the `extensions` table and the extension model's messages.

One row per extension that left the `discovered` state: its kind, version,
lifecycle state and path (ADR 0004). The messages are the `code` +
`message_key` contract of `engine.extensions.errors`, written in `en`, `pt-BR`
and `es`, leaving alone any row the project already has.

Forward-only: there is no `down()`; extension state and translations are
never deleted.

Category: Framework schema (extensions).
References:
  - Guide: `documentation/extensions.md`
"""

from craft.extensions.messages import seed_messages
from craft.facades import DB
from craft.migrations import Schema


def up():
    Schema.create_table("extensions", lambda t: (
        t.id(),
        t.string("slug").unique(),
        t.string("kind"),
        t.string("version"),
        t.string("state"),
        t.string("path").nullable(),
        t.timestamps(),
    ))
    seed_messages(DB)
