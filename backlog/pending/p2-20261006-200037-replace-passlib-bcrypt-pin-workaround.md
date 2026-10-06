---
id: "20261006-200037"
title: Replace the passlib bcrypt pin workaround with a direct, maintained bcrypt path
type: chore
priority: 2
autonomous: false
blocked_by: owner-decision
max_attempts: 2
attempts: 0
created_at: 2026-10-06T20:00:37Z
updated_at: 2026-10-06T20:00:37Z
source: owner request in a session comparing Craft Engine with other frameworks
touches:
  - data/engine/auth/password.py
  - data/pyproject.toml
---

## Problem

Password hashing carries a workaround instead of a fix. `passlib`'s bcrypt backend
reads `bcrypt.__about__`, which `bcrypt` 4.1 removed, so `pyproject.toml` pins
`bcrypt<4.1` and `engine/auth/password.py` builds the passlib context defensively,
silences passlib's logger and falls back to verify-only behavior when the backend
fails to load. The framework therefore cannot take current `bcrypt` releases
(including security fixes) without breaking, and the failure mode is a silent
downgrade path rather than an error. This affects every project on the engine
that still verifies legacy bcrypt hashes.

## Evidence

- `data/pyproject.toml` (dependencies): `"passlib>=1.7"` and `"bcrypt>=4.0,<4.1"`,
  with a comment stating the pin exists so passlib does not raise on first use.
- `data/engine/auth/password.py:56-88`: `_passlib_context()` catches the backend
  load failure, raises the passlib logger level to CRITICAL while constructing the
  context, and returns `None` so callers use the fallback path.
- `data/engine/auth/password.py:162-163`: any non-Argon2id hash is rewritten on
  next login once Argon2id is available, so bcrypt is only needed to verify
  hashes that predate Argon2id.
- UNVERIFIED: that passlib is no longer actively maintained. Check the upstream
  release history before relying on it in the decision.

## Done when

- [ ] No `bcrypt<4.1` pin remains in `data/pyproject.toml`.
- [ ] Legacy bcrypt hashes still verify, and still upgrade to Argon2id on login.
- [ ] `engine/auth/password.py` has no logger suppression and no silent fallback
      for a failed bcrypt backend; a broken backend raises a specific error.
- [ ] `passlib` is removed from the dependencies, or the task records why it stays.
- [ ] A test covers verifying a stored bcrypt hash and its upgrade to Argon2id.

## Verify

```bash
docker exec framework sh -lc 'cd /app && python -m pytest tests -q -k "password or hash"'
```

## Notes

- Decision for the owner: verify legacy hashes by calling `bcrypt` directly
  (`bcrypt.checkpw`) and drop `passlib`, or keep `passlib` and pin it with a
  recorded exit date. The first removes the pin and one dependency.
- Auth is a sensitive area: no local-model delegation, and the change needs a
  security review before release.
- Existing hashes must keep working. No password reset, no forced re-hash.
- The test file name was not located when this task was written; find the
  current password tests and add the new case there.

## History

- 2026-10-06T20:00:37Z created by claude (source: owner request in a session comparing Craft Engine with other frameworks)
