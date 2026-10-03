---
task: p2-20261003-223201-engine-boundary-gate
outcome: resolved
agent: claude
started_at: 2026-10-04T00:10:00Z
finished_at: 2026-10-03T23:13:11Z
---

## What changed

- `data/tools/check_engine_boundary.py` + `data/tools/engine-boundary-policy.json`: AST gate (`ENGINE_APP_IMPORT`, `SERVICE_CONTROLLER_IMPORT`, `BOUNDARY_SYNTAX`), ratcheted against a pinned 40-hex base; an unreadable base or missing git blocks (exit 2). Lives in `data/tools/` next to the other CI gates rather than `deploy/`.
- CI (`.github/workflows/deploy.yml`): `fetch-depth: 0` and an "Engine boundary" step.
- `engine/providers/service_providers.py`: the `routes.console` import became the `app.console_routes` config seam (also in the skeleton stub).
- `docs/adr/0003-engine-boundary-and-internal-proxy.md` and `.claude/rules/ENGINE_BOUNDARY.md` (EB-01..07). The rules went to a project-owned file instead of `CRAFT_ENGINEERING_GOVERNANCE.md`, because that file is re-provisioned from a global source and would lose the section.
- Known debt held by the ratchet: `engine/cli/app.py` imports `bootstrap.app` three times (CLI launcher loading the composition root).

## Verification

```bash
cd data && python tools/check_engine_boundary.py           # ENGINE_BOUNDARY_NEW_FINDINGS 0, exit 0
cd data && python tools/check_engine_boundary.py --full    # 3 findings, all engine/cli/app.py -> bootstrap.app
# probe: appended "from app.Models.Probe import Probe" to engine/http/router.py
#   gate: ENGINE_BOUNDARY_NEW_FINDINGS 1, exit 1; suite: test_engine_boundary errors; file restored
docker exec framework sh -lc 'cd /app && python -m pytest tests/test_engine_boundary.py -q'   # 24 passed
docker exec framework sh -lc 'cd /app && ruff check .'                                       # All checks passed
docker exec framework sh -lc 'cd /app && python -m pytest tests -q'                          # 1735 passed, 66 skipped
docker exec framework sh -lc 'cd /app && CRAFT_TEST_DB=pgsql python -m pytest tests -q'      # 1797 passed, 4 skipped
```

The CI step itself is UNVERIFIED until the next push runs it.
