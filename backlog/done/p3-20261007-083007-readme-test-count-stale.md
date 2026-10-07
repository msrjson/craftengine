---
id: "20261007-083007"
title: The framework README still advertises 1,500+ tests while the suite reports 2037
type: chore
priority: 3
autonomous: true
blocked_by: none
max_attempts: 2
attempts: 1
claimed_by: qwen@qwen-code
created_at: 2026-10-07T08:30:07Z
updated_at: 2026-10-07T08:45:00Z
source: framework audit 2026-10-07 (documentation review)
touches:
  - data/README.md
---

## Problem

`data/README.md` says "**1,500+ tests**, validated on SQLite, PostgreSQL, and
Python 3.14", while the suite the repository actually runs reports 2037 passed
on PostgreSQL and about 1971 on SQLite, and `CRAFT_ENGINE.md` was corrected to
"1900+ tests" in the same audit. Two entry pages, two different numbers.

## Evidence

- `data/README.md` - "**1,500+ tests**, validated on SQLite, PostgreSQL, and
  Python 3.14."
- `data/CRAFT_ENGINE.md` - now "1900+ tests" (corrected 2026-10-07).
- Board 2026-10-06: v4.7.0-r00027 verified with SQLite 1971 and PostgreSQL 2033;
  the 2026-10-07 run reports 2037 on PostgreSQL.

## Done when

- [ ] `data/README.md` states a test count that matches the release evidence, or
      drops the number so it cannot go stale.

## Verify

```bash
grep -n 'tests' data/README.md | head -3
grep -n 'tests' data/CRAFT_ENGINE.md | head -3
```

## History

- 2026-10-07T08:30:07Z created by qwen@qwen-code (source: framework audit 2026-10-07)
- 2026-10-07T08:35:00Z claimed by qwen@qwen-code (attempt 1)
- 2026-10-07T08:45:00Z resolved by qwen@qwen-code (resolutions/p3-20261007-083007-readme-test-count-stale.resolution.md)
