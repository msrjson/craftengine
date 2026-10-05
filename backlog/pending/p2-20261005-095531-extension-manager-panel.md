---
id: "20261005-095531"
title: Extension manager panel (low-friction administration)
type: feature
priority: 2
autonomous: false
blocked_by: owner-decision
max_attempts: 2
attempts: 0
created_at: 2026-10-05T09:55:31Z
updated_at: 2026-10-05T10:01:15Z
source: owner request 2026-10-05: extension model (modules, plugins, themes) with fault isolation and a management panel; plan approved in session
touches:
  - data-demo/app/modules/extension_manager/
  - data/tests/
---

## Problem

Operators can manage extensions only from the CLI; the owner wants a low-friction management screen.

## Evidence

- `docs/adr/0003-engine-boundary-and-internal-proxy.md` promises modules, plugins and themes that come and go without touching the engine; the code does not deliver it yet.

## Done when

- [ ] The panel is itself a module: it lists modules, plugins and themes with version, state and health, and installs, activates, deactivates, uninstalls and selects the theme through `ExtensionManager`.
- [ ] Protected by authentication and an administrator check, CSRF on every action, every string a key in en, pt-BR and es.
- [ ] A refused action (missing dependency, active dependent) is shown with its reason.

## Verify

```bash
docker exec framework sh -lc 'cd /app && python -m pytest tests -q'
docker exec framework sh -lc 'cd /app && ruff check engine'
cd data && python tools/check_engine_boundary.py
python .claude/rules/lint_language.py --config data/language-standard.toml
```

## Notes

Slice 10 of 10 of the extension model. Owner rulings 2026-10-05: one manifest with three kinds; extensions under `data/app/{modules,plugins,themes}/`; the whole model in one delivery; an extension failing must never take the application down; a low-friction management panel. Architecture is not delegable to the local model.

## History

- 2026-10-05T09:55:31Z created by claude@claude-code (source: owner request 2026-10-05)
- 2026-10-05T10:01:15Z owner ruling: data/ stays the slim framework, so the panel is a module of data-demo/; blocked with the CRM demo task until the owner decides how data-demo consumes the engine (owner, relayed by claude@claude-code)
