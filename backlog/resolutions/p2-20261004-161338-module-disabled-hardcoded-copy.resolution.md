---
task: p2-20261004-161338-module-disabled-hardcoded-copy
outcome: resolved
agent: claude@claude-code
started_at: 2026-10-05T09:56:03Z
finished_at: 2026-10-05T10:26:03Z
---

## What changed

Fixed with the extension model: a disabled module route answers 404 `{"code": "MODULE_DISABLED", "message_key": "module.error.disabled"}` through the exception handler; the key is seeded in en, pt-BR and es by `2026_10_05_000001_create_extensions_table`. Tests: `TestLegacyModules` in `tests/test_extensions.py`.

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
