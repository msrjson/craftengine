---
task: p2-20261006-210820-commercial-application-engine-boundary
outcome: resolved
agent: gpt@codex
started_at: 2026-10-06T21:08:20Z
finished_at: 2026-10-06T21:14:05Z
commits: []
---

## What changed

- Generated applications carry AGENTS.md plus CLAUDE.md, GEMINI.md, QWEN.md and .cursorrules symlinks to the same instructions.
- Added a required-baseline guard for committed/staged/unstaged/untracked protected changes and package-mode local engine copies, including ignored copies.
- Declared ordinary product feature scope, public extension contracts and separate owner-authorized framework maintenance; force generation preserves existing tool instruction files.
- Revised commercial installation and maintenance guidance to use the approved package release in a separate application repository.

## Verification

- `docker exec framework sh -lc 'cd /app && python -m pytest tests/test_application_engine_guard.py tests/test_project_scaffolder.py tests/test_package_data.py tests/test_engine_lifecycle.py -q'`: 58 passed.
- Real Git integration tests prove ordinary committed module changes pass, committed engine/governance changes fail, a reviewed unchanged vendored engine passes, and invalid/missing baselines fail closed.
- `ruff check engine tests/test_application_engine_guard.py`: clean in framework.
- Engine boundary gate: 0 new findings; both language configurations and changed documentation language checks: clean.
- Backlog, board and staged gates plus `git diff --check`: clean.
- Structure gate exits 0, disabled by the existing project configuration.
- No existing commercial application or CI pipeline was modified; projects must adopt the guard and run it against the recorded task baseline or reviewed CI merge-base. The guard is not an OS sandbox.

## Follow-ups

None in this framework task. Release/publication and adoption in existing commercial application repositories are separate owner-controlled operations.
