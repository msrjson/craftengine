---
id: "20261007-085100"
title: data/ carries two agent directories, and its AGENTS.md still points at .claude/
type: chore
priority: 2
autonomous: true
blocked_by: none
max_attempts: 2
attempts: 1
claimed_by: qwen@qwen-code
created_at: 2026-10-07T08:51:00Z
updated_at: 2026-10-07T16:21:03Z
source: dead-code audit 2026-10-07 + owner ruling 2026-10-07 (.agents is the single physical directory)
touches:
  - data/.agents/
  - data/.claude
  - data/AGENTS.md
---

## Problem

The workspace root was migrated to `.agents/` (physical) with `.claude` a
symlink, but the framework context `data/` still has **two physical agent
directories** and its instructions point at the old one. The owner's ruling is
one physical directory per project, `.agents/`, with every tool path a symlink.

## Evidence

- `data/.claude/` - physical: `agents/`, `commands/`, `references/`, `rules/`,
  `skills/` (the catalog `agent:install` writes).
- `data/.agents/` - physical and separate: `mcp.json`, `rules/AGENTS.md`.
- Neither is a symlink to the other (`ls -la data/.claude data/.agents`).
- `data/AGENTS.md:73` - "Read `.claude/rules/AGENTS.md` when present ...";
  `:82` - "read `.claude/rules/BACKLOG_QUEUE_STANDARD.md`";
  `:88` - "`python3 .claude/rules/lint_backlog.py` must exit 0". Should read
  `.agents/...`.
- The workspace `.githooks/pre-commit` was already updated to `.agents/`; the
  in-container paths still say `.claude/`.

## Done when

- [ ] `data/` has one physical agent directory: `.agents/` holds the content and
      `.claude` is a symlink to it (or the two are reconciled the other way if a
      reason is recorded; the ruling prefers `.agents/`).
- [ ] `data/AGENTS.md` writes `.agents/...`.
- [ ] The container still works: `/app` is a 1:1 mount, so a symlink inside the
      tree must resolve the same inside and outside.

## Verify

```bash
ls -la data/.claude data/.agents
readlink data/.claude
grep -n '\.claude/' data/AGENTS.md
docker exec framework sh -lc 'cd /app && python -m pytest tests/test_agent_catalog.py -q'
```

## Notes

`data/` is mounted into the container as `/app`, so verify the symlink resolves
inside the container too. This task is about the physical layout; a change to
what the scaffolder writes is a separate task (the `agent:install` one).

## History

- 2026-10-07T08:51:00Z created by qwen@qwen-code (source: dead-code audit 2026-10-07 + owner ruling)
- 2026-10-07T16:20:51Z claimed by qwen@qwen-code (attempt 1)
- 2026-10-07T16:20:51Z scope note by qwen@qwen-code: data/.claude content moved into data/.agents (the 128-byte rules/AGENTS.md stub replaced by the real contract); data/.claude is now a relative symlink to .agents, tracked like the workspace root's; data/AGENTS.md writes .agents/...
- 2026-10-07T16:21:03Z resolved by qwen@qwen-code (resolutions/p2-20261007-085100-data-context-has-two-agent-directories.resolution.md)
