---
id: "20261005-095525"
title: Namespaced views and the theme override chain
type: feature
priority: 2
autonomous: true
blocked_by: none
max_attempts: 2
claimed_by: claude@claude-code
attempts: 1
created_at: 2026-10-05T09:55:25Z
updated_at: 2026-10-05T10:26:02Z
source: owner request 2026-10-05: extension model (modules, plugins, themes) with fault isolation and a management panel; plan approved in session
touches:
  - data/engine/view/
  - data/engine/extensions/
  - data/tests/
---

## Problem

Forge loads only `resources/views`; extensions cannot ship views and there is no theme seam (ADR 0003 promises one).

## Evidence

- `docs/adr/0003-engine-boundary-and-internal-proxy.md` promises modules, plugins and themes that come and go without touching the engine; the code does not deliver it yet.

## Done when

- [ ] `slug::path.view` resolves to the extension's `views/`.
- [ ] Resolution order: active theme, then extension, then `resources/views`; `@extends`/`@include` follow the same chain.
- [ ] The theme comes from config `view.theme` or a resolver the application registers; the engine never resolves a tenant.

## Verify

```bash
docker exec framework sh -lc 'cd /app && python -m pytest tests -q'
docker exec framework sh -lc 'cd /app && ruff check engine'
cd data && python tools/check_engine_boundary.py
python .claude/rules/lint_language.py --config data/language-standard.toml
```

## Notes

Slice 4 of 10 of the extension model. Owner rulings 2026-10-05: one manifest with three kinds; extensions under `data/app/{modules,plugins,themes}/`; the whole model in one delivery; an extension failing must never take the application down; a low-friction management panel. Architecture is not delegable to the local model.

## History

- 2026-10-05T09:55:25Z created by claude@claude-code (source: owner request 2026-10-05)
- 2026-10-05T10:26:02Z claimed by claude@claude-code (attempt 1)
- 2026-10-05T10:26:02Z resolved by claude@claude-code (resolutions/p2-20261005-095525-extension-views-and-themes.resolution.md)
