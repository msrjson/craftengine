---
id: "20261005-095523"
title: Extension lifecycle, dependencies and fault isolation (circuit breaker)
type: feature
priority: 2
autonomous: true
blocked_by: none
max_attempts: 2
attempts: 0
created_at: 2026-10-05T09:55:23Z
updated_at: 2026-10-05T09:55:23Z
source: owner request 2026-10-05: extension model (modules, plugins, themes) with fault isolation and a management panel; plan approved in session
touches:
  - data/engine/extensions/
  - data/engine/cli/
  - data/tests/
---

## Problem

A failing extension can break the application, disabling a plugin leaves its hooks running until restart, and there is no install/activate/deactivate/uninstall lifecycle nor dependency check.

## Evidence

- `docs/adr/0003-engine-boundary-and-internal-proxy.md` promises modules, plugins and themes that come and go without touching the engine; the code does not deliver it yet.

## Done when

- [ ] install / activate / deactivate / uninstall; uninstall never deletes data (NR-02).
- [ ] Activation refuses missing or incompatible dependencies and an engine outside the declared range; deactivation refuses while an active dependent exists.
- [ ] A boot failure marks only that extension `failed`; the application keeps serving.
- [ ] Every contribution (listener, filter, route, proxy exposure) is undone on deactivate without a restart.
- [ ] Per-extension circuit breaker: repeated runtime failures mark the extension unavailable for a cooldown; status visible in `extension status`.
- [ ] CLI `extension list|status|sync|install|activate|deactivate|uninstall`.

## Verify

```bash
docker exec framework sh -lc 'cd /app && python -m pytest tests -q'
docker exec framework sh -lc 'cd /app && ruff check engine'
cd data && python tools/check_engine_boundary.py
python .claude/rules/lint_language.py --config data/language-standard.toml
```

## Notes

Slice 2 of 10 of the extension model. Owner rulings 2026-10-05: one manifest with three kinds; extensions under `data/app/{modules,plugins,themes}/`; the whole model in one delivery; an extension failing must never take the application down; a low-friction management panel. Architecture is not delegable to the local model.

## History

- 2026-10-05T09:55:23Z created by claude@claude-code (source: owner request 2026-10-05)
