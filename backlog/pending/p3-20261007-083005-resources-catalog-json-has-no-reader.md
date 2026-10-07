---
id: "20261007-083005"
title: resources/lang/catalog.json has no reader but is cited as the canonical translation catalog
type: decision
priority: 3
autonomous: false
blocked_by: owner-decision
max_attempts: 2
attempts: 0
created_at: 2026-10-07T08:30:05Z
updated_at: 2026-10-07T08:30:05Z
source: framework audit 2026-10-07 (dead-code sweep)
touches:
  - data/resources/lang/catalog.json
  - data/database/seeders/TranslationSeeder.py
  - data/documentation/localization.md
  - data/language-standard.toml
---

## Problem

`data/resources/lang/catalog.json` is opened by no code, test, migration or tool,
yet three places call it the canonical catalog of translation keys. Either it
should feed the seeder (or a migration) or the citations should go.

## Evidence

- No reader: `grep -rn 'catalog.json' data/` finds only prose references -
  `database/seeders/TranslationSeeder.py:16` (comment),
  `documentation/localization.md:123`, `language-standard.toml:69` (the comment
  that names `resources/lang/catalog.json` as holding "75 dot.case keys with
  complete values in all four locales").
- The seeder uses an inline dict; it never reads the file.

## Done when

- [ ] The owner picks one:
      (a) **wire it** - the seeder (or a forward migration) reads
      `catalog.json`, so the file is the source and the comment is true; or
      (b) **remove it** - delete the file and fix the three citations.
- [ ] No document calls a file "canonical" while nothing reads it.

## Verify

```bash
grep -rn 'catalog.json' data/
docker exec framework sh -lc 'cd /app && python -m pytest tests -q'
```

## Notes

The engine's i18n is database-first (`translations` table); a JSON catalog is
only a seeding source. Removing it is documentation-only if the seeder already
carries the values - verify the seeder holds every key before choosing (b).

## History

- 2026-10-07T08:30:05Z created by qwen@qwen-code (source: dead-code sweep 2026-10-07)
