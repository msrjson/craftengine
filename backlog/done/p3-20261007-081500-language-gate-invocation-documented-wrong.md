---
id: "20261007-081500"
title: The documented language-gate command fails when run from the workspace root
type: chore
priority: 3
autonomous: true
blocked_by: none
max_attempts: 2
attempts: 1
claimed_by: qwen@qwen-code
created_at: 2026-10-07T08:15:00Z
updated_at: 2026-10-07T08:45:00Z
source: framework audit 2026-10-07 (running the gates)
touches:
  - AGENTS.md
---

## Problem

`AGENTS.md` (and its symlinks `QWEN.md`, `CLAUDE.md`, `GEMINI.md`,
`.cursorrules`) documents the language gate as
`python3 .claude/rules/lint_language.py --config language-standard.toml` with no
working directory. Run from the workspace root it finds no config and scans
everything, including `.claude/Project Reference/` and the framework's own
tools, reporting tens of thousands of violations. Run from `data/` it is clean.

## Evidence

- `ls language-standard.toml` at the workspace root: "No such file or
  directory"; the file that exists is `data/language-standard.toml`.
- From the root: `python3 .claude/rules/lint_language.py --config language-standard.toml`
  → `FAILED — 21811 violation(s)` (scans `.claude/Project Reference/...`).
- From `data/`: `python3 ../.claude/rules/lint_language.py --config language-standard.toml`
  → `Language standard: clean.` (exit 0).
- `python3 .claude/rules/lint_language.py --config .claude/rules/language-standard.toml`
  from the root → exit 2 (config does not match the root layout).

## Done when

- [ ] The gate table in `AGENTS.md` states the working directory, or the script
      resolves the project config regardless of the caller's directory.

## Verify

```bash
cd data && python3 ../.claude/rules/lint_language.py --config language-standard.toml   # exit 0
```

## Notes

`AGENTS.md` is the single instruction source for every agent, so editing it is a
governance change: it should be a deliberate, owner-approved commit, not a
drive-by fix inside another task. This task only records the divergence.
(`.claude/rules/lint_board.py` and `lint_backlog.py` do run correctly from the
root.)

## History

- 2026-10-07T08:15:00Z created by qwen@qwen-code (source: framework audit 2026-10-07)
- 2026-10-07T08:23:00Z owner ruling: correct every open gap (owner, relayed by qwen@qwen-code); autonomous set true, blocked_by cleared
- 2026-10-07T08:23:00Z claimed by qwen@qwen-code (attempt 1)
- 2026-10-07T08:45:00Z resolved by qwen@qwen-code (resolutions/p3-20261007-081500-language-gate-invocation-documented-wrong.resolution.md)
