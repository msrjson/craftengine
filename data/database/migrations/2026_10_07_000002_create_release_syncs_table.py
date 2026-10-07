"""Migration: the `release_syncs` trail - one row per deploy that synced the node.

A migration creates a column, not the *rows* a system needs to serve: those are
born in a seeder, and a seeder that only runs when someone remembers leaves the
screen empty after a deploy on an environment nobody opens a terminal on.
`release:sync` runs the migrations and the seeders together on every boot; with
no record of it, "did this release reach this node?" was answered by reading a
container log that had already rolled away.

Forward-only: nothing here is ever deleted, and the previous row is the proof of
which release left the database in its current state.

Category: Framework schema (release).
References:
  - `engine/lifecycle/sync.py` (`ReleaseSync`).
  - Guide: `documentation/release.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.migrations import Schema


def up():
    Schema.create_table("release_syncs", lambda t: (
        t.id(),
        t.uuid_key(),
        t.string("version", 40),
        t.integer("migrations_run").default(0),
        t.integer("seeders_run").default(0),
        t.string("status", 20).default("ok"),
        t.json("findings").nullable(),
        t.integer("duration_ms").default(0),
        t.timestamps(),
    ))


def down():
    raise RuntimeError("This migration is forward-only.")
