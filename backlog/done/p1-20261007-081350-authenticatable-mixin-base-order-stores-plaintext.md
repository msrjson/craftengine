---
id: "20261007-081350"
title: AuthenticatableMixin stores plaintext passwords when listed after Model
type: bugfix
priority: 1
autonomous: true
blocked_by: none
max_attempts: 2
attempts: 1
claimed_by: qwen@qwen-code
created_at: 2026-10-07T08:13:50Z
updated_at: 2026-10-07T08:25:00Z
source: framework audit 2026-10-07 (auth/security exploration)
touches:
  - data/engine/auth/models.py
  - data/tests/test_auth.py
  - data/CHANGELOG.md
---

## Problem

The engine's doctrine is that a mistake stops you instead of producing
something that looks like it worked. `SoftDeletes` and `TenantScoped` enforce
that for their own failure mode with an `__init_subclass__` guard. The password
mixin does not: `class User(Model, AuthenticatableMixin)` wins the MRO with
`Model.force_create()` and `Model.save()`, the hashing hooks never run, and every
password is written as plaintext — silently, and a login still works because
`check_password` hashes the candidate.

## Evidence

- `data/engine/auth/models.py:20` — `class AuthenticatableMixin` defines
  `force_create` (:37) and `save` (:53) but no `__init_subclass__`; nothing
  validates the base order.
- `data/engine/orm/soft_deletes.py:44-70` and
  `data/engine/orm/tenant_scoped.py:42-64` — the pattern and the message format
  this fix must match.
- `data/engine/cli/auth_templates/app/Models/User.py.stub:7` — the generator
  writes the correct order (`class User(AuthenticatableMixin, AuthorizableMixin,
  Model)`), so generated projects are safe; hand-written ones are not.
- `data/documentation/dx_acceleration.md` §3 says "Inherit Mixins First" while
  its example reads `class BlogPost(Model, SluggableMixin)` — the shape that is
  wrong for this mixin.

## Done when

- [ ] `AuthenticatableMixin` defines `__init_subclass__` raising `TypeError` when
      `Model` precedes it in the MRO, naming the plaintext consequence and the
      correct order.
- [ ] A test proves the wrong order raises and the right order works.
- [ ] `data/CHANGELOG.md` carries the entry in the same change.

## Verify

```bash
docker exec framework sh -lc 'cd /app && python -m pytest tests/test_auth.py -q'
```

## Notes

Mirrors the guard already in `soft_deletes.py` / `tenant_scoped.py`. A subclass
of a correctly ordered model (its MRO still holds the mixin before `Model`) must
keep working — the check compares MRO positions, not direct bases.

## History

- 2026-10-07T08:13:50Z created by qwen@qwen-code (source: framework audit 2026-10-07)
- 2026-10-07T08:16:00Z claimed by qwen@qwen-code (attempt 1)
- 2026-10-07T08:25:00Z resolved by qwen@qwen-code (resolutions/p1-20261007-081350-authenticatable-mixin-base-order-stores-plaintext.resolution.md)
