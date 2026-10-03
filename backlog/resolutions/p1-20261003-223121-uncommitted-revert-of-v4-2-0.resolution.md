---
task: p1-20261003-223121-uncommitted-revert-of-v4-2-0
outcome: resolved
agent: claude
started_at: 2026-10-03T23:10:00Z
finished_at: 2026-10-03T22:51:47Z
---

## Decision

The owner chose to keep v4.2.0-r00020 and fix its defects instead of committing the revert. The uncommitted revert (13 files, +58 / -752) was archived as `.claude/reports/20261003-v4-2-0-revert.patch` before the working tree was restored to HEAD, so nothing is lost.

Defects found in v4.2.0 during the review, fixed in follow-up commits:

- F1 `DatabaseSessionStore.save` skips the write on read-only requests, so `last_activity_at` stops moving and active readers hit `idle_timeout`.
- F2 Translation bundles are process-global, keyed by locale only, never invalidated, with a permanent negative cache.
- F3 The kernel's request `finally` imports `engine.auth.access` and calls `auth.reset()` under `except Exception: pass` - the kernel coupled to a subsystem.
- F4 The request query log calls `list.count()` per statement (quadratic per request).

## Verification

```bash
git status --short   # the 13 engine/test/doc files no longer listed as modified
git log --oneline -1 # ad63fb5 is still the base of the v4.2.0 code
```
