---
id: "20261003-223123"
title: Explain the mistake when a relation is read as a property
type: feature
priority: 2
autonomous: true
blocked_by: none
max_attempts: 2
attempts: 0
created_at: 2026-10-03T22:31:23Z
updated_at: 2026-10-03T22:31:23Z
source: docs/backlog.md L6 (agent-resilience audit 2026-09-25)
touches:
  - data/engine/orm/model.py
  - data/engine/support/diagnostics.py
  - data/tests/
  - data/CHANGELOG.md
---

## Problem

Relations are methods. `post.user.name` reaches a bound method and fails with a generic `AttributeError` that never says the relation must be called (`post.user().first()`) or eager-loaded. Agents make this mistake routinely.

## Evidence

- `data/engine/orm/model.py:100` - eager-loaded relations are stored by method name; reading the attribute without loading returns the bound method.
- `data/engine/orm/model.py:198` - `_calling_relation_name()` already detects relation methods and can drive the hint.

## Done when

- [ ] Reading an attribute of an unloaded relation raises an error whose message comes from `craft.support.diagnostics` and names the relation, the call form and the eager-load form.
- [ ] Loaded relations and plain attributes behave exactly as before.
- [ ] Tests cover the hint, a loaded relation and a plain attribute.
- [ ] CHANGELOG entry under `[Unreleased]`.

## Verify

```bash
docker exec framework sh -lc 'cd /app && python -m pytest tests/test_orm_relations.py -q'
```

## Notes

The test file name in Verify is a suggestion; use the existing relations test module if one exists. The other two L6 leftovers (rules without arguments, `FormRequest.data()` swallowing exceptions) were found already fixed on 2026-10-03: `Validator.REQUIRED_ARGUMENTS` (`data/engine/validation/validator.py:86`) and the narrowed catch in `data/engine/validation/form_request.py:80`.

## History

- 2026-10-03T22:31:23Z created by claude (source: docs/backlog.md L6 (agent-resilience audit 2026-09-25); migrated from the single-file backlog)
