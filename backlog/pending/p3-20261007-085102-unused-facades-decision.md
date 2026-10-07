---
id: "20261007-085102"
title: Facades Broadcast, Log, Hash and Migrator have no internal callers
type: decision
priority: 3
autonomous: false
blocked_by: owner-decision
max_attempts: 2
attempts: 0
created_at: 2026-10-07T08:51:02Z
updated_at: 2026-10-07T08:51:02Z
source: dead-code audit 2026-10-07 (facade review)
touches:
  - data/engine/facades/__init__.py
  - data/documentation/
---

## Problem

Four facades in `craft.facades` are referenced by nothing inside the framework.
They resolve to real container bindings, so they are public API (NR-05) rather
than dead code — but a public surface nobody uses should be a deliberate choice,
not an accident.

## Evidence

- `data/engine/facades/__init__.py:49` `class Broadcast` — resolves to the
  `broadcast` singleton (`Broadcaster`, PostgreSQL LISTEN/NOTIFY). No internal
  caller; the facade is the documented way to publish.
- `:93` `class Log`, `:105` `class Hash`, `:123` `class Migrator` — no internal
  importer or `facades.Log`-style use.
- `Log` is taught in `.agents/skills/observability-and-instrumentation/SKILL.md:88`.

## Done when

- [ ] The owner records which of the four stay as documented public API and which
      are removed (removal follows the deprecation path; never a silent break).
- [ ] Each survivor is named in the documentation with a one-line purpose; each
      removal is in `CHANGELOG.md` under `Deprecated`/`Removed`.

## Verify

```bash
grep -rn 'facades import.*Broadcast\|facades\.Log\|facades\.Hash\|facades\.Migrator' data/ | head
grep -rn 'Broadcast\|Log\b' data/documentation/ | head
```

## Notes

`Broadcast` is real infrastructure (the `Broadcaster` in
`engine/queue/listener.py`), so its facade is likely to stay with a doc mention.
This task exists so the four are decided together instead of drifting.

## History

- 2026-10-07T08:51:02Z created by qwen@qwen-code (source: dead-code audit 2026-10-07)
