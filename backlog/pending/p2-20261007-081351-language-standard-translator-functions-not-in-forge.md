---
id: "20261007-081351"
title: language-standard.toml authorises two translator functions the Forge engine does not define
type: chore
priority: 2
autonomous: false
blocked_by: owner-decision
max_attempts: 2
attempts: 0
created_at: 2026-10-07T08:13:51Z
updated_at: 2026-10-07T08:13:51Z
source: framework audit 2026-10-07 (views and i18n exploration)
touches:
  - data/language-standard.toml
---

## Problem

The language gate's `translator_functions` lists `t` and `trans`, but neither
exists in a template: a view that calls `{{ t('key') }}` passes the gate and
fails at render on an undefined name. The gate currently approves code that
cannot run.

## Evidence

- `data/language-standard.toml:75` — `translator_functions = ["__", "translate", "trans", "t"]`.
- `data/engine/view/forge.py:493-495` — the Forge environment registers only
  `__` (`from engine.support.collection import __ as translate`); `t` and `trans`
  are registered nowhere.
- `data/documentation/governance.md` §4 and `data/AGENTS.md` document `__()` as
  the canonical template helper.

## Done when

- [ ] Either `t`/`trans` become real template globals in the Forge engine, or
      the gate stops authorising names the runtime does not define — decided by
      the owner, then applied in a dedicated change and verified.

## Verify

```bash
grep -n 'translator_functions' data/language-standard.toml
cd data && python3 ../.claude/rules/lint_language.py --config language-standard.toml
```

## Notes

This file configures the language gate; changing it is a gate change and should
be its own owner-approved commit, never bundled into another task. Hence
`autonomous: false`.

## History

- 2026-10-07T08:13:51Z created by qwen@qwen-code (source: framework audit 2026-10-07)
