---
task: p2-20261006-210154-extension-architecture-agent-guidance
outcome: resolved
agent: gpt@codex
started_at: 2026-10-06T21:01:54Z
finished_at: 2026-10-06T21:03:16Z
commits: []
---

## What changed

- Updated data/AGENTS.md to recognize extension-owned routes.py alongside application-wide route files.
- Linked the architecture and extension contracts and clarified that new extensions use ExtensionManager and the extensions table.
- Root instruction symlinks were not altered.

## Verification

- `(cd data && python3 ../.claude/rules/lint_language.py AGENTS.md documentation/architecture.md --config language-standard.toml)`: clean.
- Backlog and board gates and `git diff --check`: clean.

## Follow-ups

None for this framework correction. The pre-existing application-owned CRM/extension-panel task remains with its claimant; no demo or website work was performed.
