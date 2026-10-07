---
task: p2-20261007-085101-agent-install-writes-dot-claude
outcome: resolved
agent: qwen@qwen-code (Qwen Code, local Ollama)
started_at: 2026-10-07T16:30:00Z
finished_at: 2026-10-07T16:34:29Z
---

## What changed

- `data/engine/cli/agent_catalog/__init__.py` (outside the declared touches; the
  owner authorised it): `DEFAULT_TARGET_DIR` is now `.agents`; a new
  `ensure_layout()` creates that directory and keeps `.claude` a relative symlink
  to it, and raises `LegacyAgentDirectoryError` (`AGENT_LEGACY_DIRECTORY`) when a
  physical `.claude/` is present — a legacy layout is refused, never merged into a
  second directory. `install()` calls it after its conflict check, so a rejected
  install still leaves the project untouched.
- `data/engine/cli/agent_scaffolder.py`: `scaffold_agent_stack()` now writes the
  contract at `.agents/rules/AGENTS.md` (the pointer stub is gone), calls
  `ensure_layout()` first, and installs the catalog into `.agents/`. The module
  docstring and the `agents_md`, `llms.txt` and `project_agents` texts name
  `.agents/...`.
- `data/llms.txt` and `data/documentation/llms.txt`: the generated one-line
  install path now reads `.agents/`.
- `data/tests/test_agent_catalog.py`: paths moved to `.agents/`; two new tests
  prove `.claude` is a symlink to `.agents` and that a legacy physical `.claude/`
  is refused untouched.
- `data/tests/test_cli_auth_and_agent.py` (outside the declared touches; the owner
  authorised it): the `agents_pointer` artefact assertion is replaced by the
  `.claude` symlink and the `.agents/rules/AGENTS.md` contract.
- `data/CHANGELOG.md`: entry under `[Unreleased]` → `### Changed`.

## Verification

```bash
docker exec framework sh -lc 'cd /app && python -m pytest tests/test_agent_catalog.py tests/test_cli_auth_and_agent.py -q'
# 21 passed in 1.60s

# full suite, SQLite (.env moved aside so the run reproduces CI)
docker exec framework sh -lc 'cd /app && mv .env /tmp/env.bak; python -m pytest tests -q; mv /tmp/env.bak .env'
# 2078 passed, 68 skipped in 122.99s

# full suite, PostgreSQL
docker exec -e CRAFT_TEST_DB=pgsql -e DB_SSLMODE=disable framework sh -lc 'cd /app && mv .env /tmp/env.bak; python -m pytest tests -q; mv /tmp/env.bak .env'
# 2141 passed, 5 skipped in 178.29s

docker exec framework sh -lc 'cd /app && python dev.py agent:list | head -5'
# lists the catalog (agent/skill rows), exit 0

docker exec framework sh -lc 'cd /app && ruff check engine'
# All checks passed!
cd data && python tools/check_engine_boundary.py
# ENGINE_BOUNDARY_NEW_FINDINGS 0
cd data && python3 ../.agents/rules/lint_language.py --config language-standard.toml
# Language standard: clean.
```

The generated project still loads the catalog in Claude Code: `ensure_layout()`
makes `.claude` a symlink to `.agents`, and the tests read
`.claude/agents/...` and `.claude/rules/AGENTS.md` through it.

## Follow-ups

New task `p3-20261007-163417` for `documentation/ai_agents.md` and
`documentation/cli.md`, which still name `.claude/...` and were outside this
task's touches.
