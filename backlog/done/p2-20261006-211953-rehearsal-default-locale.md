---
id: "20261006-211953"
title: Set the declared default locale in the release rehearsal
type: bugfix
priority: 2
autonomous: true
blocked_by: none
max_attempts: 2
attempts: 1
created_at: 2026-10-06T21:19:53Z
updated_at: 2026-10-06T21:21:06Z
claimed_by: gpt@codex
source: Release rehearsal and declared workspace default locale
touches:
  - .claude/scripts/rehearse-demo.sh
---

## Problem

Release rehearsal inherits English from the demo example instead of the declared Portuguese default.

## Evidence

- `.claude/rules/AGENTS.md:38` declares Portuguese as the default visitor locale.
- `.claude/scripts/rehearse-demo.sh:33` sets APP_URL without selecting the default locale.
- A temporary exact rehearsal with APP_LOCALE=pt-BR passed all 55 tests on each database; no assertion changed.

## Done when

- [ ] Canonical rehearsal explicitly selects APP_LOCALE=pt-BR and passes both databases.

## Verify

```bash
sh .claude/scripts/rehearse-demo.sh
python3 .claude/rules/lint_backlog.py
python3 .claude/rules/lint_board.py
```

## Notes

Keep demo sources and every assertion unchanged. The separate demo task makes its translation test independent of the example environment.

## History

- 2026-10-06T21:19:53Z created by gpt@codex (release rehearsal environment defect)
- 2026-10-06T21:19:53Z claimed by gpt@codex (attempt 1)
- 2026-10-06T21:21:06Z resolved by gpt@codex (resolutions/p2-20261006-211953-rehearsal-default-locale.resolution.md)
