---
id: "20261006-205116"
title: Correct extension lifecycle and document framework composition
type: bugfix
priority: 2
autonomous: true
blocked_by: none
max_attempts: 2
attempts: 1
claimed_by: gpt@codex
created_at: 2026-10-06T20:51:16Z
updated_at: 2026-10-06T21:03:16Z
source: owner request to correct and document architecture gaps, 2026-10-06
touches:
  - data/engine/extensions/
  - data/engine/container/application.py
  - data/engine/cli/extension_commands.py
  - data/engine/cli/extension_templates/
  - data/tests/
  - data/documentation/
  - data/README.md
  - data/CRAFT_ENGINE.md
  - data/CHANGELOG.md
  - docs/adr/0004-extension-model.md

---

## Problem

Extension services survive deactivation and installed extensions have no explicit update operation. Responsibilities and the distinction between the engine and a CMS application need a single documented contract.

## Evidence

- `data/engine/extensions/context.py:52`: providers receive the raw container; service bindings are not tracked.
- `data/engine/extensions/manager.py:130`: install refuses an installed extension.
- `data/engine/cli/extension_commands.py:119`: screen generator incorrectly recommends reinstalling for migrations.
- `data/engine/extensions/loader.py:71`: unloaded routes remain registered.

## Done when

- [x] Owned service bindings are removed on unload; failed activation rolls back partial routes. Disabled routes keep their documented typed refusal.
- [x] Explicit inactive extension updates preserve records and edited translations, validate compatibility, and distinguish disk and installed versions.
- [x] Boot and reconcile validate dependencies and compatibility.
- [x] Architecture guide defines domain ownership, extension seams, presentation, application composition, upgrade procedure and in-process isolation limits.
- [x] Regression tests and required gates pass.

## Verify

```bash
docker exec framework sh -lc 'cd /app && python -m pytest tests -q'
docker exec framework sh -lc 'cd /app && ruff check engine'
(cd data && python tools/check_engine_boundary.py)
python3 .claude/rules/lint_backlog.py
python3 .claude/rules/lint_board.py
(cd data && python3 ../.claude/rules/lint_language.py --config language-standard.toml)
(cd data && python3 ../.claude/rules/lint_language.py --config language-standard.views.toml)
```

## Notes

Framework context only. The existing CRM task is owned by another agent. No CMS implementation, shared database migration, release or publication. Code replacement requires coordinated worker restarts; activation is not a Python hot reload.

## History

- 2026-10-06T20:51:16Z created by gpt@codex (owner authorized correction and documentation)
- 2026-10-06T20:51:27Z claimed by gpt@codex (attempt 1)
- 2026-10-06T20:54:21Z clarified by gpt@codex: preserve disabled-route compatibility; seed new refusals in a separate forward migration task
- 2026-10-06T21:00:00Z verification commands grounded by gpt@codex in the existing data language configs; SQLite full suite 1955 passed, isolated update regressions 22 passed
- 2026-10-06T21:03:16Z resolved by gpt@codex (backlog/resolutions/p2-20261006-205116-extension-lifecycle-and-architecture.resolution.md)
