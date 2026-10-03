---
id: "20261003-223122"
title: Finish step 0 of ADR 0002: dependency hygiene and lazy imports
type: chore
priority: 2
autonomous: true
blocked_by: none
max_attempts: 2
attempts: 0
created_at: 2026-10-03T22:31:22Z
updated_at: 2026-10-03T22:31:22Z
source: docs/adr/0002-slim-engine-optional-extras.md, Plan step 0
touches:
  - data/pyproject.toml
  - data/engine/security/__init__.py
  - data/engine/security/captcha.py
  - data/engine/http/middleware.py
  - data/CHANGELOG.md
  - data/tests/
---

## Problem

ADR 0002 chose the slim engine. Step 0 is the no-break groundwork: remove `fastapi`, move `faker` to the `dev` extra, declare `s3 = ["boto3"]`, and make the captcha, `security/__init__.py` and the firewall import in `http/middleware.py` lazy (14 -> 12 core dependencies).

## Evidence

- `data/pyproject.toml` at HEAD: `fastapi` is gone and `s3 = ["boto3>=1.28.0"]` exists (line 77); `faker>=20.0` is at line 71 - confirm which table it is in.
- The lazy-import part is unverified.

## Done when

- [ ] `fastapi` absent and `faker` only in the `dev` extra.
- [ ] Importing `engine` does not import the captcha, firewall or other `security` submodules until used (a test asserts it through `sys.modules`).
- [ ] Full suite green on SQLite and PostgreSQL in the container.
- [ ] CHANGELOG entry under `[Unreleased]`.

## Verify

```bash
docker exec framework sh -lc 'cd /app && python -c "import sys, engine; print(sorted(m for m in sys.modules if m.startswith(\"engine.security\")))"'
docker exec framework sh -lc 'cd /app && mv .env /tmp/env.bak; python -m pytest tests -q; mv /tmp/env.bak .env'
```

## Notes

Wait for the v4.2.0 decision task if it touches the same files. No public API break is allowed in this step (NR-05).

## History

- 2026-10-03T22:31:22Z created by claude (source: docs/adr/0002-slim-engine-optional-extras.md, Plan step 0; migrated from the single-file backlog)
