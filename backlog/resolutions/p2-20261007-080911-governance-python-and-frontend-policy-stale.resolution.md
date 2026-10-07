---
task: p2-20261007-080911-governance-python-and-frontend-policy-stale
outcome: resolved
agent: qwen@qwen-code (Qwen Code, local Ollama)
started_at: 2026-10-07T08:10:00Z
finished_at: 2026-10-07T08:20:00Z
commits: []
---

## What changed

`data/documentation/governance.md` §5, three lines:

- Backend runtime floor corrected from "Python (3.10+)" to "Python (3.14+)",
  matching `data/pyproject.toml:12` (`requires-python = ">=3.14"`).
- Typing line no longer claims "`mypy` compliant" as a build requirement; it
  now states what ships (type annotations and PEP 8 via `ruff`, no mypy
  configuration in the repository).
- Frontend rule rewritten to the owner ruling of 2026-09-17 (`AGENTS.md`
  §0.4): JS/TypeScript, React and a Node-based build are permitted for the UI,
  with the boundary preserved (no business rule, no Node serving requests,
  static built output, tooling out of the production image). The previous
  "Zero TypeScript" / "zero Node.js build pipelines" prohibition is gone.

## Verification

```
grep -n '3\.10+\|Zero TypeScript\|zero Node' data/documentation/governance.md
# OK: none
cd data && python3 ../.claude/rules/lint_language.py --config language-standard.toml
# Language standard: clean. (exit 0)
```

Documentation only; no code changed, pytest not run.

## Follow-ups

None.
