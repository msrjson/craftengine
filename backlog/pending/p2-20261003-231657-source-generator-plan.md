---
id: "20261003-231657"
title: Decide a shared generation plan with conflict preflight and JSON results
type: decision
priority: 2
autonomous: false
blocked_by: owner-decision
max_attempts: 2
attempts: 0
created_at: 2026-10-03T23:16:57Z
updated_at: 2026-10-03T23:16:57Z
source: Owner-corrected GitHub source comparison for human and coding-agent ergonomics
touches:
  - data/engine/cli/
  - data/documentation/cli.md
  - data/tests/
---

## Problem

A failed multi-file generation can leave partial output that a human must investigate and an agent may blindly overwrite on retry. Existing CRUD dry-run only lists paths and bypasses conflicts; other makers lack an equivalent plan contract.

## Evidence

- `data/engine/cli/crud_builder.py:286` writes the migration before model/request/controller/view conflicts are checked.
- `data/engine/cli/crud_builder.py:292` skips that collision check during pretend mode.
- `data/engine/cli/app.py:649` offers --pretend but emits human prose, not a structured conflict report.
- [phoenixframework/phoenix: def run(args)](https://github.com/phoenixframework/phoenix/blob/2ca60ffe811c0e585835cfc309b645c3a4190df1/lib/mix/tasks/phx.gen.context.ex#L112) gathers the generated file set and prompts for conflicts before copying. [laravel/framework: public function handle()](https://github.com/laravel/framework/blob/2c3294632cd68cbe35eaaa6f34fdd97087934098/src/Illuminate/Console/GeneratorCommand.php#L154) validates reserved names and file existence before a single-file write. Neither source establishes transactional filesystem writes for Craft.

## Done when

- [ ] Owner chooses the plan schema and the first two generators to adopt it (recommended: make:crud and make:auth).
- [ ] Plan describes create/update/skip/conflict per path, prerequisite gaps and route edits; preview and apply derive from the same plan.
- [ ] Add stable --json success/error results and nonzero conflict exits without mixing prose into stdout.
- [ ] Verification plan includes a collision in the LAST planned artifact: preflight leaves every existing file byte-identical and creates no earlier artifact. Runtime I/O failures have a documented recovery contract; do not promise crash-atomic multi-file writes.

## Verify

```bash
python3 .claude/rules/lint_backlog.py
rg -n 'owner ruling:' backlog/pending/p2-20261003-231657-source-generator-plan.md
git diff --check
```

These verify queue structure and a future owner ruling, not an implemented feature. Verify the Done when decisions against that ruling. Before approved implementation, create a separately scoped task with exact container test commands for the scenarios listed above. No foreign framework or Craft application behavior tests were run during this source review.

## Notes

For humans: review a concrete diff and conflicts before changing files. For agents: inspect paths/statuses without parsing ANSI text. Suggested priority within P2: first. Effort: medium. Restrict force to explicit planned overwrites, never applied migrations.

Review: `backlog/pending/p2-20261003-231656-source-framework-ergonomics-review.md`.

Craft source baseline: `58f510c344f5362de1a4b35f98190ef2147228c7`. Local references were read from the working tree; unrelated existing worktree changes were preserved. Foreign source links use immutable commit SHAs, not moving branches. Findings are static source analysis unless explicitly stated otherwise.

Research does not authorize implementation. Keep autonomous false until the owner decides. No application code was changed. Source-level lessons require adaptation to Python, Craft's runtime and existing safety contracts; no performance or usability multiplier has been measured.

## History

- 2026-10-03T23:16:57Z created by codex (source: owner-corrected GitHub code comparison; suggestion awaiting owner decision)
