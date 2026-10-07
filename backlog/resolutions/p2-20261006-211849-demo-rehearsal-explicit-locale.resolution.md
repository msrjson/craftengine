---
task: p2-20261006-211849-demo-rehearsal-explicit-locale
outcome: resolved
agent: qwen@qwen-code (local Ollama)
started_at: 2026-10-07T18:46:46Z
finished_at: 2026-10-07T18:48:20Z
commits: [99c5755 (data-demo)]
---

## What changed

- `data-demo/tests/test_extension_matrix.py`: the plural test now selects its
  locale explicitly (`current_locale.set("pt-BR")` around the two renders,
  restored in a `finally`) and imports `current_locale` from
  `craft.support.translation`, so the assertion no longer depends on
  `APP_LOCALE`. No production code changed.

## Verification

- `docker exec -e APP_LOCALE=en craftengine-demo sh -lc 'cd /app && python -m pytest tests/test_extension_matrix.py -q'`
  -> **27 passed** (red before the fix: `1 failed, 26 passed`).
- `docker exec craftengine-demo sh -lc 'cd /app && python -m pytest tests/test_extension_matrix.py -q'`
  -> **27 passed**.
- `sh .agents/scripts/rehearse-demo.sh` (engine 4.7.0 r00027) ->
  SQLite **55 passed**, disposable PostgreSQL 18 **55 passed**.

## Follow-ups

- none. The `export APP_LOCALE=pt-BR` line the rehearsal script carries is now
  redundant for this test but harmless; removing it is out of this task's
  `touches`.
