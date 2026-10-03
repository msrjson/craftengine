---
id: "20261003-223124"
title: Decide how the two language gates treat engine/
type: decision
priority: 2
autonomous: false
blocked_by: owner-decision
max_attempts: 2
attempts: 0
created_at: 2026-10-03T22:31:24Z
updated_at: 2026-10-03T22:31:24Z
source: docs/backlog.md L3
touches: []
---

## Problem

The global hook reproves any `engine/` file it touches for pre-existing violations, while `data/language-standard.toml` scopes `engine/` out with a measured backlog of 252 violations. Every engine edit is flagged for violations it did not introduce.

## Evidence

- `data/engine/cli/app.py`: 84 violations under the global gate (78 LANG-C console sentences, 6 LANG-A), measured 2026-09-25.
- `data/language-standard.toml` already exempts `tools/lint_language.py`.

## Done when

- [ ] The owner chose one: exempt engineer-facing CLI output, migrate the 252 violations to `engine/support/diagnostics.py`, or make the hook read the project's toml.
- [ ] If "migrate" is chosen, an implementation task with `autonomous: true` is created and linked here.

## Verify

```bash
python .claude/rules/lint_language.py --config data/language-standard.toml
```

## Notes

The pattern that passes both gates already exists: developer messages in `engine/support/diagnostics.py` (code -> template), exceptions with a code and params.

## History

- 2026-10-03T22:31:24Z created by claude (source: docs/backlog.md L3; migrated from the single-file backlog)
