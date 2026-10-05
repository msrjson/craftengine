---
id: "20261005-095530"
title: End-to-end extension fixtures and documentation
type: feature
priority: 2
autonomous: true
blocked_by: none
max_attempts: 2
claimed_by: claude@claude-code
attempts: 1
created_at: 2026-10-05T09:55:30Z
updated_at: 2026-10-05T10:26:03Z
source: owner request 2026-10-05: extension model (modules, plugins, themes) with fault isolation and a management panel; plan approved in session
touches:
  - data/tests/
  - data/documentation/
  - data/CHANGELOG.md
---

## Problem

The model needs one proof that composes everything and a guide agents follow.

## Evidence

- `docs/adr/0003-engine-boundary-and-internal-proxy.md` promises modules, plugins and themes that come and go without touching the engine; the code does not deliver it yet.

## Done when

- [ ] Fixtures under `tests/fixtures/extensions/`: `catalog` exposes a service, `ordering` depends on it and calls it only through the proxy, a plugin with a filter, a theme overriding a view; a failing extension leaves the rest serving.
- [ ] `documentation/extensions.md` and `documentation/plugins.md`; `governance.md` and `internal-proxy.md` updated; CHANGELOG `[Unreleased]`.

## Verify

```bash
docker exec framework sh -lc 'cd /app && python -m pytest tests -q'
docker exec framework sh -lc 'cd /app && ruff check engine'
cd data && python tools/check_engine_boundary.py
python .claude/rules/lint_language.py --config data/language-standard.toml
```

## Notes

Slice 9 of 10 of the extension model. Owner rulings 2026-10-05: one manifest with three kinds; extensions under `data/app/{modules,plugins,themes}/`; the whole model in one delivery; an extension failing must never take the application down; a low-friction management panel. Architecture is not delegable to the local model.

## History

- 2026-10-05T09:55:30Z created by claude@claude-code (source: owner request 2026-10-05)
- 2026-10-05T10:26:03Z claimed by claude@claude-code (attempt 1)
- 2026-10-05T10:26:03Z resolved by claude@claude-code (resolutions/p2-20261005-095530-extension-end-to-end-and-docs.resolution.md)
