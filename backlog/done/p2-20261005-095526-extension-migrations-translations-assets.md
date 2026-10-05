---
id: "20261005-095526"
title: Per-extension migrations, translations and assets
type: feature
priority: 2
autonomous: true
blocked_by: none
max_attempts: 2
claimed_by: claude@claude-code
attempts: 1
created_at: 2026-10-05T09:55:26Z
updated_at: 2026-10-05T10:26:02Z
source: owner request 2026-10-05: extension model (modules, plugins, themes) with fault isolation and a management panel; plan approved in session
touches:
  - data/engine/migrations/
  - data/engine/extensions/
  - data/engine/view/forge.py
  - data/tests/
---

## Problem

Migrations, translations and static assets are global; an extension cannot carry its own.

## Evidence

- `docs/adr/0003-engine-boundary-and-internal-proxy.md` promises modules, plugins and themes that come and go without touching the engine; the code does not deliver it yet.

## Done when

- [ ] `install` runs the extension's `migrations/` (forward-only); `migrate` includes installed extensions; name collisions fail.
- [ ] `lang/catalog.json` is seeded on install; keys must start with the slug and have en, pt-BR and es.
- [ ] Assets served under `/extensions/<slug>/` only while the extension is active; `asset('slug::path')` in Forge.

## Verify

```bash
docker exec framework sh -lc 'cd /app && python -m pytest tests -q'
docker exec framework sh -lc 'cd /app && ruff check engine'
cd data && python tools/check_engine_boundary.py
python .claude/rules/lint_language.py --config data/language-standard.toml
```

## Notes

Slice 5 of 10 of the extension model. Owner rulings 2026-10-05: one manifest with three kinds; extensions under `data/app/{modules,plugins,themes}/`; the whole model in one delivery; an extension failing must never take the application down; a low-friction management panel. Architecture is not delegable to the local model.

## History

- 2026-10-05T09:55:26Z created by claude@claude-code (source: owner request 2026-10-05)
- 2026-10-05T10:26:02Z claimed by claude@claude-code (attempt 1)
- 2026-10-05T10:26:02Z resolved by claude@claude-code (resolutions/p2-20261005-095526-extension-migrations-translations-assets.resolution.md)
