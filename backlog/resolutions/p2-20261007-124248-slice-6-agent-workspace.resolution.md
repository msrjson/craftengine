---
task: p2-20261007-124248-slice-6-agent-workspace
outcome: resolved
agent: qwen@qwen-code (Qwen Code, local Ollama)
started_at: 2026-10-07T18:04:53Z
finished_at: 2026-10-07T18:15:18Z
---

## What changed

- **Catalog skills** (commit `d828d43`): `engine/cli/agent_catalog/skills/`
  gains `tests-in-container` (a test counts as evidence only from the
  application container) and `craft-engine-pitfalls` (the recurring traps:
  parity assumptions, forward-only data, relations as methods, the engine
  boundary, `.agents/`). `tests/test_agent_catalog.py` follows.
- **Coordination kit and integration points** (commit `f5a5cef`):
  `engine/cli/agent_scaffolder.py` gains `coordination_kit()` and writes, under
  `.agents/`, an append-only `team/board.md`, `lessons.md`, the `handoffs/`
  directory, `journeys/smoke.json`, `validation.json`,
  `multi-session-coordination.md` and the `team-lead` agent.
- **Environment guard, pre-commit, CI, editor** (this commit):
  `developer_files()` writes `.agents/hooks/environment_guard.sh` (refuses the
  suite on the host), `.githooks/pre-commit`, `.github/workflows/ci.yml` and
  `.vscode/tasks.json` / `.vscode/launch.json`; the two shell files are made
  executable. `tests/test_cli_auth_and_agent.py` asserts every path exists.
- The **single-directory layout** — one contract at `.agents/rules/AGENTS.md`,
  no duplicated copy, `.claude` a symlink to `.agents` — had already landed in
  `p2-20261007-085101`; no duplicate content remains.
- CHANGELOG entries for each part.

## Deviation recorded

The Done-when's parenthetical "`.agents -> .claude`" is the **inverse** of the
owner's 2026-10-07 ruling (`.claude -> .agents`). The ruling wins: `.claude` is
the symlink and `.agents` the physical directory. Flagged in the task History
at claim time.

## Verification

```bash
docker exec framework sh -lc 'cd /app && python -m pytest tests/test_project_scaffolder.py tests/test_application_engine_guard.py tests/test_agent_catalog.py tests/test_cli_auth_and_agent.py -q'
# green

# full suite, SQLite (.env moved aside so the run reproduces CI)
docker exec framework sh -lc 'cd /app && mv .env /tmp/env.bak; python -m pytest tests -q; mv /tmp/env.bak .env'
# 2155 passed, 68 skipped in 120.86s

# full suite, PostgreSQL
docker exec -e CRAFT_TEST_DB=pgsql -e DB_SSLMODE=disable framework sh -lc 'cd /app && mv .env /tmp/env.bak; python -m pytest tests -q; mv /tmp/env.bak .env'
# 2218 passed, 5 skipped in 137.94s

docker exec framework sh -lc 'cd /app && ruff check engine'                 # All checks passed!
cd data && python tools/check_engine_boundary.py                             # ENGINE_BOUNDARY_NEW_FINDINGS 0
cd data && python3 ../.agents/rules/lint_language.py --config language-standard.toml   # clean
python3 .agents/rules/lint_backlog.py && python3 .agents/rules/lint_board.py  # clean
```

## Follow-ups

None. What `agent:scaffold` writes into a *generated* project is exercised
through `craft new`, a separate context; a change there reaches a project only
through a release.
