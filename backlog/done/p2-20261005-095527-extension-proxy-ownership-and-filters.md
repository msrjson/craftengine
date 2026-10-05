---
id: "20261005-095527"
title: Proxy exposures owned by extensions, prioritized listeners and filters
type: feature
priority: 2
autonomous: true
blocked_by: none
max_attempts: 2
claimed_by: claude@claude-code
attempts: 1
created_at: 2026-10-05T09:55:27Z
updated_at: 2026-10-05T10:26:02Z
source: owner request 2026-10-05: extension model (modules, plugins, themes) with fault isolation and a management panel; plan approved in session
touches:
  - data/engine/container/internal_proxy.py
  - data/engine/events/dispatcher.py
  - data/engine/extensions/
  - data/tests/
---

## Problem

Proxy exposures are not tied to an extension, so a disabled module stays callable; events have no priority and no value filters.

## Evidence

- `docs/adr/0003-engine-boundary-and-internal-proxy.md` promises modules, plugins and themes that come and go without touching the engine; the code does not deliver it yet.

## Done when

- [ ] `expose(..., owner=slug)`; calling an unavailable owner raises `INTERNAL_TARGET_UNAVAILABLE` without running it; deactivate removes the exposure.
- [ ] Unexpected exceptions from a target count toward the owner's circuit breaker; typed domain errors (status < 500) do not.
- [ ] `listen(..., priority=)`, `add_filter` / `apply_filters` / `remove_filter`, `remove_listener`.

## Verify

```bash
docker exec framework sh -lc 'cd /app && python -m pytest tests -q'
docker exec framework sh -lc 'cd /app && ruff check engine'
cd data && python tools/check_engine_boundary.py
python .claude/rules/lint_language.py --config data/language-standard.toml
```

## Notes

Slice 6 of 10 of the extension model. Owner rulings 2026-10-05: one manifest with three kinds; extensions under `data/app/{modules,plugins,themes}/`; the whole model in one delivery; an extension failing must never take the application down; a low-friction management panel. Architecture is not delegable to the local model.

## History

- 2026-10-05T09:55:27Z created by claude@claude-code (source: owner request 2026-10-05)
- 2026-10-05T10:26:02Z claimed by claude@claude-code (attempt 1)
- 2026-10-05T10:26:02Z resolved by claude@claude-code (resolutions/p2-20261005-095527-extension-proxy-ownership-and-filters.resolution.md)
