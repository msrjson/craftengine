---
id: "20261006-211152"
title: Include Git in the framework development image for application boundary tests
type: chore
priority: 2
autonomous: true
blocked_by: none
max_attempts: 2
attempts: 1
claimed_by: gpt@codex
created_at: 2026-10-06T21:11:52Z
updated_at: 2026-10-06T21:14:05Z
source: owner-authorized application guard needs real Git baseline regression tests
touches:
  - data/Dockerfile
---

## Problem

The development image promises to run the framework suite but lacks Git, now needed to verify committed application engine changes.

## Evidence

- `data/Dockerfile:9`: development tools install build-essential only.
- `data/tests/test_application_engine_guard.py:22`: isolated Git repository setup requires Git.

## Done when

- [x] The development Dockerfile includes Git; production is unchanged.
- [x] Guard, scaffold and packaging tests pass with Git present in framework.

## Verify

```bash
docker exec framework git --version
docker exec framework sh -lc 'cd /app && python -m pytest tests/test_application_engine_guard.py tests/test_project_scaffolder.py tests/test_package_data.py -q'
```

## Notes

Git is a development/test dependency. No application database or deployment is changed.

## History

- 2026-10-06T21:11:52Z created by gpt@codex (owner-authorized verification dependency)
- 2026-10-06T21:11:52Z claimed by gpt@codex (attempt 1)
- 2026-10-06T21:14:05Z resolved by gpt@codex (backlog/resolutions/p2-20261006-211152-development-image-git-for-boundary-tests.resolution.md)
