---
id: "20261005-095524"
title: Extension routes and providers, typed unavailable responses
type: feature
priority: 2
autonomous: true
blocked_by: none
max_attempts: 2
claimed_by: claude@claude-code
attempts: 1
created_at: 2026-10-05T09:55:24Z
updated_at: 2026-10-05T10:26:02Z
source: owner request 2026-10-05: extension model (modules, plugins, themes) with fault isolation and a management panel; plan approved in session
touches:
  - data/engine/extensions/
  - data/engine/http/kernel.py
  - data/engine/modules/
  - data/database/migrations/
  - data/tests/
---

## Problem

Extensions cannot contribute routes or providers; a disabled or failing extension route has no typed response.

## Evidence

- `docs/adr/0003-engine-boundary-and-internal-proxy.md` promises modules, plugins and themes that come and go without touching the engine; the code does not deliver it yet.

## Done when

- [ ] `routes.py` exposing `register(router)` is loaded for active modules and plugins, every route tagged with the extension slug.
- [ ] A disabled extension answers 404 `MODULE_DISABLED`, an unavailable one 503 `EXTENSION_UNAVAILABLE`, both with `message_key` rows in en, pt-BR, es.
- [ ] A route failure is reported to the extension's circuit breaker.

## Verify

```bash
docker exec framework sh -lc 'cd /app && python -m pytest tests -q'
docker exec framework sh -lc 'cd /app && ruff check engine'
cd data && python tools/check_engine_boundary.py
python .claude/rules/lint_language.py --config data/language-standard.toml
```

## Notes

Slice 3 of 10 of the extension model. Owner rulings 2026-10-05: one manifest with three kinds; extensions under `data/app/{modules,plugins,themes}/`; the whole model in one delivery; an extension failing must never take the application down; a low-friction management panel. Architecture is not delegable to the local model.

## History

- 2026-10-05T09:55:24Z created by claude@claude-code (source: owner request 2026-10-05)
- 2026-10-05T10:26:02Z claimed by claude@claude-code (attempt 1)
- 2026-10-05T10:26:02Z resolved by claude@claude-code (resolutions/p2-20261005-095524-extension-routes-and-providers.resolution.md)
