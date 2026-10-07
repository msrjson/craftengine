---
id: "20261007-080913"
title: The disposable-database allowlist is documented in three places and implemented in none
type: decision
priority: 2
autonomous: false
blocked_by: owner-decision
max_attempts: 2
attempts: 0
created_at: 2026-10-07T08:09:13Z
updated_at: 2026-10-07T08:09:13Z
source: framework audit 2026-10-07 (ORM and migrations exploration)
touches:
  - data/engine/migrations/safety.py
  - data/config/database.py
  - data/engine/cli/skeleton/config/database.py.stub
  - data/CHANGELOG.md
---

## Problem

The documentation describes a `DB_DISPOSABLE_DATABASES` allowlist that would
permit destructive migration commands against explicitly named throwaway
databases. The code refuses every destructive operation unconditionally, so
either a documented safety switch is missing or three documents promise a
mechanism the engine deliberately does not have. Only the owner can say which.

## Evidence

- `data/engine/migrations/safety.py` — `is_disposable_database()` returns `False`
  unconditionally and `assert_disposable()` always raises
  `DestructiveOperationRefused`; therefore `migrate fresh|reset|refresh|rollback`
  and `db wipe` have no execution path.
- `data/config/database.py` — docstring documents `disposable_databases` and
  `DB_DISPOSABLE_DATABASES` with `_test`-named databases.
- `data/engine/cli/skeleton/config/database.py.stub` — the generated project
  carries the same documented allowlist.
- `data/CHANGELOG.md` (around line 722) — records the allowlist as a feature.
- `data/tests/test_database_safety.py` — asserts the allowlist "cannot be
  enabled", which reads as the intended direction (refuse always).

## Done when

- [ ] The owner records the decision in this file.
- [ ] If the allowlist should exist: implement it in `safety.py` with a test
      proving a named disposable database is refused when not listed and
      permitted when listed, and that no production-shaped name can be listed.
- [ ] If it should not exist: remove the promise from `config/database.py`, the
      skeleton stub and the CHANGELOG entry, replacing it with the real rule.

## Verify

```bash
docker exec framework sh -lc 'cd /app && python -m pytest tests/test_database_safety.py -q'
```

## Notes

**Sensitive area — never execute without an explicit owner decision** (data
deletion; `AGENTS.md` NR-02/NR-03, BQ-11). This task exists so the divergence is
tracked instead of silently "fixed" in either direction.

## History

- 2026-10-07T08:09:13Z created by qwen@qwen-code (source: framework audit 2026-10-07)
