---
id: "20261004-162631"
title: Make .agents/ the physical agent directory, with .claude as a symlink to it
type: chore
priority: 1
autonomous: false
blocked_by: owner-action
max_attempts: 2
attempts: 0
created_at: 2026-10-04T16:26:31Z
updated_at: 2026-10-04T16:26:31Z
source: owner ruling 2026-10-04 (the Craft Engine workspace is organized as .agents, for every tool)
touches:
  - .agents/
  - .claude
  - .gitignore
  - AGENTS.md
  - handoff.md
  - backlog/README.md
  - .githooks/pre-commit
---

## Problem

The owner ruled (2026-10-04) that this workspace keeps its agent material in a
vendor-neutral `.agents/` directory, used by every tool (Claude Code, Gemini
CLI, Antigravity, Codex, Cursor, Qwen Code), with `.claude` as a symlink to
it. Today the reverse holds: `.claude/` (34 MB, 82 tracked files) is the
real directory and `.agents/` (232 KB, 28 tracked files) is a second, partly
stale copy.

**Blocked on the owner:** the global rule `~/.claude/agent-team/AGENTS.md`
section 0.1 says `.claude/` is the single agent directory, and
`~/.local/bin/workspace-guard` (lines 5-6, `TOOL_DIRS` line 17) refuses
every write under `.agents/` unless `.agents` is a symlink to `.claude`.
Both live outside this workspace; agents cannot change them, and moving files
with the shell to get around the guard is not allowed.

## Evidence

Overlap of the two directories (2026-10-04):

| Path | State |
|---|---|
| `rules/AGENTS.md`, `rules/LANGUAGE_AND_I18N_STANDARD.md` | in both, **different** - reconcile, `.claude` copies are the newer |
| `rules/RELEASE_NON_REGRESSION_STANDARD.md` | in both, identical |
| `rules/CRAFT_ENGINE_CONSTITUTION.md`, `rules/database_safety.md`, `rules/ENGINEERING_GOVERNANCE.md` | only in `.agents` |
| `agents/` (codepy-architect, codepy-developer, codepy-tester, craft-data-guardian, README) | only in `.agents`; `.claude/agents/` has its own set |
| `skills/business`, `skills/framework`, `skills/project` | only in `.agents`; `.claude/skills/` has 26 entries |
| `docs/` (backlog, benchmarks 2026-08-07 and 2026-09-16, blueprint, vision...) | only in `.agents` |
| `plans/codepy_design_review.md`, `scripts/run_tests.{sh,ps1}` | only in `.agents` |
| `github/apijey.txt` | only in `.agents`; **a credential**, gitignored (`.gitignore:33`), never committed - must stay ignored |

`.claude/settings.json` hooks call `$CLAUDE_PROJECT_DIR/.claude/rules/*.py`;
they keep working through the symlink.

## Done when

- [ ] Owner: global rule 0.1 and `workspace-guard` allow a physical `.agents/` with `.claude -> .agents` for this workspace (or in general).
- [ ] Every `.claude/` entry lives under `.agents/`; each collision above reconciled (newer content kept, the other recorded in the commit message); nothing lost.
- [ ] `.claude` is a symlink to `.agents`; `.claude/settings.json`, hooks, skills and commands still load in Claude Code.
- [ ] `.gitignore` still ignores `.agents/github/` and `settings.local.json`; `git ls-files` shows no credential.
- [ ] Documentation paths (`AGENTS.md`, `handoff.md`, `backlog/README.md`, `.claude/rules/*.md`, `.githooks/pre-commit`) say `.agents/...`.
- [ ] `lint_backlog.py`, `lint_board.py`, `lint_language.py` exit 0; a board RULE line announces the move.

## Verify

```bash
test -d .agents && test -L .claude && readlink .claude
git ls-files .agents | grep -c . ; git ls-files | grep -i apijey || echo "no credential tracked"
python3 .agents/rules/lint_backlog.py && python3 .agents/rules/lint_board.py
```

## Notes

Order matters: reconcile the overlapping files first, then move, then link, in
one commit, while no other agent holds a CLAIM on `.claude/` or `.agents/`
(check the board). Destructive steps (removing the old copies) need the owner's
go-ahead (BQ-11).

## History

- 2026-10-04T16:26:31Z created by claude (source: owner ruling 2026-10-04)
