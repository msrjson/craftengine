---
task: p2-20261005-095522-extension-manifest-and-discovery
outcome: resolved
agent: claude@claude-code
started_at: 2026-10-05T09:56:03Z
finished_at: 2026-10-05T10:26:02Z
---

## What changed

`docs/adr/0004-extension-model.md`; `engine/extensions/{manifest,versions,errors,store,manager}.py`; `config/extensions.py` (`extensions.paths` seam, the engine never names `app`); forward-only migration `2026_10_05_000001_create_extensions_table` with the extension messages in en, pt-BR, es. Deviation from the task, by owner ruling 2026-10-05 (data/ stays the slim framework): `audit-log` was NOT moved into `data/app/plugins/`; it moves with the demo (task crm-demo-on-extension-model). Legacy `plugins` rows are not copied into `extensions`: legacy plugins have no manifest and keep loading through `PluginManager` for one release (deprecated in CHANGELOG). `ModuleManager` keeps its API and defers to the extension manager.

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
