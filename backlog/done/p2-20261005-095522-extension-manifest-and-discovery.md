---
id: "20261005-095522"
title: Extension manifest, discovery and state store (ADR 0004)
type: feature
priority: 2
autonomous: true
blocked_by: none
max_attempts: 2
claimed_by: claude@claude-code
attempts: 1
created_at: 2026-10-05T09:55:22Z
updated_at: 2026-10-05T10:26:02Z
source: owner request 2026-10-05: extension model (modules, plugins, themes) with fault isolation and a management panel; plan approved in session
touches:
  - data/engine/extensions/
  - data/engine/plugins/
  - data/engine/modules/
  - data/engine/providers/
  - data/config/extensions.py
  - data/bootstrap/app.py
  - data/database/migrations/
  - data/app/plugins/
  - data/plugins/
  - docs/adr/0004-extension-model.md
  - data/tests/
---

## Problem

Extensions (modules, plugins, themes) have no manifest, no shared discovery and no shared state: `PluginManager` reads a `PLUGIN` dict from `data/plugins/`, `ModuleManager` only stores state, and `app/modules/`, `app/plugins/` are empty placeholders.

## Evidence

- `docs/adr/0003-engine-boundary-and-internal-proxy.md` promises modules, plugins and themes that come and go without touching the engine; the code does not deliver it yet.

## Done when

- [ ] `docs/adr/0004-extension-model.md` records the model: one manifest (`extension.toml`), three kinds, extensions under `data/app/{modules,plugins,themes}/`, isolation by contract + gate + per-extension error boundary.
- [ ] `engine/extensions/` parses and validates `extension.toml` (slug, kind, version, engine range, name_key, requires) with typed errors (`code` + `message_key`).
- [ ] Discovery roots come from config `extensions.paths` set by the application (the engine never names `app`).
- [ ] Forward-only migration creates `extensions` and copies existing `plugins` rows; `audit-log` moves to `data/app/plugins/audit_log/` with a manifest.
- [ ] `PluginManager` / `ModuleManager` keep their public API (NR-05).

## Verify

```bash
docker exec framework sh -lc 'cd /app && python -m pytest tests -q'
docker exec framework sh -lc 'cd /app && ruff check engine'
cd data && python tools/check_engine_boundary.py
python .claude/rules/lint_language.py --config data/language-standard.toml
```

## Notes

Slice 1 of 10 of the extension model. Owner rulings 2026-10-05: one manifest with three kinds; extensions under `data/app/{modules,plugins,themes}/`; the whole model in one delivery; an extension failing must never take the application down; a low-friction management panel. Architecture is not delegable to the local model.

## History

- 2026-10-05T09:55:22Z created by claude@claude-code (source: owner request 2026-10-05)
- 2026-10-05T09:56:03Z claimed by claude@claude-code (attempt 1)
- 2026-10-05T10:26:02Z resolved by claude@claude-code (resolutions/p2-20261005-095522-extension-manifest-and-discovery.resolution.md)
