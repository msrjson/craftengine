---
id: "20261006-210820"
title: Protect the engine boundary in generated commercial applications
type: bugfix
priority: 2
autonomous: true
blocked_by: none
max_attempts: 2
attempts: 1
claimed_by: gpt@codex
created_at: 2026-10-06T21:08:20Z
updated_at: 2026-10-06T21:14:05Z
source: owner wants commercial solutions extended through modules/plugins without agents modifying the framework
touches:
  - data/engine/cli/project_scaffolder.py
  - data/engine/cli/skeleton/AGENTS.md.stub
  - data/engine/cli/skeleton/tools/check_engine_changes.py.stub
  - data/tests/test_project_scaffolder.py
  - data/tests/test_application_engine_guard.py
  - data/documentation/architecture.md
  - data/documentation/installation.md
  - data/documentation/engine-lifecycle.md
  - data/README.md
  - data/CHANGELOG.md
---

## Problem

Generated applications have no agent instructions or task-baseline guard against engine edits. Installation guidance starts from an editable framework clone.

## Evidence

- `data/engine/cli/skeleton/`: no AGENTS.md template.
- `data/documentation/installation.md:14`: clone and editable installation instructions.
- `data/engine/cli/project_scaffolder.py:157`: generated projects already use a package-mode engine lock.

## Done when

- [x] New applications carry one agent instruction source and tool symlinks, prohibiting engine edits for product features.
- [x] A baseline-based guard detects tracked, untracked and already committed engine/lock/governance changes without blocking ordinary extension changes.
- [x] Application setup and maintenance docs explain the pinned package workflow and separate owner-authorized framework changes.
- [x] Scaffold, packaging and guard regression tests pass in framework; required gates pass.

## Verify

```bash
docker exec framework sh -lc 'cd /app && python -m pytest tests/test_application_engine_guard.py tests/test_project_scaffolder.py tests/test_package_data.py -q && ruff check engine'
(cd data && python tools/check_engine_boundary.py)
(cd data && python3 ../.claude/rules/lint_language.py --config language-standard.toml)
(cd data && python3 ../.claude/rules/lint_language.py --config language-standard.views.toml)
python3 .claude/rules/lint_backlog.py
python3 .claude/rules/lint_board.py
```

## Notes

Framework scaffolding context only; no commercial application's files, database, release or deployment are changed. The guard is a workflow check, not an OS sandbox. An explicitly requested framework maintenance task remains possible in a separate reviewed workflow.

## History

- 2026-10-06T21:08:20Z created by gpt@codex (owner-authorized commercial application boundary correction)
- 2026-10-06T21:08:20Z claimed by gpt@codex (attempt 1)
- 2026-10-06T21:14:05Z resolved by gpt@codex (backlog/resolutions/p2-20261006-210820-commercial-application-engine-boundary.resolution.md)
