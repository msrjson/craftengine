---
id: "20261003-231703"
title: Decide editor-visible types for dynamic facades
type: decision
priority: 2
autonomous: false
blocked_by: owner-decision
max_attempts: 2
attempts: 0
created_at: 2026-10-03T23:17:03Z
updated_at: 2026-10-03T23:17:03Z
source: Owner-corrected GitHub source comparison for human and coding-agent ergonomics
touches:
  - data/engine/facades/
  - data/engine/cli/
  - data/pyproject.toml
  - data/documentation/container.md
  - data/tests/
---

## Problem

Facade convenience hides method declarations from static tooling. Humans lose autocomplete and agents must read service source or discover misspelled methods at runtime.

## Evidence

- `data/engine/facades/base.py:12` resolves unknown class attributes dynamically and returns Any.
- `data/engine/facades/__init__.py:9` exposes an accessor instead of declaring the actual router methods.
- [fastapi/fastapi: class APIRouter(](https://github.com/fastapi/fastapi/blob/5f9fc5c59a9bb54608aa35376715f3ba9708188e/fastapi/routing.py#L2302) declares typed public routing methods directly, enabling source/editor discovery. [dotnet/aspnetcore: private static Expression CreateArgument(](https://github.com/dotnet/aspnetcore/blob/dc8b384c43e5578b9dbb476ce15c66c04423ab91/src/Http/Http.Extensions/src/RequestDelegateFactory.cs#L700) consumes explicit typed signatures and parameter metadata. These are examples of discoverable contracts, not proof that a .pyi generator already exists upstream.

## Done when

- [ ] Owner chooses explicit typed facade wrappers versus packaged generated .pyi stubs; recommendation: start with Route and DB to evaluate cost.
- [ ] Public parameters/return types are visible to an editor and a static checker without booting the application.
- [ ] Any generated signatures have a reproducible drift check against public service methods, handling fluent return types and class/instance binding correctly.
- [ ] Runtime facades and test swaps retain compatibility; static checks flag a misspelled method and an invalid parameter in a minimal consumer example.

## Verify

```bash
python3 .claude/rules/lint_backlog.py
rg -n 'owner ruling:' backlog/pending/p2-20261003-231703-source-typed-facades.md
git diff --check
```

These verify queue structure and a future owner ruling, not an implemented feature. Verify the Done when decisions against that ruling. Before approved implementation, create a separately scoped task with exact container test commands for the scenarios listed above. No foreign framework or Craft application behavior tests were run during this source review.

## Notes

For humans: autocomplete, jump-to-definition and earlier type errors. For agents: an inspectable public contract. Effort: medium. Avoid handwritten duplicate signatures across every facade; no performance claims.

Review: `backlog/pending/p2-20261003-231656-source-framework-ergonomics-review.md`.

Craft source baseline: `58f510c344f5362de1a4b35f98190ef2147228c7`. Local references were read from the working tree; unrelated existing worktree changes were preserved. Foreign source links use immutable commit SHAs, not moving branches. Findings are static source analysis unless explicitly stated otherwise.

Research does not authorize implementation. Keep autonomous false until the owner decides. No application code was changed. Source-level lessons require adaptation to Python, Craft's runtime and existing safety contracts; no performance or usability multiplier has been measured.

## History

- 2026-10-03T23:17:03Z created by codex (source: owner-corrected GitHub code comparison; suggestion awaiting owner decision)
