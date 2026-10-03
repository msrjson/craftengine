---
id: "20261003-231658"
title: Decide synchronous typed controller templates using existing FormRequest binding
type: decision
priority: 2
autonomous: false
blocked_by: owner-decision
max_attempts: 2
attempts: 0
created_at: 2026-10-03T23:16:58Z
updated_at: 2026-10-03T23:16:58Z
source: Owner-corrected GitHub source comparison for human and coding-agent ergonomics
touches:
  - data/engine/cli/generators.py
  - data/documentation/controllers.md
  - data/documentation/validation.md
  - data/tests/
---

## Problem

Generated CRUD controllers teach an async style around synchronous ORM calls and manual construction of FormRequests even though Craft already supports typed, prevalidated action parameters. Users learn two ways to do the same operation.

## Evidence

- `data/engine/cli/generators.py:87` emits async actions with no awaited calls and manually constructs the request validator.
- `data/engine/http/kernel.py:155` already authorizes and validates FormRequest subclasses before invoking the action.
- `data/engine/http/kernel.py:683` runs async action results within the worker thread. This analysis does NOT claim these templates block the main ASGI event loop.
- [laravel/framework: afterResolving(](https://github.com/laravel/framework/blob/2c3294632cd68cbe35eaaa6f34fdd97087934098/src/Illuminate/Foundation/Providers/FormRequestServiceProvider.php#L29) integrates FormRequest validation into resolution. [fastapi/fastapi: def get_typed_signature(](https://github.com/fastapi/fastapi/blob/5f9fc5c59a9bb54608aa35376715f3ba9708188e/fastapi/dependencies/utils.py#L213) resolves declared parameter types. [dotnet/aspnetcore: private static Expression CreateArgument(](https://github.com/dotnet/aspnetcore/blob/dc8b384c43e5578b9dbb476ce15c66c04423ab91/src/Http/Http.Extensions/src/RequestDelegateFactory.cs#L700) makes parameter sources explicit in the binding implementation.

## Done when

- [ ] Owner approves sync def as the default for generated actions using the synchronous Craft ORM, with genuine async use documented separately.
- [ ] Generated store actions use a typed FormRequest parameter and validated() without manual wrapping; annotate route identifiers, Request and responses where meaningful.
- [ ] Keep existing async applications compatible; do not redesign the runtime as part of this template slice.
- [ ] Plan verifies 403/422 occur before action-side effects and exercises the generated template through a real route, plus cached repeated validated() behavior.

## Verify

```bash
python3 .claude/rules/lint_backlog.py
rg -n 'owner ruling:' backlog/pending/p2-20261003-231658-source-controller-conventions.md
git diff --check
```

These verify queue structure and a future owner ruling, not an implemented feature. Verify the Done when decisions against that ruling. Before approved implementation, create a separately scoped task with exact container test commands for the scenarios listed above. No foreign framework or Craft application behavior tests were run during this source review.

## Notes

For humans: one taught validation flow. For agents: signatures declare what is injected and validated. Effort: low/medium. Retain separate ownership/policy authorization and existing update validation semantics. This is a proposed convention, not a proven performance gain.

Review: `backlog/pending/p2-20261003-231656-source-framework-ergonomics-review.md`.

Craft source baseline: `58f510c344f5362de1a4b35f98190ef2147228c7`. Local references were read from the working tree; unrelated existing worktree changes were preserved. Foreign source links use immutable commit SHAs, not moving branches. Findings are static source analysis unless explicitly stated otherwise.

Research does not authorize implementation. Keep autonomous false until the owner decides. No application code was changed. Source-level lessons require adaptation to Python, Craft's runtime and existing safety contracts; no performance or usability multiplier has been measured.

## History

- 2026-10-03T23:16:58Z created by codex (source: owner-corrected GitHub code comparison; suggestion awaiting owner decision)
