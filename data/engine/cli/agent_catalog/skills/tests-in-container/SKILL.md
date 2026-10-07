---
name: tests-in-container
description: Runs and trusts tests only inside the project's application container. Use when reporting a test result, validating a change, or deciding whether a green run counts as evidence.
---

# Tests in the container

## Overview

A green run in the host editor's virtual environment is an impression; only a run
inside the project's application container is evidence. The container carries the
real database, the image's dependencies and the container environment, so a test
that passes there passes where the code actually runs. Reporting a host run as
"verified" is how a broken change reaches the main branch.

## When to Use

- Reporting any test result to another agent or to the owner
- Validating a change before closing a backlog task
- A test that so far ran only in the host `.venv`
- A migration or seed that must be checked against the real database

## The rule

1. Run every test, and every migration check, inside the application container:
   `docker exec <app-container> sh -lc 'cd /app && python -m pytest <path> -q'`.
2. If the container is down, bring it up (`docker compose up -d`) — never fall
   back to the host environment and call the result verified.
3. A result produced only in the host `.venv` is marked UNVERIFIED.
4. Never install packages into the system Python. A new runtime dependency goes
   into the dependency file **and** the image, or the container run will not see
   it.
5. Run the affected test files, not the whole suite, when the project's rules
   scope the task that way; run the whole suite when the change touches shared
   code.

## Reporting

State the container, the exact command and the outcome:

```bash
docker exec framework sh -lc 'cd /app && python -m pytest tests/test_x.py -q'
# 12 passed in 0.90s
```

"Tests pass" without the command is not evidence. A skipped or unrun check is
reported as not run, never implied to have passed.
