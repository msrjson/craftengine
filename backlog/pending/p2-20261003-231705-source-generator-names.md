---
id: "20261003-231705"
title: Decide validated module names for nested generated classes
type: decision
priority: 2
autonomous: false
blocked_by: owner-decision
max_attempts: 2
attempts: 0
created_at: 2026-10-03T23:17:05Z
updated_at: 2026-10-03T23:17:05Z
source: Owner-corrected GitHub source comparison for human and coding-agent ergonomics
touches:
  - data/engine/cli/generators.py
  - data/engine/support/naming.py
  - data/documentation/cli.md
  - data/tests/
---

## Problem

Organizing classes in domain submodules currently requires manual moves and import edits. Passing a nested name can produce an invalid class identifier instead of a normalized module path.

## Evidence

- `data/engine/cli/generators.py:24` normalizes underscores/hyphens/spaces, but does not split slash or dotted module paths.
- `data/engine/cli/generators.py:664` interpolates that result into a filename and class declaration.
- Isolated AST probe (host, NOT container test evidence): studly("Sales/Product") -> "Sales/Product"; studly("Sales.Product") -> "Sales.Product"; studly("123Product") -> "123Product". All three fail str.isidentifier().
- [laravel/framework: public function handle()](https://github.com/laravel/framework/blob/2c3294632cd68cbe35eaaa6f34fdd97087934098/src/Illuminate/Console/GeneratorCommand.php#L154) qualifies names and validates reserved names. [MasoniteFramework/masonite: if "/" in full_path:](https://github.com/MasoniteFramework/masonite/blob/b86a236c87e888937e77c031fc1ec378514b4632/src/masonite/commands/MakeControllerCommand.py#L28) splits parent directories from the leaf controller name. [adonisjs/core: async prepare()](https://github.com/adonisjs/core/blob/e1b2357eacc2e8e72e0815abbc5f2e94264acffb/commands/make/controller.ts#L106) delegates entity naming to application generators.

## Done when

- [ ] Owner approves a single documented nested-name notation and a reusable entity-name parser.
- [ ] Validate every module/class segment and suffix before creating directories; reject invalid identifiers, traversal, empty segments and paths escaping the intended application root.
- [ ] Generated class/import/route references use the same parsed entity descriptor, and nested packages get required markers.
- [ ] Verification plan generates a nested controller/model and imports it in an isolated project; invalid names produce a coded nonzero error with no filesystem writes.

## Verify

```bash
python3 .claude/rules/lint_backlog.py
rg -n 'owner ruling:' backlog/pending/p2-20261003-231705-source-generator-names.md
git diff --check
```

These verify queue structure and a future owner ruling, not an implemented feature. Verify the Done when decisions against that ruling. Before approved implementation, create a separately scoped task with exact container test commands for the scenarios listed above. No foreign framework or Craft application behavior tests were run during this source review.

## Notes

For humans: organize domains with one command. For agents: no manual move/import repair. Effort: low/medium. Do not transplant PHP namespaces into Python; define Python module behavior explicitly.

Review: `backlog/pending/p2-20261003-231656-source-framework-ergonomics-review.md`.

Craft source baseline: `58f510c344f5362de1a4b35f98190ef2147228c7`. Local references were read from the working tree; unrelated existing worktree changes were preserved. Foreign source links use immutable commit SHAs, not moving branches. Findings are static source analysis unless explicitly stated otherwise.

Research does not authorize implementation. Keep autonomous false until the owner decides. No application code was changed. Source-level lessons require adaptation to Python, Craft's runtime and existing safety contracts; no performance or usability multiplier has been measured.

## History

- 2026-10-03T23:17:05Z created by codex (source: owner-corrected GitHub code comparison; suggestion awaiting owner decision)
