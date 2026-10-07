"""Migration: chain the sign-in audit log so a removed row is detectable.

`auth_audit_logs` recorded each attempt but nothing tied one row to the next, so
a row could be edited, reordered or deleted and no reader could tell. Each row
now carries `previous_hash` (the `chain_hash` of the row before it, or a genesis
value for the first) and `chain_hash` (a digest of the row's own fields plus
`previous_hash`). `HoneypotService` fills both on every insert, so recomputing
the chain from the first row proves no row was changed or removed.

Only two nullable columns are added; no existing row is touched, and a row
written before this migration keeps `NULL` in both (the chain starts at the
first row written after it).

Category: Framework schema (security).
References:
  - `engine/security/honeypot.py` (`_append_audit_log`).
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.facades import Schema


def up() -> None:
    Schema.table("auth_audit_logs", lambda t: (
        t.string("previous_hash", max_length=64).nullable(),
        t.string("chain_hash", max_length=64).nullable(),
    ))


def down() -> None:
    raise RuntimeError("This migration is forward-only.")
