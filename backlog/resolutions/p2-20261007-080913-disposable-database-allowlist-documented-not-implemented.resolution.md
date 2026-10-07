---
task: p2-20261007-080913-disposable-database-allowlist-documented-not-implemented
outcome: resolved
agent: qwen@qwen-code (Qwen Code, local Ollama)
started_at: 2026-10-07T08:23:00Z
finished_at: 2026-10-07T08:45:00Z
commits: []
---

## What changed

The owner chose the safe direction: remove the promise, never enable a wipe
path.

- `data/config/database.py` - the inert `disposable_databases = env("DB_DISPOSABLE_DATABASES", "")`
  key is gone, replaced by a comment stating the real rule: destructive schema
  operations are refused in every environment, with no allowlist, no `_test`
  exemption and no in-memory carve-out.
- `data/engine/cli/skeleton/config/database.py.stub` - the same change, so a
  generated project no longer carries a key nothing reads.
- `data/CHANGELOG.md` - `[Unreleased] / Changed` entry correcting the earlier
  note and recording the unconditional refusal.
- `data/engine/migrations/safety.py` was left unchanged: `is_disposable_database()`
  returning false and `assert_disposable()` always raising **is** the implemented
  policy, not a bug.

## Verification

```
grep -rn 'disposable' data/config/database.py data/engine/cli/skeleton/config/database.py.stub
# no match

docker exec framework sh -lc 'cd /app && ruff check engine'
# All checks passed!

docker exec -e CRAFT_TEST_DB=pgsql -e DB_SSLMODE=disable -e DB_HOST=db -e DB_PORT=5499 \
  -e DB_DATABASE=craft_db -e DB_USERNAME=craft -e DB_PASSWORD=secretpassword \
  framework sh -lc 'cd /app && python -m pytest tests -q'
# 2037 passed, 4 skipped
```

`tests/test_database_safety.py` still passes: it builds its own config object, so
it never read the removed key.

## Follow-ups

None. The `allowlist` parameter of `is_disposable_database()` remains as tested
API; removing it would break the public signature (NR-05) for no behavioural gain.
