---
id: "20261004-152410"
title: Kernel touches the database on the event loop thread, outside the request release
type: bugfix
priority: 2
autonomous: false
blocked_by: none
max_attempts: 2
attempts: 0
created_at: 2026-10-04T15:24:10Z
updated_at: 2026-10-04T15:24:10Z
source: adversarial review of ad63fb5..1dfb16f (finding 6), 2026-10-04
touches:
  - data/engine/http/kernel.py
  - data/engine/modules/manager.py
  - data/tests/
---

## Problem

Two kernel paths run on the ASGI event loop thread instead of the request's worker thread, so whatever they borrow from the database is never returned by the `RequestTerminated` release, and they run outside the worker's tenant context:

- the module switch check calls `make("module").state(name)`, which queries the database each time its cache expires;
- `_render_exception` renders the error page after `run_in_threadpool` returned.

Pre-existing: the module check is already in `ad63fb5` (v4.2.0). Confidence of the review: medium - reproduce before fixing.

## Evidence

- `data/engine/http/kernel.py` module check (around the `make("module").state` call) and `_render_exception` after `serve`.
- `data/engine/modules/manager.py:92` - `DB.statement` inside `state` once `cache_ttl` expires.
- `data/engine/orm/connection.py` - pooled sessions are thread-local.

## Done when

- [ ] A test shows the event-loop thread holds no checked-out connection after a request to a module-scoped route with an expired module cache, and after a request whose action raises.
- [ ] Both paths either run on the worker thread or borrow nothing; the kernel still names no subsystem (`tests/test_kernel_lifecycle.py`).

## Verify

```bash
docker exec framework sh -lc 'cd /app && python -m pytest tests/test_kernel_lifecycle.py -q'
docker exec framework sh -lc 'cd /app && CRAFT_TEST_DB=pgsql python -m pytest tests -q'
cd data && python tools/check_engine_boundary.py
```

## Notes

Kernel and connection lifecycle: not delegable to the local model.

## History

- 2026-10-04T15:24:10Z created by claude (source: adversarial review finding 6)
