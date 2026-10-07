---
task: p2-20261007-081352-translations-not-unique-per-key-and-locale
outcome: resolved
agent: qwen@qwen-code (Qwen Code, local Ollama)
started_at: 2026-10-07T08:23:00Z
finished_at: 2026-10-07T08:45:00Z
commits: []
---

## What changed

- `data/database/migrations/2026_10_07_000001_unique_index_on_translations.py`
  (new) - forward-only migration adding `uq_translations_key_locale` on
  `(key, locale)`. It first probes for existing duplicates and refuses with a
  reconciliation message, because NR-02 forbids deleting a translation row to
  force the index through. `down()` raises, like every forward-only migration.
- `data/engine/cli/skeleton/database/migrations/2025_01_01_000004_create_translations_and_settings_tables.py.stub`
  - a new project now creates the table with the same unique index, so it never
  needs the repair migration.
- `data/tests/test_translation.py` - `TestOneRowPerKeyAndLocale`: a duplicate
  `(key, locale)` insert is refused and leaves one row; the same key in another
  locale is allowed.
- `data/CHANGELOG.md` - `[Unreleased] / Fixed` entry.

## Verification

```
docker exec framework sh -lc 'cd /app && python -m pytest tests/test_translation.py -q'
# 23 passed

docker exec -e CRAFT_TEST_DB=pgsql -e DB_SSLMODE=disable -e DB_HOST=db -e DB_PORT=5499 \
  -e DB_DATABASE=craft_db -e DB_USERNAME=craft -e DB_PASSWORD=secretpassword \
  framework sh -lc 'cd /app && python -m pytest tests/test_translation.py -q'
# 23 passed

docker exec -e CRAFT_TEST_DB=pgsql ... framework sh -lc 'cd /app && python -m pytest tests -q'
# 2037 passed, 4 skipped   (conftest builds the schema with the real migrator,
#                           so the new migration ran on PostgreSQL)

docker exec framework sh -lc 'cd /app && ruff check engine tests/test_translation.py'
# All checks passed!
```

Existing duplicates: the development databases hold none
(`data/storage/database.sqlite` 92 rows, `craft_test.sqlite` 66 rows, zero
duplicate pairs), so the migration applies cleanly here; on a database that
holds duplicates it refuses instead of dropping data.

## Follow-ups

None.
