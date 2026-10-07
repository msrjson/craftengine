---
id: "20261007-163417"
title: The ai_agents and cli docs still name `.claude/` for the agent catalog
type: chore
priority: 3
autonomous: true
blocked_by: none
max_attempts: 2
attempts: 0
created_at: 2026-10-07T16:34:17Z
updated_at: 2026-10-07T16:34:17Z
source: found while closing p2-20261007-085101 (these docs sit outside its touches)
touches:
  - data/documentation/ai_agents.md
  - data/documentation/cli.md
---

## Problem

The agent catalog now installs into `.agents/` (the single physical agent
directory) with `.claude` a symlink to it, but the hand-written documentation
still describes the catalog as living under `.claude/...`. A reader follows the
docs to the wrong physical directory.

## Evidence

- `data/documentation/ai_agents.md:35-38` — `.claude/rules/AGENTS.md`,
  `.claude/skills/`, `.claude/agents/`, `.claude/commands/`.
- `data/documentation/ai_agents.md:51-52,73-77` — the same paths again in the
  catalog tables.
- `data/documentation/cli.md:168` — "install the whole agent catalog into
  `.claude/`".

## Done when

- [ ] Both docs name `.agents/...` as the catalog location and describe `.claude`
      as a symlink to it, not a second directory.
- [ ] No `.claude/` remains except a deliberate mention of the symlink.

## Verify

```bash
grep -rn '\.claude' data/documentation/ai_agents.md data/documentation/cli.md
# only intentional symlink mentions remain
```

## Notes

The generated `llms.txt` files (project root and `documentation/`) were already
aligned to `.agents/` in `p2-20261007-085101`, because they are output of the
scaffolder that the same task changed.

## History

- 2026-10-07T16:34:17Z created by qwen@qwen-code (source: found while closing p2-20261007-085101; docs outside its touches)
