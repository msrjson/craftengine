---
id: "20261005-095529"
title: Scaffolding: make:module, make:plugin, make:theme, make:screen
type: feature
priority: 2
autonomous: true
blocked_by: none
max_attempts: 2
attempts: 0
created_at: 2026-10-05T09:55:29Z
updated_at: 2026-10-05T09:55:29Z
source: owner request 2026-10-05: extension model (modules, plugins, themes) with fault isolation and a management panel; plan approved in session
touches:
  - data/engine/cli/
  - data/tests/
---

## Problem

Agents have no generator for an isolated extension or a screen inside one.

## Evidence

- `docs/adr/0003-engine-boundary-and-internal-proxy.md` promises modules, plugins and themes that come and go without touching the engine; the code does not deliver it yet.

## Done when

- [ ] `make:module`, `make:plugin`, `make:theme` write a complete extension that installs and activates.
- [ ] `make:screen <slug> <screen>` writes a thin controller, a namespaced view, the route and three-locale keys.
- [ ] Generated code passes the language gate.

## Verify

```bash
docker exec framework sh -lc 'cd /app && python -m pytest tests -q'
docker exec framework sh -lc 'cd /app && ruff check engine'
cd data && python tools/check_engine_boundary.py
python .claude/rules/lint_language.py --config data/language-standard.toml
```

## Notes

Slice 8 of 10 of the extension model. Owner rulings 2026-10-05: one manifest with three kinds; extensions under `data/app/{modules,plugins,themes}/`; the whole model in one delivery; an extension failing must never take the application down; a low-friction management panel. Architecture is not delegable to the local model.

## History

- 2026-10-05T09:55:29Z created by claude@claude-code (source: owner request 2026-10-05)
