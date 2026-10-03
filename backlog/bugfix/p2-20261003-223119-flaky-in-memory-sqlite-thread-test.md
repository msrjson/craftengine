---
id: "20261003-223119"
title: Fix the flaky in-memory SQLite shared-session concurrency test
type: bugfix
priority: 2
autonomous: true
blocked_by: none
max_attempts: 2
attempts: 0
created_at: 2026-10-03T22:31:19Z
updated_at: 2026-10-03T22:31:19Z
source: docs/backlog.md L8
touches:
  - data/tests/test_connection_concurrency.py
  - data/engine/orm/connection.py
---

## Problem

`TestInMemorySqliteSharesOneSession::test_threads_share_the_session_and_therefore_the_data` fails intermittently with `IndexError: tuple index out of range`. A flaky test either hides a real race in the shared in-memory session or trains everyone to ignore red runs.

## Evidence

- `data/tests/test_connection_concurrency.py` - the test above; failed once in about 20 runs on 2026-09-25 on a loaded machine, before and independent of that day's changes.

## Done when

- [ ] The root cause is identified: a race in `engine/orm/connection.py` or a defect in the test itself.
- [ ] The fix is at the root (no retry, no sleep, no skip).
- [ ] 50 consecutive runs of the test pass in the container.

## Verify

```bash
docker exec framework sh -lc 'cd /app && for i in $(seq 50); do python -m pytest tests/test_connection_concurrency.py -q -p no:randomly || exit 1; done'
```

## Notes

If the race is in the engine, the change needs a CHANGELOG entry under `[Unreleased]` and a regression test that fails without the fix.

## History

- 2026-10-03T22:31:19Z created by claude (source: docs/backlog.md L8; migrated from the single-file backlog)
