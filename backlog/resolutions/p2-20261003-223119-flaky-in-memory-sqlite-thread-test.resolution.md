---
task: p2-20261003-223119-flaky-in-memory-sqlite-thread-test
outcome: resolved
agent: gemini
started_at: 2026-10-04T16:20:00Z
finished_at: 2026-10-04T16:34:00Z
---

## What changed

- `data/engine/orm/connection.py`:
  - Identified root cause: When multiple threads execute concurrent queries on a shared in-memory SQLite connection (`:memory:`), `sqlite3.Row` item lookup by column name string `item[key]` queries the cursor's description metadata. Concurrent execution interleaves statement resets and cursor descriptions, causing `IndexError: tuple index out of range`.
  - Added thread synchronization `lock = threading.RLock()` to `_Session` class and guarded `statement()` execution with `with session.lock:`.
  - In `_fetch()` for `sqlite3.Row`, replaced dictionary comprehension `{key: item[key] for key in item.keys()}` with `dict(zip(item.keys(), item))`, directly consuming tuple values by index position from the row sequence rather than triggering cursor metadata lookups on race-prone cursors.
- `data/CHANGELOG.md`: Added bugfix entry under `## [Unreleased]`.

## Verification

```bash
docker exec framework sh -lc 'cd /app && for i in $(seq 50); do python -m pytest tests/test_connection_concurrency.py -q -p no:randomly || exit 1; done'
# 50/50 runs passed (15 passed, 1 skipped per run)
docker exec framework sh -lc 'cd /app && ruff check engine'
# All checks passed!
cd data && python tools/check_engine_boundary.py
# ENGINE_BOUNDARY_NEW_FINDINGS 0
```
