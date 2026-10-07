---
from: qwen@qwen-code
to: next-agent
created: 2026-10-07T12:30:00Z
status: open
phase: build
touches:
  - data/engine/
  - data/config/
  - data/database/migrations/
  - data/tests/
  - data/documentation/
  - data/CHANGELOG.md
---

# Goal: finish Slices 4-6 of the SoftPax upstream roadmap, then validate the new version

## Goal (authoritative)

`todas as fases ate o framework a nova versao esta validada` — every phase of
`.agents/plans/softpax-upstream-roadmap.md` implemented, and the resulting
framework version validated. Goal id `d776171b-3ad0-4b9b-a0c7-f550063622df`.

## State at handoff (commit `e0e7691`, working tree clean)

Slices **0, 1, 2 and 3 are complete and committed**:

- Slice 3 (this session): `release:sync` / `release:status` + `VERSION`
  (`engine/lifecycle/sync.py`, commits `cd9f84d`), the seed ledger
  (`engine/seeding/ledger.py`, `85e9aa0`), the production image
  (`docker/entrypoint.sh`, `Dockerfile.prod`, `.dockerignore`, `7e59055`) and
  materialized-view suspension (`engine/migrations/migrator.py`, `33a4e73`).
- Slice 4 started: `route:check` + duplicate route names (`e0e7691`).

Task `backlog/processing/p2-20261007-122450-slice-4-platform.md` is **claimed
and open** (attempt 1, claimed_by qwen@qwen-code). The board CLAIM is the line
of `2026-10-07T12:25Z`.

## What remains

### Slice 4 ("Platform") — the open task lists every item; status:

- MISSING: `data:audit` CLI; `Idempotency-Key` middleware; `Money` type + ORM
  cast; transactional outbox; notification contract with provider failover and
  quotas; bounded in-memory cache with prefix flush; fallback routes ordered
  last; tenant-scoped storage disk.
- PARTIAL: DB i18n tenant override (`translations` has no `tenant_id`);
  validator errors as a structured `code`/`message_key`; `data/.dockerignore`
  already exists (Slice 3).
- DONE already (do not re-do): bundle cache, ICU plural/params, plugin circuit
  breaker, static asset cache headers, server-side datagrid, `route:check`.

### Slice 5 ("Official plugins") — all MISSING as official plugins

Brazil validator (exists only as `documentation/examples/plugins/brazil_validator/`),
PIX BR Code, QR/barcode with `segno`, XLSX export, XMLDSig/PKCS#12, mTLS
channel, cookieless SEO, privacy kit, document seal, e-signature, hash-chained
audit trail. `data/plugins/` is empty.

### Slice 6 ("agent workspace") — mostly MISSING

Single `AGENTS.md` + symlinks `.agents -> .claude`
(`engine/cli/agent_scaffolder.py` still writes duplicate copies); coordination
kit (`.agents/team/board.md`, sessions, `multi-session-coordination.md`,
`team-lead` agent); integration points (`.agents/handoffs/`,
`journeys/smoke.json`, `validation.json`, `lessons.md`, generated
`local-brief.md`); Python environment guard hook; generated pre-commit, CI
workflow, VS Code tasks/launch; catalog skills `tests-in-container` and
`craft-engine-pitfalls`.

### Final phase

When every slice is done: full suite green on **both** databases, all gates
clean, and the new version validated (a release candidate). Releases/pushes are
owner-only (`BQ-11`, NR-02/NR-03).

## How to work (mandatory, from `QWEN.md` / `AGENTS.md`)

1. Read the board tail, then the task file; the queue rules are
   `.agents/rules/BACKLOG_QUEUE_STANDARD.md` + `backlog/README.md`.
2. Claim shared paths on the board before editing; RELEASE when done.
3. Change only the task's `touches`; anything else becomes a new task file.
4. Tests only from the `framework` container. Never delete/wipe/truncate
   (NR-02); forward-only migrations.
5. Run the gates before declaring done: `lint_backlog.py`, `lint_board.py`,
   `tools/check_engine_boundary.py`, `lint_language.py`, `ruff`.

## Verify (exact commands)

```bash
cd "/data/projects/workspaces/craft engine"
docker exec framework sh -lc 'cd /app && mv .env /tmp/env.bak; python -m pytest tests -q; mv /tmp/env.bak .env'
docker exec -e CRAFT_TEST_DB=pgsql -e DB_SSLMODE=disable framework sh -lc 'cd /app && mv .env /tmp/env.bak; python -m pytest tests -q; mv /tmp/env.bak .env'
cd data && python tools/check_engine_boundary.py
python3 .agents/rules/lint_backlog.py && python3 .agents/rules/lint_board.py
```

Last full runs (this session): SQLite 1999 passed / 68 skipped; PostgreSQL 2059
passed / 4 skipped (before the `route:check` commit).

## Notes

- The reference is `/data/projects/workspaces/softpax` — **read-only learning
  source**; nothing is copied verbatim and nothing there is edited.
- Context was near full for the sender; the remaining Slice 4 items are the
  natural next step.
