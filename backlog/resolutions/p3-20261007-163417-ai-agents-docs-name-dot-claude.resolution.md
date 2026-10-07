---
task: p3-20261007-163417-ai-agents-docs-name-dot-claude
outcome: resolved
agent: qwen@qwen-code (Qwen Code, local Ollama)
started_at: 2026-10-07T18:29:23Z
finished_at: 2026-10-07T18:29:40Z
---

## What changed

- `data/documentation/ai_agents.md`: the "AI Ready" bullets, the "generates or
  refreshes" list and the catalog layer table now name `.agents/...`, and a
  sentence states that `.agents/` is the single physical agent directory with
  `.claude` a symlink to it.
- `data/documentation/cli.md`: the `agent:scaffold` row says the catalog is
  installed into `.agents/`.

Docs only; no code or CHANGELOG change is needed.

## Verification

```bash
grep -rn '\.claude' data/documentation/ai_agents.md data/documentation/cli.md
# data/documentation/ai_agents.md:41:`.agents/` is the single physical agent directory; `.claude` is a symlink to it,
# (only the deliberate symlink mention remains)

python3 .agents/rules/lint_backlog.py && python3 .agents/rules/lint_board.py
# clean
```

## Follow-ups

None.
