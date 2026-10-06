---
id: "20261006-200424"
title: Map the Starlette coupling and decide on an adapter layer
type: decision
priority: 3
autonomous: false
blocked_by: owner-decision
max_attempts: 2
attempts: 0
created_at: 2026-10-06T20:04:24Z
updated_at: 2026-10-06T20:04:24Z
source: owner request in a session comparing Craft Engine with other frameworks
touches:
  - docs/adr/
---

## Problem

The HTTP transport of the engine is Starlette, and the imports are spread over
eleven engine modules instead of one boundary. Replacing or upgrading Starlette
(a breaking release, a security fix, a different ASGI base) would mean editing
every one of them, and the framework public types (`Request`, `Response`) wrap
Starlette classes by name. The owner wants the coupling mapped and a decision on
whether to put an adapter layer between the engine and Starlette.

This task produces a decision record. It changes no engine code.

## Evidence

Direct `starlette` imports under `data/engine/` (11 files):

- `data/engine/http/kernel.py:20-27` - `Starlette`, `run_in_threadpool`, request and
  response classes, `Mount`, `Route`, `StaticFiles`. The application entry point.
- `data/engine/http/request.py:23-24` - `UploadFile`, `Request`; `from_starlette`
  is called from `kernel.py:644`.
- `data/engine/http/response.py:16` - four Starlette response classes wrapped.
- `data/engine/http/middleware.py:71, 664, 695, 737, 770, 811` - responses and
  redirects, five of them as function-local imports.
- `data/engine/http/health.py:236, 260, 336, 386, 410` - JSON and plain-text
  responses, `run_in_threadpool`.
- `data/engine/http/msr.py:90-91` - `run_in_threadpool`, file and JSON responses.
- `data/engine/http/static_files.py:17-19` - `Response`, `StaticFiles`, `Scope`.
- `data/engine/exceptions/handler.py:209, 213` - JSON and HTML responses.
- `data/engine/security/firewall.py:22` - `JSONResponse`.
- `data/engine/media/image.py:476` - `Response`.
- `data/engine/extensions/assets.py:16` - `PlainTextResponse`.

Application code under `data/app/` has no direct import. At least ten test files
import Starlette directly, among them `data/tests/conftest.py`,
`test_kernel_async_actions.py` and `test_request_scope.py`.

`python-multipart` is a dependency only because Starlette parses
`multipart/form-data` (`data/pyproject.toml`, dependencies comment).

## Done when

- [ ] An ADR under `docs/adr/` lists every Starlette symbol the engine uses and
      groups them by role (application, request, response, concurrency, static
      files, routing).
- [ ] The ADR compares at least: keeping the direct imports; one internal module
      that re-exports what the engine needs; a thin adapter with engine-owned
      `Request`/`Response` types. Each option has a cost estimate in files touched.
- [ ] The ADR states what each option does for the engine boundary rules
      (EB-03, EB-04) and for the public facade compatibility rule (NR-05).
- [ ] The ADR ends with a recommendation and the owner's decision is recorded in
      this task's History.

## Verify

```bash
cd data && grep -rn "starlette" engine --include=*.py | grep import | wc -l
cd data && python tools/check_engine_boundary.py
```

The first command should list the same imports the ADR enumerates.

## Notes

- Do not remove the Starlette dependency or change an import under this task.
- A decision to adopt an adapter becomes new implementation tasks, one per slice,
  with their own tests in the `framework` container.
- Any adapter lives inside `data/engine/` and must not import the application.
- Related: `backlog/pending/p2-20261006-200037-replace-passlib-bcrypt-pin-workaround.md`
  (the other dependency finding from the same review).

## History

- 2026-10-06T20:04:24Z created by claude (source: owner request in a session comparing Craft Engine with other frameworks)
