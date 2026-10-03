---
id: "20261003-223121"
title: Decide the uncommitted changes that undo v4.2.0-r00020
type: decision
priority: 1
autonomous: false
blocked_by: owner-decision
max_attempts: 2
attempts: 0
created_at: 2026-10-03T22:31:21Z
updated_at: 2026-10-03T22:51:47Z
source: git status, 2026-10-03
touches: []
---

## Problem

HEAD is `ad63fb5 chore(release): v4.2.0-r00020`, but the working tree holds uncommitted changes that remove most of it: the translation bundle cache, the performance benchmark and its hardening tests, and the version bump. Until this is settled, any task that touches these files works on an ambiguous base.

## Evidence

- `git diff --stat`: 13 files, +58 / -752, including `data/engine/support/translation.py` (HEAD has `_locale_bundles` at line 80), `data/engine/__init__.py`, `data/pyproject.toml`, `data/CHANGELOG.md`, `data/tests/test_architectural_performance_hardening.py` and `data/tests/benchmark_performance.py`.
- The old backlog item "translation lookups query per key" (L6) is solved in HEAD and unsolved in the working tree.

## Done when

- [x] The owner chose: keep v4.2.0 (discard the working-tree changes) or revert it (commit the revert, with a CHANGELOG entry and a new release counter per NR-01).
- [x] The decision is recorded in this file's History.

## Verify

```bash
git status --short
git log --oneline -3
```

## Notes

Discarding or committing someone else's working tree is destructive; an agent never does either on its own.

## History

- 2026-10-03T22:31:21Z created by claude (source: git status, 2026-10-03; migrated from the single-file backlog)
- 2026-10-03T22:51:47Z owner decision: keep v4.2.0 and fix its defects; revert diff archived in .claude/reports/20261003-v4-2-0-revert.patch, working tree restored to HEAD; resolved by claude (resolutions/p1-20261003-223121-uncommitted-revert-of-v4-2-0.resolution.md)
