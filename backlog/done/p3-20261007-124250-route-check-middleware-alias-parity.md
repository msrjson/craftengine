---
id: "20261007-124250"
title: route:check cannot resolve middleware aliases without the engine importing bootstrap.app
type: chore
priority: 3
autonomous: true
blocked_by: none
max_attempts: 2
attempts: 1
claimed_by: qwen@qwen-code
created_at: 2026-10-07T12:42:50Z
updated_at: 2026-10-07T18:29:30Z
source: commit 634687a (route:check engine-boundary fix), follow-up
touches:
  - data/bootstrap/app.py
  - data/engine/cli/app.py
  - data/engine/support/doctor.py
  - data/engine/cli/skeleton/
  - data/tests/
  - data/CHANGELOG.md
---

## Problem

`route:check` (`data/engine/cli/app.py`) validates route actions and names but
not middleware aliases, because resolving them needs the kernel and the kernel
lives only at module scope in `bootstrap/app.py`. The engine must not import the
application (engine-boundary gate), so the check was split: `doctor` resolves
middleware, `route:check` does not. A route with a misspelled middleware alias -
`Route.get(...).middleware("authh")` - is therefore not caught by `route:check`.

## Evidence

- `data/engine/support/doctor.py` - `check_routes(app, kernel)` resolves
  middleware then delegates to `check_route_actions(app)`; the latter is what
  `route:check` calls.
- `data/engine/cli/app.py` `route_check` docstring: "Middleware aliases are
  resolved by `dev.py doctor` instead: that needs the kernel, and the engine must
  not import `bootstrap.app`."
- `data/bootstrap/app.py:63` `kernel = Kernel(app)` - module scope only; no
  container binding.
- Commit `634687a` fixed the boundary violation by removing the import rather
  than by making the kernel reachable.

## Done when

- [ ] The kernel is reachable from the container (bound in `data/bootstrap/app.py`
  and in the generated skeleton stub), so the engine resolves it as
  `app.make("kernel")` with no `bootstrap.app` import.
- [ ] `route:check` validates middleware aliases again and exits 1 on a bad
  alias, proved by a test.
- [ ] `python tools/check_engine_boundary.py` still reports 0 new findings.

## Verify

```bash
docker exec framework sh -lc 'cd /app && python -m pytest tests/test_route_check.py -q'
cd data && python tools/check_engine_boundary.py
```

## Notes

The alternative - keeping the `bootstrap.app` import - was rejected in `634687a`:
the boundary gate counts it as new engine -> application coupling. Mirrors the
SoftPax `route:check`, which resolves middleware.

## History

- 2026-10-07T12:42:50Z created by qwen@qwen-code (source: follow-up of commit 634687a)
- 2026-10-07T18:28:39Z claimed by qwen@qwen-code (attempt 1)
- 2026-10-07T18:28:39Z scope note by qwen@qwen-code: bound the kernel in the container (`app.instance("kernel", kernel)` in `bootstrap/app.py` and the skeleton stub); `route:check` now resolves it via `get_app().make("kernel")` and runs `check_routes` (middleware + actions), falling back to `check_route_actions` when no kernel is bound; two route:check tests cover a bad alias (exit 1) and a good one
- 2026-10-07T18:29:30Z resolved by qwen@qwen-code (resolutions/p3-20261007-124250-route-check-middleware-alias-parity.resolution.md): route:check 6 passed; engine-boundary 0 new findings; full SQLite 2158 passed/68 skipped; gates clean
