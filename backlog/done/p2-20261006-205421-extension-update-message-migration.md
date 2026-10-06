---
id: "20261006-205421"
title: Seed extension update refusal messages through a forward migration
type: bugfix
priority: 2
autonomous: true
blocked_by: none
max_attempts: 2
attempts: 1
claimed_by: gpt@codex
created_at: 2026-10-06T20:54:21Z
updated_at: 2026-10-06T21:03:16Z
source: owner-authorized extension lifecycle correction requires translated refusals
touches:
  - data/database/migrations/2026_10_06_000004_seed_extension_update_messages.py
  - data/engine/cli/skeleton/database/migrations/2026_10_06_000004_seed_extension_update_messages.py.stub
---

## Problem

Existing installations already applied the extension message migration and need the new refusal keys seeded without editing migration history.

## Evidence

- `data/database/migrations/2026_10_05_000002_seed_extension_messages.py:16`: applied once, calls seed_messages.
- `data/engine/extensions/lang/catalog.json`: new update and ownership refusal keys.

## Done when

- [x] A new forward migration seeds missing messages in all three locales without replacing existing records.
- [x] Generated projects include the same migration.

## Verify

```bash
docker exec framework sh -lc 'cd /app && python -m pytest tests/test_extension_updates.py tests/test_project_scaffolder.py tests/test_package_data.py -q'
```

## Notes

Part of the owner-requested extension lifecycle correction. Never run migrations against shared databases.

## History

- 2026-10-06T20:54:21Z created by gpt@codex (owner-authorized correction)
- 2026-10-06T20:54:21Z claimed by gpt@codex (attempt 1)
- 2026-10-06T21:03:16Z resolved by gpt@codex (backlog/resolutions/p2-20261006-205421-extension-update-message-migration.resolution.md)
