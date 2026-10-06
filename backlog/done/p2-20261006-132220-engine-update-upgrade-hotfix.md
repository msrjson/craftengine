---
id: "20261006-132220"
title: Engine lifecycle - lock, status, update, upgrade and hotfix commands
type: feature
priority: 2
autonomous: true
blocked_by: none
max_attempts: 2
attempts: 1
claimed_by: claude@claude-code
created_at: 2026-10-06T13:22:20Z
updated_at: 2026-10-06T13:37:02Z
source: owner request 2026-10-06 ("what craftengine lacks is the update, upgrade and hotfix engine")
touches:
  - data/engine/lifecycle/
  - data/engine/cli/engine_commands.py
  - data/engine/cli/app.py
  - data/engine/cli/project_scaffolder.py
  - data/tests/test_engine_lifecycle.py
  - data/tests/test_project_scaffolder.py
  - data/documentation/engine-lifecycle.md
  - docs/adr/0005-engine-lifecycle.md
  - data/CHANGELOG.md
---

## Problem

A project built on Craft Engine has no way to know which engine it runs, to
move to a newer release, or to take a single security fix without moving.
`craft new` copies the skeleton and records no engine version. Projects that
vendor `engine/` (SoftPax) drift silently - 314 files diverge from v4.4.2 - and
are now inventing their own lock and patch ledger to be able to upgrade.

## Evidence

- `data/engine/cli/app.py` - no `upgrade`, `update` or `hotfix` command.
- `data/engine/cli/project_scaffolder.py:181` - the skeleton is copied; no
  engine pin is written.
- Team bus 2026-10-06 #136-#140: SoftPax builds `deploy/craft-engine-lock.json`
  with patch classes `security|improvement|upstream-sync` on its own.

## Done when

- [x] `craft-engine.lock` (JSON) records source, mode (`package` or
      `vendored`), ref, version, release, file manifest and local patches.
- [x] `craft engine adopt <ref>` writes the lock; `craft new` writes one too.
- [x] `craft engine status` reports unregistered drift, patches and newer releases.
- [x] `craft engine patch` registers local edits with a class and a reason.
- [x] `craft engine hotfix <ref> <paths>` takes files from a canonical ref and
      records them as a security patch without changing version.
- [x] `craft engine update` moves to the newest patch release of the same minor;
      `craft engine upgrade --to X.Y.Z` moves across minors and majors, shows the
      changelog between, refuses downgrades.
- [x] Applying is transactional: staged beside the current engine, swapped,
      verified by an optional command, rolled back on failure.
- [x] Patches absorbed upstream are retired; conflicting patches block the move.
- [x] Tests cover every refusal and both modes, run in the `framework` container.

## Verify

```bash
docker exec framework sh -lc 'cd /app && python -m pytest tests/test_engine_lifecycle.py tests/test_project_scaffolder.py -q'
```

## Notes

Releases are fetched as tag archives from the canonical remote (the same URL the
CRM demo's Dockerfile pins), with the standard library only: the `framework`
container has no git, and the engine must not depend on it. Never from the
development workspace (owner ruling 2026-09-22).

## History

- 2026-10-06T13:22:20Z created by claude@claude-code (source: owner request 2026-10-06)
- 2026-10-06T13:23:30Z claimed by claude@claude-code (attempt 1)
- 2026-10-06T13:37:02Z resolved by claude@claude-code (43 lifecycle tests, full suite 1903 passed, end-to-end against the canonical repository)
