---
id: "20261007-124248"
title: Implement Slice 6 of the SoftPax upstream roadmap (agent workspace scaffolding)
type: feature
priority: 2
autonomous: true
blocked_by: none
max_attempts: 2
attempts: 1
claimed_by: qwen@qwen-code
created_at: 2026-10-07T12:42:48Z
updated_at: 2026-10-07T18:15:18Z
source: .agents/plans/softpax-upstream-roadmap.md, Slice 6
touches:
  - data/engine/cli/agent_scaffolder.py
  - data/engine/cli/
  - data/engine/cli/skeleton/
  - data/tests/
  - data/documentation/
  - data/CHANGELOG.md
---

## Problem

Slice 6 of the upstream roadmap ("Last-generation agent workspace") is not
landed: a generated project gets duplicated instruction copies and none of the
coordination kit, hooks, CI or catalog skills the slice names.

## Evidence

- `data/engine/cli/agent_scaffolder.py` writes `AGENTS.md` at the root *and*
  `.claude/rules/AGENTS.md` with the same content, plus a pointer file - no
  symlinks, so the copies drift.
- No `.claude/team/board.md`, `multi-session-coordination.md` or `team-lead`
  agent is generated.
- No `journeys/smoke.json`, `validation.json`, `lessons.md` or `local-brief.md`
  integration points; no Python environment guard hook; no generated
  pre-commit, CI workflow or `.vscode/tasks.json`/`launch.json`.
- `data/engine/cli/agent_catalog/skills/` has 25 skills, without
  `tests-in-container` and `craft-engine-pitfalls`.

## Done when

- [ ] A generated project has one `AGENTS.md` and tool paths as symlinks
  (`.agents -> .claude`), no duplicated content.
- [ ] The coordination kit, integration points, environment guard hook, generated
  pre-commit/CI/VS Code files and the two catalog skills exist and are covered
  by tests.
- [ ] Full suite green on SQLite and PostgreSQL in the framework container;
  ruff, engine-boundary and language gates clean.

## Verify

```bash
docker exec framework sh -lc 'cd /app && python -m pytest tests/test_project_scaffolder.py tests/test_application_engine_guard.py tests/test_agent_catalog.py -q'
docker exec framework sh -lc 'cd /app && python -m pytest tests -q'
```

## Notes

- The generated-project side follows `data/engine/cli/skeleton/`; a change there
  is validated in the `framework` container and reaches a real project only
  through `craft new`.
- Related: p2-20261007-084616 (global .agents migration), p2-20261007-085101
  (agent:install writes .claude) and p3-20261007-081500.

## History

- 2026-10-07T12:42:48Z created by qwen@qwen-code (source: .agents/plans/softpax-upstream-roadmap.md, Slice 6; queued after the Slice 4 task)
- 2026-10-07T18:04:53Z claimed by qwen@qwen-code (attempt 1)
- 2026-10-07T18:04:53Z scope note by qwen@qwen-code: the Done-when's "`.agents -> .claude`" is the inverse of the owner's 2026-10-07 ruling (`.claude -> .agents`); the ruling wins, so any symlink generated will point `.claude` at `.agents`. Increment 1 (this commit): the two catalog skills `tests-in-container` and `craft-engine-pitfalls` under `engine/cli/agent_catalog/skills/`, with `tests/test_agent_catalog.py` updated (13 passed). Remaining: coordination kit, integration points, environment guard hook, generated pre-commit/CI/VS Code, and the single-AGENTS.md-with-symlinks layout in the scaffolder/skeleton
- 2026-10-07T18:15:18Z resolved by qwen@qwen-code (resolutions/p2-20261007-124248-slice-6-agent-workspace.resolution.md): the two catalog skills (d828d43), the coordination kit + integration points (f5a5cef) and the environment guard/pre-commit/CI/VS Code files landed; the single-directory layout had already landed in p2-20261007-085101. Full suite green on SQLite (2155/68) and PostgreSQL (2218/5); ruff, engine-boundary, language, backlog and board gates clean
