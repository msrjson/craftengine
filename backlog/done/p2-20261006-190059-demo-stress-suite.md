---
id: "20261006-190059"
title: Demo: stress suite for tenants, events, jobs, rollback and theme swap on both databases
type: feature
priority: 2
autonomous: true
blocked_by: none
max_attempts: 2
attempts: 1
claimed_by: claude@claude-code
created_at: 2026-10-06T19:00:59Z
updated_at: 2026-10-06T19:24:38Z
source: owner order 2026-10-06 (demo must stress every extension kind through the CLI)
touches:
  - data-demo/
---

## Problem

The demo needs scenarios that push the framework: tenant A, tenant B and owner isolation, events and jobs across modules, extension deactivation, runtime theme swap, on SQLite and PostgreSQL.

## Evidence

- The demo installs the engine from a release tag, so the connector kind and the module-born-with-migration generator (unreleased, CHANGELOG Unreleased) reach it only after a release.

## Done when

- [x] Each scenario has a passing test on both databases, and tenant isolation has A/B/owner proof.

## Verify

```bash
docker compose exec -T app python -m pytest tests -q
```

## Notes

Blocked on the owner cutting and publishing the next release (BQ-11). Generate everything with the CLI; hand-write only business rules.

## History

- 2026-10-06T19:00:59Z created by claude@claude-code (source: owner order 2026-10-06)
- 2026-10-06T19:24:38Z owner ruling: published v4.6.0-r00026 and ordered the demo slices executed (2026-10-06, "Sim, publique")
- 2026-10-06T19:24:38Z claimed by claude@claude-code (attempt 1)
- 2026-10-06T19:24:38Z resolved by claude@claude-code (see resolutions/p2-20261006-190059-demo-stress-suite.resolution.md)
