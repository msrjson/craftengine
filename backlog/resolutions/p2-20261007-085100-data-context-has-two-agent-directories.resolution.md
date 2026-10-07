---
task: p2-20261007-085100-data-context-has-two-agent-directories
outcome: resolved
agent: qwen@qwen-code (Qwen Code, local Ollama)
started_at: 2026-10-07T16:20:51Z
finished_at: 2026-10-07T16:21:03Z
---

## What changed

- `data/.claude/` (physical: 57 files under `agents/`, `commands/`,
  `references/`, `rules/`, `skills/`) was merged into `data/.agents/`, and
  `data/.claude` is now a relative symlink to `.agents`, mirroring the workspace
  root (`readlink` -> `.agents`). The 128-byte `data/.agents/rules/AGENTS.md`
  stub, which only pointed at `.claude/rules/AGENTS.md`, was replaced by the real
  contract; `data/.agents` now holds 58 files.
- `data/AGENTS.md`: the three `.claude/rules/...` references now read
  `.agents/rules/...`.
- The `data/.claude` symlink is tracked (mode `120000`), as the root's is. Note
  the ignore pattern `data/.gitignore:38` (`.claude/`) does not match a symlink,
  so without tracking it the link would sit untracked in `git status`; tracking it
  records the layout. The `.agents/` content stays local (still ignored by
  `data/.gitignore:41`), exactly as the catalog was before.

## Verification

```bash
ls -la data/.claude data/.agents
# data/.claude -> .agents
readlink data/.claude
# .agents
grep -n '\.claude/' data/AGENTS.md
# (no matches)

docker exec framework sh -lc 'cd /app && readlink .claude; ls -la .claude/rules/AGENTS.md .agents/rules/AGENTS.md'
# .agents
# both paths resolve to the same 10319-byte file (1:1 mount, so the link
# resolves the same inside and outside the container)

docker exec framework sh -lc 'cd /app && python -m pytest tests/test_agent_catalog.py -q'
# 11 passed in 2.43s

# full suite, SQLite (.env moved aside so the run reproduces CI)
docker exec framework sh -lc 'cd /app && mv .env /tmp/env.bak; python -m pytest tests -q; mv /tmp/env.bak .env'
# 2076 passed, 68 skipped in 156.88s

docker exec framework sh -lc 'cd /app && ruff check engine'
# All checks passed!
cd data && python tools/check_engine_boundary.py
# ENGINE_BOUNDARY_NEW_FINDINGS 0
cd data && python3 ../.agents/rules/lint_language.py --config language-standard.toml
# Language standard: clean.
```

## Follow-ups

None. `data/.gitignore` was deliberately not changed: the `data/.claude` symlink
is tracked instead, matching the workspace root. What `agent:install` *writes*
is a separate queued task (`p2-20261007-085101`).
