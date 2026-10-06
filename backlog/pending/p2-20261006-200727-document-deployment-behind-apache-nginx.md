---
id: "20261006-200727"
title: Document how to deploy the framework behind Apache or nginx
type: chore
priority: 2
autonomous: true
blocked_by: none
max_attempts: 2
attempts: 0
created_at: 2026-10-06T20:07:27Z
updated_at: 2026-10-06T20:07:27Z
source: owner question in a session comparing Craft Engine with other frameworks
touches:
  - data/documentation/
---

## Problem

The framework is an ASGI application served by its own long-running process, not
a script an HTTP server executes per request. Teams used to PHP hosting expect to
point Apache at a directory and are not told what to do instead. The production
image shows the answer (gunicorn with uvicorn workers on port 8000), but no
deployment guide explains how to put Apache, nginx or another HTTP server in
front of it, why `mod_wsgi` does not apply, or what a host must offer (a process
that stays up) before the framework can run there.

## Evidence

- `data/Dockerfile.prod:60` - `gunicorn -w 4 -k uvicorn.workers.UvicornWorker
  public.index:application --bind 0.0.0.0:8000`, after `python dev.py migrate`.
- `data/Dockerfile.prod:55` - `EXPOSE 8000`; the container serves HTTP itself.
- `data/engine/cli/app.py:1718-1739` - the dev server calls `uvicorn.run`.
- `data/pyproject.toml` (dependencies) - `starlette` and `uvicorn[standard]`:
  the framework speaks ASGI.
- `data/documentation/` - a search for `apache`, `nginx`, `reverse proxy` and
  `mod_wsgi` matched only `security.md:137`, a passing mention of trusting a
  proxy. UNVERIFIED: whether another file under `documentation/` covers
  deployment under different wording; check before writing.

## Done when

- [ ] A deployment page in `data/documentation/` states the model plainly: an
      ASGI process (`gunicorn` with `UvicornWorker`, or `uvicorn`) behind a
      reverse proxy, and that a WSGI module such as `mod_wsgi` is not the path.
- [ ] It gives a working Apache configuration (`mod_proxy`, `mod_proxy_http`,
      forwarded headers, WebSocket upgrade if the engine uses it) and an nginx
      equivalent, each tested against the `framework` container.
- [ ] It lists host requirements: a long-running process, a process supervisor
      or container runtime, and what that rules out (plain shared hosting).
- [ ] It states how the engine learns the real client address and scheme behind
      the proxy, taken from the code, not from memory of another framework.
- [ ] The documentation index links the new page.

## Verify

```bash
cd data && grep -rln "reverse proxy" documentation
docker exec framework sh -lc 'cd /app && python -m pytest tests -q -k "proxy or forwarded"'
```

## Notes

- English, committed documentation; no third-party framework is named as a model.
- Read `engine/http/middleware.py` and `config/` for the trusted-proxy handling
  before writing the header section.
- Do not change engine code under this task; a gap found becomes its own task.

## History

- 2026-10-06T20:07:27Z created by claude (source: owner question in a session comparing Craft Engine with other frameworks)
