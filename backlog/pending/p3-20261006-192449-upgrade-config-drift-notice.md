---
id: "20261006-192449"
title: engine upgrade should tell the project about new config it needs
type: feature
priority: 3
autonomous: true
blocked_by: none
max_attempts: 2
attempts: 0
created_at: 2026-10-06T19:24:49Z
updated_at: 2026-10-06T19:24:49Z
source: demo move to v4.6.0 (2026-10-06)
touches:
  - data/engine/lifecycle/
  - data/documentation/engine-lifecycle.md
---

## Problem

`engine upgrade` swaps the engine and never touches project files, so a new default such as the `app/connectors` extension root stays missing from the project's `config/extensions.py`. The demo's connector was not discovered until the path was added by hand.

## Evidence

- `data/config/extensions.py:15` lists the new root; `data-demo/config/extensions.py` did not after the upgrade.

## Done when

- [ ] `engine upgrade` prints, from the CHANGELOG entry, a "project files to review" note when a release declares one, and a test covers it.

## Verify

```bash
docker exec framework sh -lc 'cd /app && python -m pytest tests/test_engine_lifecycle.py -q'
```

## Notes

A note in the CHANGELOG convention (a `Project files:` line) is probably enough; no automatic edits to project files.

## History

- 2026-10-06T19:24:49Z created by claude@claude-code (source: demo move to v4.6.0)
