"""Migration: the `seed_ledger` - one row per seed that may run exactly once.

A seeder that is idempotent by `first_or_create` is only idempotent while the
row it looks for still exists. An edited catalog row (a price the owner
re-priced) no longer matches the factory value, so the next `release:sync`
inserts a second copy - and a commercial catalog is money, seeded when a node is
born and never again.

This is the record that lets a seeder declare itself once-only and be honoured
across releases.

Forward-only: the ledger is the proof of what already ran on this node.

Category: Framework schema (seeding).
References:
  - `engine/seeding/ledger.py` (`SeedLedger`).
  - Guide: `documentation/migrations.md#seeders`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.migrations import Schema


def up():
    Schema.create_table("seed_ledger", lambda t: (
        t.id(),
        t.uuid_key(),
        t.string("key", 160).unique(),
        t.string("version", 40).nullable(),
        t.text("note").nullable(),
        t.datetime("seeded_at").nullable(),
        t.timestamps(),
    ))


def down():
    raise RuntimeError("This migration is forward-only.")
