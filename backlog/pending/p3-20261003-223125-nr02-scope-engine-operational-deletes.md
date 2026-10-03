---
id: "20261003-223125"
title: Decide whether NR-02 covers the engine's operational deletes
type: decision
priority: 3
autonomous: false
blocked_by: owner-decision
max_attempts: 2
attempts: 0
created_at: 2026-10-03T22:31:25Z
updated_at: 2026-10-03T22:31:25Z
source: docs/backlog.md Also open
touches: []
---

## Problem

NR-02 bans physical deletes on business entities. The engine itself physically deletes operational rows; whether those are in scope is a policy decision, not a fix.

## Evidence

- `data/engine/queue/manager.py:365` - a finished job is removed (`store().complete`).
- `data/engine/orm/relationships.py:370` - `detach()` deletes the pivot row.
- `data/engine/security/honeypot.py` - sign-in cooldowns are cleared.

## Done when

- [ ] The owner ruled in or out of scope, and the ruling is written into `.claude/rules/RELEASE_NON_REGRESSION_STANDARD.md` NR-02.
- [ ] If in scope, an implementation task per subsystem is created.

## Verify

```bash
grep -n "NR-02" -A8 .claude/rules/RELEASE_NON_REGRESSION_STANDARD.md
```

## Notes

None.

## History

- 2026-10-03T22:31:25Z created by claude (source: docs/backlog.md Also open; migrated from the single-file backlog)
