---
task: p3-20261007-124250-route-check-middleware-alias-parity
outcome: resolved
agent: qwen@qwen-code (Qwen Code, local Ollama)
started_at: 2026-10-07T18:28:39Z
finished_at: 2026-10-07T18:29:30Z
---

## What changed

- `data/bootstrap/app.py`: the kernel is bound in the container
  (`app.instance("kernel", kernel)`), so the engine reaches it as
  `app.make("kernel")` and never imports `bootstrap.app`.
- `data/engine/cli/skeleton/bootstrap/app.py.stub`: the same binding, so a
  generated project's kernel is reachable the same way.
- `data/engine/cli/app.py`: `route:check` takes the kernel from the container and
  runs `doctor.check_routes(app, kernel)` — middleware aliases included — and
  falls back to `check_route_actions` when a project binds no kernel. A route
  with a misspelled alias (`Route.get(...).middleware("authh")`) is now reported
  and exits 1.
- `data/tests/test_route_check.py`: a bad alias is reported and exits 1; a known
  alias passes.
- `data/CHANGELOG.md`: entry.

## Verification

```bash
docker exec framework sh -lc 'cd /app && python -m pytest tests/test_route_check.py -q'
# 6 passed in 1.25s

cd data && python tools/check_engine_boundary.py
# ENGINE_BOUNDARY_NEW_FINDINGS 0

docker exec framework sh -lc 'cd /app && mv .env /tmp/env.bak; python -m pytest tests -q; mv /tmp/env.bak .env'
# 2158 passed, 68 skipped in 122.64s

docker exec framework sh -lc 'cd /app && ruff check engine'                 # All checks passed!
cd data && python3 ../.agents/rules/lint_language.py --config language-standard.toml   # clean
```

## Follow-ups

None. `dev.py doctor` keeps resolving middleware through the same kernel, so the
two commands now agree.
