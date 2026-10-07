---
id: "20261007-083004"
title: The official validation database (PostgreSQL) has no pgvector extension installed
type: bugfix
priority: 2
autonomous: false
blocked_by: owner-action
max_attempts: 2
attempts: 0
created_at: 2026-10-07T08:30:04Z
updated_at: 2026-10-07T08:30:04Z
source: owner ruling 2026-10-07 ("the official validation database is postgresql vector") + probe
touches:
  - data/docker-compose.yml
  - data/docker-compose.prod.yml
  - data/documentation/postgres.md
---

## Problem

The owner states PostgreSQL **with pgvector** is the official validation
database, and the engine advertises vector search and probes for the extension
at runtime - but the local validation service has only `plpgsql` installed, so a
vector-dependent behaviour can never be proven here (and would fail silently or
skip).

## Evidence

- `docker exec framework-db sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT extname FROM pg_extension;"'`
  → `plpgsql` only; server `PostgreSQL 18.6`.
- `data/engine/orm/dialect.py` probes for the `vector` extension and enables
  vector macros when it is present; `data/documentation/postgres.md` documents
  vector/JSONB/range/full-text macros; `data/tests/test_vector_search.py` exists.
- Owner, 2026-10-07: the official database for validation is postgresql vector.

## Done when

- [ ] The validation service (`framework-db`, port 5499) has the `vector`
      extension available and created, or the compiled image is documented as the
      one used for the official validation.
- [ ] The PostgreSQL test run either exercises the vector macros or explicitly
      reports the extension as absent (no silent skip).
- [ ] `data/documentation/postgres.md` states which image provides pgvector.

## Verify

```bash
docker exec framework-db sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT extname FROM pg_extension;"'
docker exec -e CRAFT_TEST_DB=pgsql -e DB_SSLMODE=disable -e DB_HOST=db -e DB_PORT=5499 \
  -e DB_DATABASE=craft_db -e DB_USERNAME=craft -e DB_PASSWORD=secretpassword \
  framework sh -lc 'cd /app && python -m pytest tests -q'
```

## Notes

Changing the database image is infrastructure: needs the owner's go-ahead
(image rebuild, possibly a data volume). `blocked_by: owner-action`. The full
suite already passes without pgvector (2037 passed, 4 skipped on 2026-10-07), so
the gap is coverage of the vector path, not a red suite.

## History

- 2026-10-07T08:30:04Z created by qwen@qwen-code (source: owner ruling 2026-10-07)
