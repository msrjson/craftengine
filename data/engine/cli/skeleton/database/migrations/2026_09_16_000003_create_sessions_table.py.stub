"""Migration: server-side session storage for `DatabaseSessionStore`.

The cookie/file stores this framework already ships cannot be revoked from
outside the browser that holds them, and neither tracks idle time separately
from the signed cookie's own absolute expiry - a stolen but still-signed
cookie stays valid until it naturally expires, and "log out everywhere" has
nowhere to act on. A database-backed row gives both: `revoke()` marks a row
un-usable immediately regardless of what the cookie still says, and
`last_activity_at` lets a store enforce idle timeout independent of the
cookie's own lifetime.

Category: Framework schema (auth security).
References:
  - Guide: `documentation/sessions.md#database-driver`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.facades import Schema


def up():
    Schema.create_table("sessions", lambda t: (
        t.string("id", 255).primary(),
        t.text("payload"),
        t.timestamp("last_activity_at"),
        t.timestamp("revoked_at").nullable(),
        t.timestamps(),
    ))


def down():
    Schema.drop_table("sessions")
