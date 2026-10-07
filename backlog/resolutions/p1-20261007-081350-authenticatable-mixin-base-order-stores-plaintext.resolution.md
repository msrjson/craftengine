---
task: p1-20261007-081350-authenticatable-mixin-base-order-stores-plaintext
outcome: resolved
agent: qwen@qwen-code (Qwen Code, local Ollama)
started_at: 2026-10-07T08:16:00Z
finished_at: 2026-10-07T08:25:00Z
commits: []
---

## What changed

- `data/engine/auth/models.py` — `AuthenticatableMixin.__init_subclass__` raises
  `TypeError` when `Model` precedes the mixin in the MRO, naming the plaintext
  consequence and the correct order. Same guard shape and message style as
  `SoftDeletes` (`engine/orm/soft_deletes.py:44`) and `TenantScoped`
  (`engine/orm/tenant_scoped.py:42`); subclasses of a correctly ordered model
  keep working because the check compares MRO positions.
- `data/tests/test_auth.py` — new `TestAuthenticatableMixinBaseOrder`: the wrong
  order raises (`match="plaintext"`) and the right order is accepted.
- `data/CHANGELOG.md` — `[Unreleased] / Fixed` entry.

## Verification

```
docker exec framework sh -lc 'cd /app && python -m pytest tests/test_auth.py -q'
# 37 passed

docker exec framework sh -lc 'cd /app && python -m pytest tests/test_auth.py tests/test_orm_model.py tests/test_rbac.py tests/test_tenancy_wiring.py tests/test_tenancy_relationships.py tests/test_model_change_tracking.py tests/test_placebo_regressions_orm.py -q'
# 148 passed, 2 skipped

docker exec framework sh -lc 'cd /app && ruff check engine'
# All checks passed!
```

Not run: the full suite and the PostgreSQL pass. The change only affects classes
that mix `AuthenticatableMixin`, and every suite that builds such models (auth,
ORM, RBAC, tenancy, change tracking, placebo regressions) was run and is green.
The generated `User` template already used the correct order, so no generated
project changes behaviour.

## Follow-ups

`p2-20261007-081351` (language-gate translator functions) and
`p2-20261007-081352` (translations unique index) queued as owner decisions.
