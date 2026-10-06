---
task: p2-20261006-211152-development-image-git-for-boundary-tests
outcome: resolved
agent: gpt@codex
started_at: 2026-10-06T21:11:52Z
finished_at: 2026-10-06T21:14:05Z
commits: []
---

## What changed

- Added Git to data/Dockerfile's development tools so the new real-repository tests remain runnable after rebuilding.
- Installed Git in the running framework development container to verify the behavior. Production Dockerfile was not changed.

## Verification

- `docker exec framework git --version`: Git installed and executable.
- Application guard, scaffolding, packaging and engine lifecycle tests: 58 passed in framework.
- Dockerfile installation declaration was inspected. A complete image rebuild is UNVERIFIED; equivalent Git functionality was tested in the existing development container.
- Backlog/board gates and `git diff --check`: clean.

## Follow-ups

None in this framework task. Release/publication and adoption in existing commercial application repositories are separate owner-controlled operations.
