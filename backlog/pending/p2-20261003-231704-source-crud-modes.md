---
id: "20261003-231704"
title: Decide explicit API and HTML modes for CRUD scaffolding
type: decision
priority: 2
autonomous: false
blocked_by: owner-decision
max_attempts: 2
attempts: 0
created_at: 2026-10-03T23:17:04Z
updated_at: 2026-10-03T23:17:04Z
source: Owner-corrected GitHub source comparison for human and coding-agent ergonomics
touches:
  - data/engine/cli/crud_builder.py
  - data/engine/cli/app.py
  - data/engine/cli/generators.py
  - data/documentation/crud-builder.md
  - data/tests/
---

## Problem

An API-only feature currently receives admin templates, an admin controller, layout and web routes as well as its JSON API. A human or agent must infer which generated files and prerequisites actually belong to the requested feature.

## Evidence

- `data/engine/cli/crud_builder.py:336` unconditionally generates HTML artifacts during real builds.
- `data/engine/cli/crud_builder.py:365` couples web route generation to the same resource_route option as API registration.
- [adonisjs/core: async prepare()](https://github.com/adonisjs/core/blob/e1b2357eacc2e8e72e0815abbc5f2e94264acffb/commands/make/controller.ts#L106) selects resource, API or specified-action stubs and handles conflicting flags. [MasoniteFramework/masonite: if "/" in full_path:](https://github.com/MasoniteFramework/masonite/blob/b86a236c87e888937e77c031fc1ec378514b4632/src/masonite/commands/MakeControllerCommand.py#L28) separates API/resource/basic controller templates. [phoenixframework/phoenix: def run(args)](https://github.com/phoenixframework/phoenix/blob/2ca60ffe811c0e585835cfc309b645c3a4190df1/lib/mix/tasks/phx.gen.context.ex#L112) supports schema/context choices and an explicit generated file list.

## Done when

- [ ] Owner approves --api/--web/--both semantics and a backward-compatible default, with incompatible flags rejected deterministically.
- [ ] API mode writes no views/layout/admin controller/web route; web mode does not add unwanted API artifacts.
- [ ] Generation plan reports auth/model/config prerequisites and the resulting protected routes before apply; never assume an admin table or identity model exists in a fresh project.
- [ ] Verification plan checks mode-specific file manifests on craft new output, route inventory, authorization and reproducible reruns.

## Verify

```bash
python3 .claude/rules/lint_backlog.py
rg -n 'owner ruling:' backlog/pending/p2-20261003-231704-source-crud-modes.md
git diff --check
```

These verify queue structure and a future owner ruling, not an implemented feature. Verify the Done when decisions against that ruling. Before approved implementation, create a separately scoped task with exact container test commands for the scenarios listed above. No foreign framework or Craft application behavior tests were run during this source review.

## Notes

For humans: generate the feature actually requested. For agents: smaller bounded changes and fewer unexplained prerequisites. Effort: medium. Existing broad CRUD behavior can remain as --both until a versioned default change is approved. Keep authentication/authorization enforcement.

Review: `backlog/pending/p2-20261003-231656-source-framework-ergonomics-review.md`.

Craft source baseline: `58f510c344f5362de1a4b35f98190ef2147228c7`. Local references were read from the working tree; unrelated existing worktree changes were preserved. Foreign source links use immutable commit SHAs, not moving branches. Findings are static source analysis unless explicitly stated otherwise.

Research does not authorize implementation. Keep autonomous false until the owner decides. No application code was changed. Source-level lessons require adaptation to Python, Craft's runtime and existing safety contracts; no performance or usability multiplier has been measured.

## History

- 2026-10-03T23:17:04Z created by codex (source: owner-corrected GitHub code comparison; suggestion awaiting owner decision)
