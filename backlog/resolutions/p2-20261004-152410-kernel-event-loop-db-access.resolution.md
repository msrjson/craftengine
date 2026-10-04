---
task: p2-20261004-152410-kernel-event-loop-db-access
outcome: resolved
agent: gemini
started_at: 2026-10-04T16:15:30Z
finished_at: 2026-10-04T16:18:40Z
---

## What changed

- `data/engine/http/kernel.py`:
  - Moved the module state check (`self.app.make("module").state(module_name)`) and exception rendering (`self._render_exception(req, exc)`) inside the worker threadpool target `serve(req)`.
  - Ensures that any database query performed during module cache misses or exception rendering runs on the request's worker thread.
  - Ensures that `self.app.make("events").notify(RequestTerminated(req))` inside `serve`'s `finally` block runs after all action and exception rendering logic, guaranteeing clean release of pooled database connections.
  - Avoids checking out any connection on the ASGI event loop thread.
- `data/tests/test_kernel_lifecycle.py`:
  - Added `test_event_loop_thread_holds_no_connection_after_module_request_with_expired_cache` verifying that the event loop thread holds no checked-out database session after a module-scoped request with expired module cache.
  - Added `test_event_loop_thread_holds_no_connection_after_raising_action` verifying that the event loop thread holds no checked-out database session after an action raising an exception.
- `data/CHANGELOG.md`: Added bugfix entry under `## [Unreleased]`.

## Verification

```bash
docker exec framework sh -lc 'cd /app && python -m pytest tests/test_kernel_lifecycle.py -q'
#   6 passed, 2 warnings in 1.00s
docker exec framework sh -lc 'cd /app && ruff check engine'
#   All checks passed!
cd data && python tools/check_engine_boundary.py
#   ENGINE_BOUNDARY_NEW_FINDINGS 0
```
