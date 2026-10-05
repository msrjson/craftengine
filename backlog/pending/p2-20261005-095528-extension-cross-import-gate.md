---
id: "20261005-095528"
title: Boundary gate: an extension never imports another extension
type: feature
priority: 2
autonomous: true
blocked_by: none
max_attempts: 2
attempts: 0
created_at: 2026-10-05T09:55:28Z
updated_at: 2026-10-05T09:55:28Z
source: owner request 2026-10-05: extension model (modules, plugins, themes) with fault isolation and a management panel; plan approved in session
touches:
  - data/tools/check_engine_boundary.py
  - data/tools/engine-boundary-policy.json
  - data/tests/test_engine_boundary.py
---

## Problem

Nothing stops `app/modules/a` from importing `app/modules/b`, which defeats isolation.

## Evidence

- `docs/adr/0003-engine-boundary-and-internal-proxy.md` promises modules, plugins and themes that come and go without touching the engine; the code does not deliver it yet.

## Done when

- [ ] New rule `EXTENSION_CROSS_IMPORT` (static and literal dynamic imports), mirrored in `tests/test_engine_boundary.py`.
- [ ] The ratchet base does not advance.

## Verify

```bash
docker exec framework sh -lc 'cd /app && python -m pytest tests -q'
docker exec framework sh -lc 'cd /app && ruff check engine'
cd data && python tools/check_engine_boundary.py
python .claude/rules/lint_language.py --config data/language-standard.toml
```

## Notes

Slice 7 of 10 of the extension model. Owner rulings 2026-10-05: one manifest with three kinds; extensions under `data/app/{modules,plugins,themes}/`; the whole model in one delivery; an extension failing must never take the application down; a low-friction management panel. Architecture is not delegable to the local model.

## History

- 2026-10-05T09:55:28Z created by claude@claude-code (source: owner request 2026-10-05)
