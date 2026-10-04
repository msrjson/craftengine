---
id: "20261004-161344"
title: Remove the unused craftengine_framework_db_data_pg18 volume
type: chore
priority: 3
autonomous: false
blocked_by: owner-action
max_attempts: 2
attempts: 0
created_at: 2026-10-04T16:13:44Z
updated_at: 2026-10-04T16:13:44Z
source: evaluation of the boundary/proxy release, 2026-10-04
touches: []
---

## Problem

Running `docker compose up -d db app` from the workspace root on 2026-10-04 created an empty volume, `craftengine_framework_db_data_pg18`, because the running `framework` / `framework-db` containers belong to another compose project name. No container uses it.

## Evidence

- `docker volume ls | grep craftengine_framework_db_data_pg18`
- The live database volume is the one attached to `framework-db` (`docker inspect framework-db`).

## Done when

- [ ] The owner confirmed the volume is unused and removed it, or decided to keep it.
- [ ] A note in the workspace docs says which compose project name owns `framework` / `framework-db`, so `docker compose` from the root does not create duplicates.

## Verify

```bash
docker volume ls | grep framework_db
docker inspect framework-db --format '{{json .Mounts}}'
```

## Notes

Deleting a volume is destructive: never done by an agent (BQ-11).

## History

- 2026-10-04T16:13:44Z created by claude (source: evaluation of the boundary/proxy release, 2026-10-04)
