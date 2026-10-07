---
id: "20261007-083002"
title: An unknown AI driver falls back to mock in silence, and config advertises two drivers that do not exist
type: bugfix
priority: 2
autonomous: true
blocked_by: none
max_attempts: 2
attempts: 0
created_at: 2026-10-07T08:30:02Z
updated_at: 2026-10-07T08:45:00Z
source: framework audit 2026-10-07 (dead-code sweep)
touches:
  - data/engine/ai/manager.py
  - data/engine/support/diagnostics.py
  - data/CRAFT_ENGINE.md
  - data/tests/
  - data/CHANGELOG.md
---

## Problem

`AI_DEFAULT_DRIVER=claude` (or any name the manager does not know) silently
falls back to the mock driver. An application configured for a real provider
gets fabricated answers with no error - the exact "placebo" the framework's
rules forbid. `config/ai.py` also advertises `claude` and `ollama` blocks, but
no driver module for either exists, so the config promises what the engine
cannot do.

## Evidence

- `data/engine/ai/manager.py:54-62` - `driver()` handles `gemini`, `openai` and
  `mock`; every other name lands on the `MockAIDriver` branch.
- `data/config/ai.py:21-28` - `claude` (`ANTHROPIC_API_KEY`) and `ollama`
  (`OLLAMA_BASE_URL`) blocks are declared.
- No `data/engine/ai/drivers/claude.py` or `ollama.py`; `documentation/ai.md`
  does not mention either.
- Doctrine: "a promise the framework cannot keep is removed rather than faked"
  (`introduction.md`, "Nothing decorative").

## Done when

- [ ] An unknown driver name fails loudly (a typed configuration error naming
      the supported drivers) instead of returning the mock.
- [ ] `config/ai.py` (and its skeleton stub) either keep only the drivers that
      exist, or mark the others clearly as not implemented.
- [ ] A test pins the loud failure for an unknown driver.
- [ ] `data/CHANGELOG.md` entry in the same change.

## Verify

```bash
docker exec -e CRAFT_TEST_DB=pgsql -e DB_SSLMODE=disable -e DB_HOST=db -e DB_PORT=5499 \
  -e DB_DATABASE=craft_db -e DB_USERNAME=craft -e DB_PASSWORD=secretpassword \
  framework sh -lc 'cd /app && python -m pytest tests -q'
```

## History

- 2026-10-07T08:30:02Z created by qwen@qwen-code (source: dead-code sweep 2026-10-07)
- 2026-10-07T08:35:00Z scope corrected: no `engine/cli/skeleton/config/ai.py.stub` exists (verified); `data/engine/support/diagnostics.py` added, because `MisconfigurationError` requires a code in the diagnostics catalog
- 2026-10-07T08:35:00Z claimed by qwen@qwen-code (attempt 1)
- 2026-10-07T08:45:00Z resolved by qwen@qwen-code (resolutions/p2-20261007-083002-ai-driver-falls-back-to-mock-in-silence.resolution.md)
