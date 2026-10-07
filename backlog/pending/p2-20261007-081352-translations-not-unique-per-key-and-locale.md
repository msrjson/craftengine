---
id: "20261007-081352"
title: The translations table has no unique index on (key, locale); duplicates resolve silently
type: bugfix
priority: 2
autonomous: false
blocked_by: owner-decision
max_attempts: 2
attempts: 0
created_at: 2026-10-07T08:13:52Z
updated_at: 2026-10-07T08:13:52Z
source: framework audit 2026-10-07 (i18n exploration)
touches:
  - data/database/migrations/
  - data/engine/support/translation.py
---

## Problem

Translations are keyed by `(key, locale)` but the table enforces nothing: two
rows with the same pair are accepted, and the loader keeps whichever row the
query returns last. A seed mistake or a concurrent admin edit changes displayed
copy with no error.

## Evidence

- `data/database/migrations/2025_01_01_000004_create_framework_dynamic_tables.py:11-17`
  — `t.string("key")` and `t.string("locale")` carry no `.unique()` and no
  composite index, while sibling tables in the same migration do
  (`modules.slug`, `roles.name`, `roles.slug`).
- `data/engine/support/translation.py:94-102` — `_fetch_bundle` builds
  `{key: value}` from every row of the locale, so a duplicate silently
  overwrites and the last row wins.
- Seeders defensively pre-check for an existing row (for example
  `data/database/migrations/2026_10_05_000003_seed_csrf_messages.py:27`), a
  workaround for the missing constraint rather than a substitute.

## Done when

- [ ] A forward-only migration adds the unique constraint/index on
      `(key, locale)`; the decision on pre-existing duplicates is recorded, and
      no translation row is physically deleted (NR-02).
- [ ] The loader's duplicate behaviour is defined by the constraint, not by
      query order.
- [ ] A test proves a duplicate insert is refused.

## Verify

```bash
docker exec framework sh -lc 'cd /app && python -m pytest tests/test_localization.py -q'
```

## Notes

A schema change plus a data question (what to do with duplicates already in a
live database): not autonomous, and not to be merged into an unrelated change.
The engine forbids physical deletes, so deduplication must be a deliberate
soft-touch decision by the owner.

## History

- 2026-10-07T08:13:52Z created by qwen@qwen-code (source: framework audit 2026-10-07)
