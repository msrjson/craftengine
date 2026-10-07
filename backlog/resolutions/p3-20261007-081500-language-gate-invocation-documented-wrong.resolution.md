---
task: p3-20261007-081500-language-gate-invocation-documented-wrong
outcome: resolved
agent: qwen@qwen-code (Qwen Code, local Ollama)
started_at: 2026-10-07T08:23:00Z
finished_at: 2026-10-07T08:45:00Z
commits: []
---

## What changed

`AGENTS.md` (the single instruction source; `QWEN.md`, `CLAUDE.md`, `GEMINI.md`
and `.cursorrules` are symlinks to it) - the Gates table now states the working
directory for the language gate, matching the boundary gate's style:

```
| `cd data && python3 ../.claude/rules/lint_language.py --config language-standard.toml` | English code, no hardcoded copy | Claude hook, CI |
```

The config lives at `data/language-standard.toml`; run from the workspace root
with a bare `--config language-standard.toml`, the script finds no config and
scans the whole workspace (21116 violations, including `.claude/Project
Reference/`).

## Verification

```
cd data && python3 ../.claude/rules/lint_language.py --config language-standard.toml
# Language standard: clean.   (exit 0)

python3 .claude/rules/lint_backlog.py   # clean
python3 .claude/rules/lint_board.py     # clean
```

## Follow-ups

The log and board gates do run correctly from the workspace root; only the
language gate needed the directory. No further task.
