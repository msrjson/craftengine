---
id: "20261003-231706"
title: Decide project-owned template overrides and generated behavior tests
type: decision
priority: 3
autonomous: false
blocked_by: owner-decision
max_attempts: 2
attempts: 0
created_at: 2026-10-03T23:17:06Z
updated_at: 2026-10-03T23:17:06Z
source: Owner-corrected GitHub source comparison for human and coding-agent ergonomics
touches:
  - data/engine/cli/generators.py
  - data/engine/cli/crud_builder.py
  - data/engine/cli/project_scaffolder.py
  - data/documentation/cli.md
  - data/tests/
---

## Problem

Common team conventions require post-generation edits because basic makers build embedded strings and CRUD creates no application behavior tests. Repeated manual fixes increase the chance that an agent produces a slice that compiles but does not protect or validate correctly.

## Evidence

- `data/engine/cli/generators.py:47` embeds controller source; there is no project override lookup in generate().
- `data/engine/cli/project_scaffolder.py:26` already uses packaged .stub files: reusable template machinery exists for projects.
- `data/engine/cli/crud_builder.py:374` returns model/request/resource/controllers/views/routes, with no generated application test entry.
- [rails/rails: def self.hook_for(](https://github.com/rails/rails/blob/4088f9d2ef00f9b85493362fb6f4b2526bd5d314/railties/lib/rails/generators/base.rb#L174) provides named generator hooks. [laravel/framework: public function handle()](https://github.com/laravel/framework/blob/2c3294632cd68cbe35eaaa6f34fdd97087934098/src/Illuminate/Console/GeneratorCommand.php#L154) conditionally invokes matching-test creation when the relevant trait is used. [phoenixframework/phoenix: def generator_paths](https://github.com/phoenixframework/phoenix/blob/2ca60ffe811c0e585835cfc309b645c3a4190df1/lib/mix/phoenix.ex#L200) supplies generator template paths; Phoenix context source generates tests and fixtures.

## Done when

- [ ] Owner approves a small project-template override precedence, plus an opt-in behavior-test hook for make:crud.
- [ ] Override lookup never silently changes packaged templates; chosen template origin appears in the generation plan.
- [ ] Initial generated tests exercise authorization, invalid input and successful response shape through routes, without mirroring implementation or connecting to an existing database.
- [ ] Verification plan packages/installs the framework, applies a project override, generates a slice and runs its behavior tests in an isolated application environment within framework.

## Verify

```bash
python3 .claude/rules/lint_backlog.py
rg -n 'owner ruling:' backlog/pending/p3-20261003-231706-source-scaffold-test-hooks.md
git diff --check
```

These verify queue structure and a future owner ruling, not an implemented feature. Verify the Done when decisions against that ruling. Before approved implementation, create a separately scoped task with exact container test commands for the scenarios listed above. No foreign framework or Craft application behavior tests were run during this source review.

## Notes

For humans: encode team conventions once. For agents: executable acceptance criteria accompany generated code. Effort: medium/high. Avoid a general plugin system or copied business assumptions; follow database safety for future fixture work.

Review: `backlog/pending/p2-20261003-231656-source-framework-ergonomics-review.md`.

Craft source baseline: `58f510c344f5362de1a4b35f98190ef2147228c7`. Local references were read from the working tree; unrelated existing worktree changes were preserved. Foreign source links use immutable commit SHAs, not moving branches. Findings are static source analysis unless explicitly stated otherwise.

Research does not authorize implementation. Keep autonomous false until the owner decides. No application code was changed. Source-level lessons require adaptation to Python, Craft's runtime and existing safety contracts; no performance or usability multiplier has been measured.

## History

- 2026-10-03T23:17:06Z created by codex (source: owner-corrected GitHub code comparison; suggestion awaiting owner decision)
