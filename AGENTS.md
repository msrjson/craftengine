# Craft Engine workspace instructions

The running application is `data/`. Read `data/AGENTS.md` before changing its
code. The workspace root holds orchestration files and is not mounted into the
application container. Preserve the existing Git worktree changes.

Do not run destructive database commands or physical deletes in any
environment. Read `.agents/rules/database_safety.md` before database work.

## Agents talk through files

Claude, Gemini, Qwen and the local worker share no memory. Work passes between
them only through files in this repository: the backlog queue says what to do,
a handoff in `.claude/handoffs/` says where someone stopped, and the `team` bus
carries live notes. Read [`handoff.md`](handoff.md) before handing work to
another agent or picking up someone else's.

## Backlog queue - mandatory

All open work is a task file under `backlog/`. Before creating, picking,
claiming, editing or closing a task, read `.claude/rules/BACKLOG_QUEUE_STANDARD.md`
(the rules, BQ-01 to BQ-11) and `backlog/README.md` (the procedure). In short:
the directory is the state; every file is named and stamped with its UTC
creation time; History is append-only; tasks are never deleted or renamed;
claim only by `mv` into `processing/`; execute only `autonomous: true` with
`blocked_by: none`; close only with evidence. The gate
`python3 .claude/rules/lint_backlog.py` must exit 0; it runs as a Claude hook
and as the Git `pre-commit` (`git config core.hooksPath .githooks` once per
clone). Never bypass it.
