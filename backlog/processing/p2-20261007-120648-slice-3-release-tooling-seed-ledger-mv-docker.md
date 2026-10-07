---
id: "20261007-120648"
title: Finish Slice 3 of the SoftPax upstream roadmap (release tooling, seed ledger, view suspension, production Docker)
type: feature
priority: 2
autonomous: true
blocked_by: none
max_attempts: 2
attempts: 1
claimed_by: qwen@qwen-code
created_at: 2026-10-07T12:06:48Z
updated_at: 2026-10-07T12:06:48Z
source: .agents/plans/softpax-upstream-roadmap.md, Slice 3
touches:
  - data/VERSION
  - data/database/migrations/
  - data/engine/lifecycle/
  - data/engine/seeding/
  - data/engine/cli/app.py
  - data/Dockerfile.prod
  - data/docker/
  - data/.dockerignore
  - data/tests/
  - data/CHANGELOG.md
---

## Problem

Slice 3 of the upstream roadmap ("Migrations, scheduler, release") is only partly
landed. A survey of the current tree (Slices 0-2 are complete and released)
found these items still missing or partial:

- MISSING `release:sync` / `release:status` commands and their advisory lock.
- MISSING a `VERSION` file carrying the release identity.
- MISSING the seed ledger (a record of seeds that may run exactly once per node).
- MISSING materialized-view suspension in the migration DSL.
- MISSING `docker/entrypoint.sh`; the production Dockerfile lacks HEALTHCHECK,
  tzdata and a real HOME.

## Evidence

- `data/engine/cli/app.py`: no `release_app`; `route_app` has only `list`.
- No `data/VERSION` (glob).
- `engine/seeding/__init__.py:62` `run_seeder()` has no once-only path and there
  is no `seed_ledger` table.
- `engine/migrations/schema.py` has no materialized-view helper (`grep
  -i materialized engine/` → nothing).
- `data/Dockerfile.prod` is multi-stage but has no `HEALTHCHECK`, no `tzdata`
  and no `HOME`; `data/docker/` does not exist.

## Done when

- [ ] `data/VERSION` holds the release identity and `release:status` reports it.
- [ ] `release:sync` runs migrations + seeders under an advisory lock, records a
  row in `release_syncs`, and refuses a stale code/`VERSION` mismatch;
  `release:status` prints the last sync.
- [ ] A seeder can declare itself once-only and runs exactly once per node,
  proved by the `seed_ledger`.
- [ ] The migration DSL can suspend and restore a materialized view (PostgreSQL).
- [ ] `data/docker/entrypoint.sh` exists; `data/Dockerfile.prod` declares
  `HEALTHCHECK`, `tzdata` and a real `HOME`; `data/.dockerignore` exists.
- [ ] Full suite green on SQLite and PostgreSQL in the framework container;
  ruff, engine-boundary and language gates clean.

## Verify

```bash
docker exec framework sh -lc 'cd /app && python -m pytest tests -q'
docker exec -e CRAFT_TEST_DB=pgsql -e DB_SSLMODE=disable framework sh -lc 'cd /app && mv .env /tmp/env.bak; python -m pytest tests -q; mv /tmp/env.bak .env'
cd data && python tools/check_engine_boundary.py
```

## Notes

Forward-only migrations (NR-02): the new tables are additive and nothing is
deleted. Re-implemented from the SoftPax reference as read-only learning, to
Craft standards (English, no hardcoded copy, tests in the container).

## History

- 2026-10-07T12:06:48Z created by qwen@qwen-code (source: .agents/plans/softpax-upstream-roadmap.md, Slice 3 gap survey)
- 2026-10-07T12:06:48Z claimed by qwen@qwen-code (attempt 1)
