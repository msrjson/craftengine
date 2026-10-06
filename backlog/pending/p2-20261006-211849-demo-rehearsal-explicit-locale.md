---
id: "20261006-211849"
title: Make the CRM translation test locale explicit
type: bugfix
priority: 2
autonomous: true
blocked_by: none
max_attempts: 2
attempts: 0
created_at: 2026-10-06T21:18:49Z
updated_at: 2026-10-06T21:18:49Z
source: Framework 4.7.0 release rehearsal
touches:
  - data-demo/tests/test_extension_matrix.py
---

## Problem

The translation plural test assumes Portuguese while the rehearsal starts from the English example environment.

## Evidence

- `data-demo/.env.example:5` sets APP_LOCALE=en.
- `data-demo/tests/test_extension_matrix.py:194` expects Portuguese without selecting a locale.
- `.claude/scripts/rehearse-demo.sh:32` copies the example environment; default run returned 54 passed and 1 failed.

## Done when

- [ ] The translation test explicitly selects and restores its intended locale.
- [ ] Default release rehearsal passes SQLite and PostgreSQL without environment adjustment.

## Verify

```bash
sh .claude/scripts/rehearse-demo.sh
```

## Notes

Finding belongs to the demo context; framework release work must not edit demo sources. A temporary rehearsal script setting APP_LOCALE=pt-BR can verify candidate compatibility independently.

## History

- 2026-10-06T21:18:49Z created by gpt@codex (release rehearsal finding for demo context)
