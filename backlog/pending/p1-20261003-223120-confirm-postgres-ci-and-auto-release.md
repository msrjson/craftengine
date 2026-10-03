---
id: "20261003-223120"
title: Confirm the PostgreSQL CI job and the automatic release on the next push
type: chore
priority: 1
autonomous: false
blocked_by: owner-action
max_attempts: 2
attempts: 0
created_at: 2026-10-03T22:31:20Z
updated_at: 2026-10-03T22:31:20Z
source: docs/backlog.md P2
touches: []
---

## Problem

The suite runs PostgreSQL in a fresh `craft_test_*` database per session and no longer deletes, truncates or drops (3a7c62f). It was verified locally against PostgreSQL 18; the GitHub `test-postgres` job and the automatic `release` job were never observed after that change.

## Evidence

- Local runs: PostgreSQL `1758 passed, 4 skipped`; SQLite `1696 passed, 66 skipped`.
- CI run 36046625355 (before the fix): SQLite success, PostgreSQL exit code 4, release skipped.

## Done when

- [ ] The owner pushed `master`.
- [ ] The `test-postgres` job of that push is green.
- [ ] The `release` job ran on its own and created the release for that version.

## Verify

```bash
gh run list --repo msrjson/craftengine --limit 5
gh run view <run-id> --repo msrjson/craftengine
```

## Notes

Blocked on the owner: agents never push. Once pushed, an agent may run the Verify commands and resolve this task read-only.
Residue by design on a development server: one `craft_test_*` database per session and one `craft_rls_probe_*` role; nothing is dropped.

## History

- 2026-10-03T22:31:20Z created by claude (source: docs/backlog.md P2; migrated from the single-file backlog)
