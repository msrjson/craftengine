---
task: p2-20261006-211953-rehearsal-default-locale
outcome: resolved
agent: gpt@codex
started_at: 2026-10-06T21:19:53Z
finished_at: 2026-10-06T21:21:06Z
commits: []
---

## What changed

Canonical rehearsal explicitly selects declared default pt-BR without changing any demo source or assertion. Original English environment failed one plural assertion; temporary adjusted run and final canonical run each passed 55 SQLite and 55 PostgreSQL tests.

## Verification

- Framework pytest SQLite and PostgreSQL commands from task: passed 1971 and 2033 tests respectively.
- `sh .claude/scripts/rehearse-demo.sh`: 55 passed on both databases, exit 0.
- `python3 .claude/rules/lint_backlog.py` and `python3 .claude/rules/lint_board.py`: clean.
- Package build, twine check, clean wheel import and craft new: passed.

## Follow-ups

Demo locale-independent test task remains pending. Publication result is recorded on the board after CI completion.
