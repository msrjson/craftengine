---
task: p2-20261007-083002-ai-driver-falls-back-to-mock-in-silence
outcome: resolved
agent: qwen@qwen-code (Qwen Code, local Ollama)
started_at: 2026-10-07T08:35:00Z
finished_at: 2026-10-07T08:45:00Z
commits: []
---

## What changed

- `data/engine/ai/manager.py` - `driver()` no longer falls back to
  `MockAIDriver` for an unknown name. It raises
  `MisconfigurationError("AI_DRIVER_UNKNOWN", name=..., drivers=...)`, naming the
  drivers the configuration declares. `AI.set_driver()` is unchanged, so a
  custom driver still registers.
- `data/engine/support/diagnostics.py` - the `AI_DRIVER_UNKNOWN` message joins
  the diagnostics catalog (the catalog is the engine's single source of
  developer-facing messages; `describe()` refuses an unknown code).
- `data/CRAFT_ENGINE.md` - the `ai/` row no longer lists Claude and Ollama as
  shipped drivers: it names the three that exist and points at `AI.set_driver`.
- `data/tests/test_ai_sdk.py` - `TestUnknownDriverIsRefused` pins the loud
  failure and the code.
- `data/CHANGELOG.md` - `[Unreleased] / Fixed` entry.

Scope note: `config/ai.py` keeps its `claude`/`ollama` blocks on purpose. They are
configuration for a driver an application may register through `AI.set_driver`;
the defect was the silent fallback, not the presence of the blocks. The
documentation that called those drivers built-in was wrong and is now fixed.

## Verification

```
docker exec framework sh -lc 'cd /app && python -m pytest tests/test_ai_sdk.py -q'
# 6 passed

docker exec -e CRAFT_TEST_DB=pgsql -e DB_SSLMODE=disable -e DB_HOST=db -e DB_PORT=5499 \
  -e DB_DATABASE=craft_db -e DB_USERNAME=craft -e DB_PASSWORD=secretpassword \
  framework sh -lc 'cd /app && python -m pytest tests/test_ai_sdk.py -q'
# 6 passed

docker exec -e CRAFT_TEST_DB=pgsql ... framework sh -lc 'cd /app && python -m pytest tests -q'
# 2038 passed, 4 skipped

docker exec framework sh -lc 'cd /app && ruff check engine tests/test_ai_sdk.py'
# All checks passed!
```

## Follow-ups

None.
