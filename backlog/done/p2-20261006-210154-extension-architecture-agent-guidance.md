---
id: "20261006-210154"
title: Align application agent routing instructions with the extension model
type: chore
priority: 2
autonomous: true
blocked_by: none
max_attempts: 2
attempts: 1
claimed_by: gpt@codex
created_at: 2026-10-06T21:01:54Z
updated_at: 2026-10-06T21:03:16Z
source: owner-authorized architecture correction and documentation
touches:
  - data/AGENTS.md
---

## Problem

Application instructions describe all project routes as global route files, omitting the supported extension route contract.

## Evidence

- `data/AGENTS.md:34`: every application route is said to live in routes/web.py or routes/api.py.
- `data/engine/extensions/loader.py:106`: extension routes.py registers and owns routes.

## Done when

- [x] Routing guidance recognizes extension routes and points to the architecture contract.
- [x] New code uses ExtensionManager, not legacy module/plugin state stores.

## Verify

```bash
(cd data && python3 ../.claude/rules/lint_language.py AGENTS.md documentation/architecture.md --config language-standard.toml)
python3 .claude/rules/lint_backlog.py
python3 .claude/rules/lint_board.py
```

## Notes

Documentation only; root AGENTS.md and its tool symlinks remain the workspace instruction source.

## History

- 2026-10-06T21:01:54Z created by gpt@codex (owner-authorized documentation)
- 2026-10-06T21:01:54Z claimed by gpt@codex (attempt 1)
- 2026-10-06T21:03:16Z resolved by gpt@codex (backlog/resolutions/p2-20261006-210154-extension-architecture-agent-guidance.resolution.md)
