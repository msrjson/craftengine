---
name: craft-engine-pitfalls
description: The recurring traps in a Craft Engine project and how to avoid them. Use when writing engine-facing code, generators, migrations or templates, or when a change behaves unlike a framework you may already know.
---

# Craft Engine pitfalls

## Overview

Craft Engine looks like frameworks you already know, which is exactly the trap: a
helper you recognise may not exist here, may take different arguments, or may not
be wired the way you expect. **Zero guessing** — ground every decision in this
project's source (`engine/`) and its tests, never in memory of another framework.

## Pitfalls

- **Assuming framework parity.** Read `engine/` before using a helper you know
  from elsewhere. The engine ships what it names, nothing more; a missing helper
  is a missing helper, not a bug to work around by importing your own.
- **Destructive database commands.** Never run reset/fresh/wipe/drop, in any
  environment; schema evolves forward-only with `python dev.py migrate`. The
  engine refuses the rest — do not try to bypass it.
- **Relations are methods, not attributes.** `post.author` is a callable;
  resolve it with `post.author().first()` (or `.get()`) or eager-load it with
  `with_("author")`. Reading `post.author.name` raises a diagnostic, not data.
- **Mass assignment fails closed.** An empty `fillable` means nothing is
  assignable through `create()`/`update_attributes()`; assign one by one or use
  `force_create()` for trusted internal writes.
- **The engine never imports the application.** `tools/check_engine_boundary.py`
  fails the build when a file under `engine/` imports `app`, `routes`,
  `database`, `config` or `bootstrap`. Business rules live in the application.
- **Hardcoded copy fails the language gate.** Every user-facing string is a
  translation key; identifiers, comments and commits are English.
- **The agent directory is `.agents/`.** `.claude` is a symlink to it; write
  `.agents/...` in docs, rules and generated text.

## Before you finish

Run the tests in the container, `ruff check engine`, the engine-boundary gate and
the language gate. Report any gate that could not run.
