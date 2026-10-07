---
task: p2-20261007-120648-slice-3-release-tooling-seed-ledger-mv-docker
outcome: resolved
agent: qwen@qwen-code (Qwen Code, local Ollama)
started_at: 2026-10-07T12:06:48Z
finished_at: 2026-10-07T12:23:22Z
---

## What changed

Three commits, one per coherent piece:

- `cd9f84d` - **release tooling.** New `engine/lifecycle/sync.py` (`ReleaseSync`),
  the `release:sync` / `release:status` commands (`engine/cli/app.py`), the
  `VERSION` file at the application root, the forward-only migration
  `2026_10_07_000002_create_release_syncs_table.py`, and
  `documentation/release.md` (linked from the docs index). `release:sync`
  applies the pending migrations and runs the release seeders under the
  migrator's advisory lock, records one `release_syncs` row, and refuses a
  `VERSION` that disagrees with the running code.
- `85e9aa0` - **seed ledger.** `engine/seeding/ledger.py` (`SeedLedger`,
  `once_key`), the `SEED_ONCE` opt-in honoured by `run_seeder()` and
  `Seeder.call()`, and the forward-only migration
  `2026_10_07_000003_create_seed_ledger_table.py`.
- `7e59055` - **production Docker.** `data/docker/entrypoint.sh`,
  `data/.dockerignore`, and `Dockerfile.prod` gaining `tzdata`, a real `HOME`,
  the health routes and a `HEALTHCHECK`; `documentation/deployment.md` now names
  `release:sync` as the deploy step.
- Materialized-view suspension: `Migrator` drops every materialized view before
  a pending batch and recreates it - indexes included, in dependency passes -
  when `MIGRATION_SUSPEND_MATERIALIZED_VIEWS` is on
  (`config/framework.py`, `engine/migrations/migrator.py`).

## Verification

```bash
docker exec framework sh -lc 'cd /app && mv .env /tmp/env.bak; python -m pytest tests -q; mv /tmp/env.bak .env'
# 1995 passed, 68 skipped

docker exec -e CRAFT_TEST_DB=pgsql -e DB_SSLMODE=disable framework sh -lc 'cd /app && mv .env /tmp/env.bak; python -m pytest tests -q; mv /tmp/env.bak .env'
# 2059 passed, 4 skipped

docker exec framework sh -lc 'cd /app && python -m pytest tests/test_release_sync.py tests/test_seed_ledger.py -q'
# 12 passed (7 + 5)

docker exec -e CRAFT_TEST_DB=pgsql -e DB_SSLMODE=disable framework sh -lc 'cd /app && python -m pytest tests/test_materialized_view_suspension.py tests/test_fixture_safety.py -q'
# 11 passed

docker exec framework sh -lc 'cd /app && python dev.py release:sync && python dev.py release:status'
# Release 4.7.0-r00027 synced: 1 migration(s), 1 seeder(s); status shows the trail

cd data && python tools/check_engine_boundary.py            # ENGINE_BOUNDARY_NEW_FINDINGS 0
cd data && python3 ../.agents/rules/lint_language.py --config language-standard.toml   # clean
docker exec framework sh -lc 'cd /app && python dev.py docs:check'   # 43 page(s), no broken links
docker exec framework sh -lc 'cd /app && ruff check engine/migrations/migrator.py engine/seeding engine/lifecycle/sync.py'
# All checks passed!

# Production image, end to end
docker build -f data/Dockerfile.prod -t craft-prod-check:local data/   # builds; --check: no warnings
docker run -d --network framework_default -e DB_SSLMODE=disable ... craft-prod-check:local
# entrypoint ran release:sync ("Release 4.7.0-r00027 synced"); /health -> 200;
# docker inspect .State.Health.Status -> healthy
```

## Follow-ups

The production image needs a reachable PostgreSQL (or none at all) at boot: the
`release:sync` in `docker/entrypoint.sh` is the first thing it does. On a local
PostgreSQL without TLS, `DB_SSLMODE=disable` is required - the framework default
(`require`) is correct for a managed database, so this is a deployment setting,
not a defect.

Slice 3 is complete; Slices 4-6 of the roadmap remain (Platform, Official
plugins, agent workspace).
