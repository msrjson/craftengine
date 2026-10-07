---
task: p1-20261004-162631-agents-directory-migration
outcome: resolved
agent: qwen@qwen-code (Qwen Code, local Ollama)
started_at: 2026-10-07T08:42:00Z
finished_at: 2026-10-07T08:52:00Z
commits: []
---

## What changed

`.agents/` is now the physical agent directory of this workspace and `.claude`
is a symlink to it. Nothing was lost; every entry of `.claude/` lives in
`.agents/`, and the collisions were reconciled in `.claude`'s favour (it held
the newer copies; `.agents/docs/` and `.agents/github/` were kept).

Also aligned, outside the workspace but without which the migration could not
run (the owner lifted the block: "no global policy may forbid the author from
organizing the workspace"):

- `~/.claude/agent-team/AGENTS.md` section 0.1 — a project may use `.agents/` or
  `.claude/` as the physical directory; the other must be a symlink.
- `~/.claude/agent-team/bin/workspace-guard` — `.agents` removed from
  `TOOL_DIRS` (`.gemini`, `.qwen`, `.cursor` must still be symlinks). The
  "write only inside your own workspace" guard is untouched. Backups:
  `~/.claude/agent-team/AGENTS.md.bak-20261007-083532` and
  `bin/workspace-guard.bak-20261007-083532`.

Documentation updated to `.agents/...`: `AGENTS.md` (and the symlinks),
`handoff.md`, `backlog/README.md`, `.githooks/pre-commit`, `.agents/rules/*.md`.
`.gitignore` now ignores `.agents/Project Reference/` (moved with the tree),
`.agents/github/` and `settings.local.json`; no credential is tracked.

## Incident during the work

The owner reorganised the workspace by hand mid-session: the agent tree was
spread into the workspace root and `.agents/` was left empty. Recovered with two
backups (`/tmp/agents-migration-20261007-083545`, the pre-migration state, and
`/tmp/agents-manual-20261007-083932`, the manual state) plus the Git index. The
root duplicates were verified identical (`diff -rq`: 0 differences) before
removal, and `docs/backlog.md` — overwritten by the team copy — was restored
from `HEAD`.

## Verification

```bash
test -L .claude && readlink .claude              # .agents
find .agents -type f | wc -l                     # 1506
ls docs/                                         # adr  backlog.md  brand  reports
git status --short | grep -c 'apijey'            # 0 (credential untracked)
python3 .agents/rules/lint_backlog.py            # clean
python3 .agents/rules/lint_board.py              # clean
cd data && python3 ../.agents/rules/lint_language.py --config language-standard.toml   # clean
cd data && python3 tools/check_engine_boundary.py | tail -1                             # 0 new findings
```

Staged set: 79 renames (R100), 3 renamed-with-changes (R097), 3 modified
(`.agents/rules/*.md`, the sed), 3 deleted (`.claude/rules/*.md`), 1 added (the
`.claude` symlink). No engine code touched, so the pytest suite was not re-run
for this task.

## Follow-ups

None. The board carries a RULE line for the move.
