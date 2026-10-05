---
task: p2-20261005-095524-extension-routes-and-providers
outcome: resolved
agent: claude@claude-code
started_at: 2026-10-05T09:56:03Z
finished_at: 2026-10-05T10:26:02Z
---

## What changed

`ExtensionLoader` loads `provider.py` (`register(context)`) and `routes.py` (`register(router)`, every route tagged with the slug). Kernel: typed refusal from `ModuleManager.refusal` raised on the worker thread (404 `MODULE_DISABLED`, 503 `EXTENSION_UNAVAILABLE`), route failures reported to the breaker; exception payloads carry `message_key` (< 500 and 503).

Commits: `569edd5` (ADR 0004 and queue), `9352e47` (implementation, tests, docs, CHANGELOG).

## Verification

```bash
docker exec framework sh -lc 'cd /app && python -m pytest tests/test_extensions.py -q'          # 43 passed
docker exec framework sh -lc 'cd /app && python -m pytest tests/test_engine_boundary.py -q'     # 35 passed
docker exec framework sh -lc 'cd /app && python -m pytest tests -q'                             # 1840 passed, 66 skipped (baseline before the change: 1784 passed, 66 skipped)
docker exec framework sh -lc 'cd /app && ruff check engine tests tools'                         # All checks passed!
cd data && python tools/check_engine_boundary.py                                                # ENGINE_BOUNDARY_NEW_FINDINGS 0
python .claude/rules/lint_language.py --config data/language-standard.toml                      # Language standard: clean.
python .claude/rules/lint_language.py --config data/language-standard.views.toml                # Language standard: clean.
```

PostgreSQL: UNVERIFIED locally - `documentation/testing.md` forbids running the suite against a persistent server; the CI matrix (SQLite + PostgreSQL) runs it on push.
