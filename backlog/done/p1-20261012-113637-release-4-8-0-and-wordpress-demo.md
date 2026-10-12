---
id: "20261012-113637"
title: Release Craft Engine 4.8.0 r00028 and publish the WordPress-style demo
type: chore
priority: 1
autonomous: true
blocked_by: none
max_attempts: 2
attempts: 1
claimed_by: claude@claude-code
created_at: 2026-10-12T11:36:37Z
updated_at: 2026-10-12T11:57:27Z
source: owner request in chat, 2026-10-12
touches:
  - data/CHANGELOG.md
  - data/pyproject.toml
  - data/engine/__init__.py
  - data/VERSION
  - data/CRAFT_ENGINE.md
  - data/CONTRIBUTING.md
  - data/documentation/
  - AGENTS.md
  - .agents/scripts/rehearse-demo.sh
  - data-demo/README.md
  - data-demo/Dockerfile
  - data-demo/craft-engine.lock
---

## Problem

`master` carries 66 commits and 36 changelog entries on top of v4.7.0 r00027
that were never released. The demo (`data-demo/`) became a WordPress-style
admin whose purpose is to validate the extension isolation architecture, but
its README still describes a CRM, it pins the previous engine release, and it
was never pushed to its repository. Workspace documents still call it "the CRM
demo".

## Evidence

- `data/CHANGELOG.md` - `## [Unreleased]` holds Added, Changed and Fixed entries.
- `data-demo/README.md:1` - titled "Craft CRM".
- `data-demo/Dockerfile:10` - `CRAFT_ENGINE_REF=v4.7.0-r00027`.
- `AGENTS.md:41` - the context table names the demo "Demo (CRM)".

## Done when

- [x] Version and release counter agree at 4.8.0 r00028, with the changelog promoted.
- [x] The framework suite passes on SQLite and PostgreSQL in the `framework` container; ruff, the language gate and the engine boundary gate exit 0.
- [x] The demo rehearsal passes against the candidate on SQLite and PostgreSQL.
- [x] Framework documentation covers what the release ships; the demo README describes the WordPress-style admin and the isolation it validates.
- [x] `master` and `main` are pushed, CI is green and has created `v4.8.0-r00028`.
- [x] The demo pins `v4.8.0-r00028`, its suite passes in its own container, and it is pushed to `msrjson/craftengine-demo`.

## Verify

```bash
docker exec framework sh -lc 'cd /app && python -m pytest tests -q'
sh .agents/scripts/rehearse-demo.sh
```

## Notes

Forward-only: no database reset in any context. The tag is created by CI, never
by hand. The website (`data-website/`) is a separate context and is not touched.

## History

- 2026-10-12T11:36:37Z created by claude@claude-code (source: owner request in chat, 2026-10-12)
- 2026-10-12T11:37:36Z owner ruling: the owner asked in chat for this release, the documentation update and the publication of framework and demo; claimed by claude@claude-code (attempt 1)
- 2026-10-12T11:40:36Z checkpoint by claude@claude-code: version cut to 4.8.0 r00028, static gates clean, demo rehearsal 107 passed on SQLite and PostgreSQL; framework suite still running, nothing pushed
- 2026-10-12T11:44:59Z checkpoint by claude@claude-code: data/VERSION bumped after 4 release-sync failures; framework guides audited against the 36 changelog entries (docs:check 43 pages, no broken links); demo README rewritten, /tickets and /invoices put behind auth with a test, visible CRM naming removed; scope widened to data-demo/app, data-demo/tests, data-demo/resources and data-demo/docker-compose.yml for those fixes; full rerun in progress, nothing pushed
- 2026-10-12T11:49:45Z candidate verified by claude@claude-code: framework suite 2169 passed / 68 skipped on SQLite and 2232 passed / 5 skipped on PostgreSQL (framework container, local .env moved aside); demo rehearsal 109 passed on both; pushing master and main under the owner's request
- 2026-10-12T11:57:27Z resolved by claude@claude-code: v4.8.0-r00028 released by CI at 01482f5 (master and main pushed); demo pinned to it and pushed to msrjson/craftengine-demo at 1f60655; resolution in resolutions/
