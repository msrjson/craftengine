"""Migration: a unique index `auth_cooldowns` needs for an atomic upsert.

`HoneypotService.record_attempt()` used to read the current failed-attempt
count, add one, then write it back in a separate statement — a classic
TOCTOU race: two concurrent failed logins (exactly what an automated
brute-force tool produces) could both read the same count and both write
`count + 1`, silently losing an increment and letting the attacker try more
times than the limit allows. Fixing it means an atomic
`INSERT ... ON CONFLICT ... DO UPDATE`, which needs a unique constraint on
the columns being conflicted on.

Category: Framework schema (auth security).
References:
  - Plan: `.claude/plans/softpax-upstream-roadmap.md` (Slice 0 item 0.11,
    Slice 2 "sliding-window login limiter with atomic upsert")
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.facades import DB, Schema


def up():
    # Existing duplicates require manual, non-destructive reconciliation.
    # Never erase security history to make an index creation succeed.
    duplicate = DB.statement("""
        SELECT identifier_type, identifier_value
        FROM auth_cooldowns
        GROUP BY identifier_type, identifier_value
        HAVING COUNT(*) > 1
        LIMIT 1
    """).fetchone()
    if duplicate is not None:
        raise RuntimeError("Duplicate auth cooldown identifiers require non-destructive reconciliation.")
    Schema.table("auth_cooldowns", lambda t: (
        t.unique_index(["identifier_type", "identifier_value"], name="uq_auth_cooldowns_identifier"),
    ))


def down():
    raise RuntimeError("This migration is forward-only.")
