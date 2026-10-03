---
id: "20261003-231659"
title: Decide consistent annotation resolution and dependency-path diagnostics
type: decision
priority: 2
autonomous: false
blocked_by: owner-decision
max_attempts: 2
attempts: 0
created_at: 2026-10-03T23:16:59Z
updated_at: 2026-10-03T23:16:59Z
source: Owner-corrected GitHub source comparison for human and coding-agent ergonomics
touches:
  - data/engine/container/application.py
  - data/engine/http/kernel.py
  - data/engine/support/diagnostics.py
  - data/documentation/container.md
  - data/tests/
---

## Problem

Constructor injection and route binding interpret Python annotations differently. Failure messages name the immediate parameter but do not provide a bounded dependency path that helps users diagnose cycles or unresolved forward references.

## Evidence

- `data/engine/container/application.py:207` consumes constructor annotations directly without eval_str or typed annotation normalization.
- `data/engine/http/kernel.py:133` attempts eval_str=True for action annotations: the two entry points differ.
- [fastapi/fastapi: def get_typed_signature(](https://github.com/fastapi/fastapi/blob/5f9fc5c59a9bb54608aa35376715f3ba9708188e/fastapi/dependencies/utils.py#L213) unwraps functions and resolves string forward references. [symfony/symfony: private function createTypeAlternatives(](https://github.com/symfony/symfony/blob/9493f3e814d1cf270f8dcb95c58e44c56de14a89/src/Symfony/Component/DependencyInjection/Compiler/AutowirePass.php#L657) lists candidate services for ambiguous types. [nestjs/nest: public async resolveConstructorParams](https://github.com/nestjs/nest/blob/35142c3eca8edaaf6abc5984d915da2fbd458aa2/packages/core/injector/injector.ts#L311) carries resolution context; Nest loadInstance checks pending/circular dependencies. [laravel/framework: public function currentlyResolving()](https://github.com/laravel/framework/blob/2c3294632cd68cbe35eaaa6f34fdd97087934098/src/Illuminate/Container/Container.php#L1656) exposes its current resolution stack. [MasoniteFramework/masonite: def make(](https://github.com/MasoniteFramework/masonite/blob/b86a236c87e888937e77c031fc1ec378514b4632/src/masonite/container/container.py#L100) offers class/key resolution, but its class-level mutable registries are NOT a pattern to copy into Craft.

## Done when

- [ ] Owner approves a shared bounded annotation resolver and explicit unsupported-type policy before implementation.
- [ ] Resolution covers future annotations, forward references, wrapped callables, supported Optional/Annotated cases, defaults, positional-only/variadic parameters, without constructing scalar builtins as services.
- [ ] Report a stable diagnostic code with owner, parameter, annotation, dependency chain and explicit binding fix; cycles fail before RecursionError.
- [ ] Verification plan includes A -> B -> A, unresolved references, legitimate defaults and concurrent request isolation. No import search that silently guesses application classes.

## Verify

```bash
python3 .claude/rules/lint_backlog.py
rg -n 'owner ruling:' backlog/pending/p2-20261003-231659-source-container-resolution.md
git diff --check
```

These verify queue structure and a future owner ruling, not an implemented feature. Verify the Done when decisions against that ruling. Before approved implementation, create a separately scoped task with exact container test commands for the scenarios listed above. No foreign framework or Craft application behavior tests were run during this source review.

## Notes

For humans: root-cause path and a precise remedy. For agents: use normal typed constructors without guessing string aliases. Effort: medium. Preserve current ContextVar scopes and primary causes; optional defaults must not hide implementation failures.

Review: `backlog/pending/p2-20261003-231656-source-framework-ergonomics-review.md`.

Craft source baseline: `58f510c344f5362de1a4b35f98190ef2147228c7`. Local references were read from the working tree; unrelated existing worktree changes were preserved. Foreign source links use immutable commit SHAs, not moving branches. Findings are static source analysis unless explicitly stated otherwise.

Research does not authorize implementation. Keep autonomous false until the owner decides. No application code was changed. Source-level lessons require adaptation to Python, Craft's runtime and existing safety contracts; no performance or usability multiplier has been measured.

## History

- 2026-10-03T23:16:59Z created by codex (source: owner-corrected GitHub code comparison; suggestion awaiting owner decision)
