---
task: p2-20261007-081351-language-standard-translator-functions-not-in-forge
outcome: resolved
agent: qwen@qwen-code (Qwen Code, local Ollama)
started_at: 2026-10-07T08:23:00Z
finished_at: 2026-10-07T08:45:00Z
commits: []
---

## What changed

`data/language-standard.toml` - `translator_functions` is now
`["__", "translate"]` instead of `["__", "translate", "trans", "t"]`. `trans`
and `t` are defined nowhere in the engine: the Forge environment registers `__`
(`engine/view/forge.py:493-495`) and `translate` exists in Python
(`engine/support/translation.py`). A view calling `{{ t('key') }}` used to pass
the gate and fail at render; now the gate stops authorising it.

- `data/CHANGELOG.md` - `[Unreleased] / Changed` entry.

## Verification

```
grep -rn '\btrans(\|\bt(' data/engine/view/ data/resources/ data/engine/cli/
# no match

cd data && python3 ../.claude/rules/lint_language.py --config language-standard.toml
# Language standard: clean.

docker exec framework sh -lc 'cd /app && ruff check engine'
# All checks passed!
```

## Follow-ups

Note for the record, not a defect: `data-website/src/` does use `{{ t('...') }}`,
but that is the **website's own Python build** (`data-website/build.py`), a
separate context with its own catalogs, not the Forge engine. The framework's
gate only walks `roots = ["config", "routes"]`, so this change cannot affect it.
If the website ever shares this config, its helper must be named `__`/`translate`
or the config must list it explicitly.
