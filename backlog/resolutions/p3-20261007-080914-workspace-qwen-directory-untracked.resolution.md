---
task: p3-20261007-080914-workspace-qwen-directory-untracked
outcome: resolved
agent: qwen@qwen-code (Qwen Code, local Ollama)
started_at: 2026-10-07T08:10:00Z
finished_at: 2026-10-07T08:20:00Z
commits: []
---

## What changed

- `.gitignore` — added a `.qwen/` entry under the tooling-caches block, with a
  comment pointing to `AGENTS.md` §0.1 (tool-owned content lives under
  `.claude/`). This is the minimal, reversible fix; the symlink option
  (`.qwen -> .claude`) stays with
  `backlog/pending/p1-20261004-162631-agents-directory-migration.md`.

## Verification

```
git status --short | grep -c '\.qwen/'    # 0
```

`git status --short` after the change lists only the intended task/documentation
files, no `.qwen/`.

## Follow-ups

None. The broader agent-directory consolidation remains
`p1-20261004-162631-agents-directory-migration`.
