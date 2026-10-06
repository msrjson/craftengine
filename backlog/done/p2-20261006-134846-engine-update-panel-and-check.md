---
id: "20261006-134846"
title: Engine update notice in the admin panel, visual update, and CLI parity
type: feature
priority: 2
autonomous: true
blocked_by: none
max_attempts: 2
attempts: 1
claimed_by: claude@claude-code
created_at: 2026-10-06T13:48:46Z
updated_at: 2026-10-06T13:57:46Z
source: owner request 2026-10-06 (update through the panel as a user, with the same option in the CLI)
touches:
  - data/engine/lifecycle/
  - data/engine/providers/
  - data/engine/cli/
  - data/tests/
  - data/documentation/
  - docs/adr/0005-engine-lifecycle.md
  - data/CHANGELOG.md
---

## Problem

The engine lifecycle is console-only. The owner wants the panel to warn when
the canonical repository publishes a newer release, and wants to review and
apply the update visually as a signed-in admin. Every panel operation must
also exist in the console.

## Evidence

- `data/engine/cli/engine_commands.py` - no cached update check.
- `data/engine/cli/admin_templates/` - no engine screen, no update notice.

## Done when

- [x] `EngineUpdates` (container key `engine_updates`) checks the source, caches
      the notice, reviews a move (dry run) and applies it with the lock's
      verification command, one move at a time.
- [x] `engine check` refreshes the same cached notice from the console;
      `engine verify-command` sets the command the panel and the console use.
- [x] `make:engine-panel` generates the screen, the alert partial, the
      translations (en, pt-BR, es) and the routes; `make:admin` includes it.
- [x] Panel requests never call the network; the check is explicit or scheduled.
- [x] Tests pass in the `framework` container.

## Verify

```bash
docker exec framework sh -lc 'cd /app && python -m pytest tests/test_engine_lifecycle.py tests/test_engine_updates.py tests/test_admin_scaffolder.py -q'
```

## Notes

The verification command comes from `craft-engine.lock`, never from a form:
a field that runs a command would make every admin a shell user.

## History

- 2026-10-06T13:48:46Z created by claude@claude-code (source: owner request 2026-10-06)
- 2026-10-06T13:48:46Z claimed by claude@claude-code (attempt 1)
- 2026-10-06T13:57:46Z resolved by claude@claude-code (13 tests incl. HTTP panel journey; full suite 1921 passed)
