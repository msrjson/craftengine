---
id: "20261007-080914"
title: The Qwen Code .qwen/ directory is untracked and not ignored
type: chore
priority: 3
autonomous: true
blocked_by: none
max_attempts: 2
attempts: 1
claimed_by: qwen@qwen-code
created_at: 2026-10-07T08:09:14Z
updated_at: 2026-10-07T08:20:00Z
source: workspace inspection 2026-10-07
touches:
  - .gitignore
---

## Problem

`git status` reports `?? .qwen/` in the workspace root. The global owner rule
(`AGENTS.md` §0.1) says tool-owned content inside a project lives under
`.claude/` — when a tool insists on its own path, that path is a symlink to
`.claude`. The file is currently neither tracked, ignored, nor a symlink, so it
pollutes every `git status` and risks being committed by accident.

## Evidence

- `git status --short` → `?? .qwen/`; the directory holds `.qwen/settings.json`.
- `.gitignore` has no `.qwen/` entry (it ignores `.do/`, `.agents/github/`,
  `.github/`, `data-website/`, `data-demo/`).

## Done when

- [ ] `.qwen/` no longer appears as untracked in `git status`, and the chosen
      policy (ignore vs. symlink to `.claude/`) is written down.

## Verify

```bash
git status --short | grep -c '\.qwen/'   # expect 0
```

## Notes

The full consolidation of the agent directories is tracked separately by
`backlog/pending/p1-20261004-162631-agents-directory-migration.md`; this task
only ends the untracked-file noise. Ignoring is the minimal, reversible fix;
symlinking `.qwen -> .claude` is the option the global rule prefers but it
changes what the tool writes into `.claude/`, so it belongs to that migration
task if chosen.

## History

- 2026-10-07T08:09:14Z created by qwen@qwen-code (source: workspace inspection 2026-10-07)
- 2026-10-07T08:10:00Z claimed by qwen@qwen-code (attempt 1)
- 2026-10-07T08:20:00Z resolved by qwen@qwen-code (resolutions/p3-20261007-080914-workspace-qwen-directory-untracked.resolution.md)
