---
task: p2-20261006-134846-engine-update-panel-and-check
outcome: resolved
agent: claude@claude-code
started_at: 2026-10-06T13:48:46Z
finished_at: 2026-10-06T13:57:46Z
---

## Summary

`EngineUpdates` (container key `engine_updates`, `LifecycleServiceProvider`)
caches the update notice and reviews and applies moves, with the verification
command taken from `craft-engine.lock` and one move at a time. New console
commands `engine check` and `engine verify-command`, and `adopt
--verify-command`. `make:engine-panel` (also run by `make:admin`) generates
`/admin/engine`, the alert partial, the translations (en, pt-BR, es) and the
routes. `PanelPage` carries the cached notice for admins only.

## Verification

- `docker exec framework sh -lc 'cd /app && python -m pytest tests/test_engine_updates.py -q'` -> 13 passed, including the HTTP journey on a generated project (check 302, alert shown after check, review 200, apply 200 with the pin rewritten, no CSRF 419, plain user 403, anonymous 302)
- `docker exec framework sh -lc 'cd /app && python -m pytest tests -q'` -> 1921 passed, 66 skipped (SQLite)
- `ruff check engine` -> All checks passed!; `dev.py docs check` -> 40 pages, no broken links
- `tools/lint_language.py` -> clean; `tools/check_engine_boundary.py` -> 0 new findings
- PostgreSQL: not run locally (documentation/testing.md forbids the full suite against a persistent server); the CI PostgreSQL job runs it on push. UNVERIFIED locally.
