---
name: incremental-implementation
description: Delivers changes in thin, verified, committed slices instead of one large pass. Use when implementing any feature or change that touches more than one file, when picking up the next task from a plan, when shipping unfinished work behind a feature flag, or when a task feels too big to land in one step.
---

# Incremental Implementation

## Overview

Build in thin vertical slices: implement one piece, test it, verify it, commit it,
then expand. Never implement a whole feature in a single pass. Every increment
leaves the system working and testable. This is the execution discipline that
makes large features manageable.

On Craft Engine, the increment runs **after** the architecture is confirmed (see
the `spec-driven-development` skill,
`.claude/skills/spec-driven-development/SKILL.md`). Slicing decides the order of
work, never the shape of modules, services or schema.

## When to Use

- Implementing any multi-file change
- Building a feature from a task breakdown (`.agents/plans/todo.md`)
- Refactoring existing code
- Any time you are tempted to write more than about 100 lines before running tests

**When NOT to use:** single-file, single-function changes whose scope is already minimal.

## The Increment Cycle

```
┌──────────────────────────────────────┐
│                                      │
│   Implement ──→ Test ──→ Verify ──┐  │
│       ▲                           │  │
│       └───── Commit ◄─────────────┘  │
│              │                       │
│              ▼                       │
│          Next slice                  │
│                                      │
└──────────────────────────────────────┘
```

For each slice:

1. **Implement** the smallest complete piece of functionality
2. **Test** — run the relevant tests (write one first if none exists; see the
   `test-driven-development` skill, `.claude/skills/test-driven-development/SKILL.md`)
3. **Verify** — tests pass, gates exit 0, the behaviour works in `python dev.py serve`
4. **Commit** — one Conventional Commit in English imperative, with its
   `CHANGELOG.md` entry under `## [Unreleased]` (see the
   `git-workflow-and-versioning` skill,
   `.claude/skills/git-workflow-and-versioning/SKILL.md`)
5. **Move to the next slice** — carry forward, do not restart

## Slicing Strategies

### Vertical Slices (Preferred)

Build one complete path through the stack:

```
Slice 1: Create a task (migration + model + service + FormRequest + controller + Forge view)
    → Tests pass, a user can create a task from the form

Slice 2: List tasks (query + policy + Resource + view)
    → Tests pass, a user sees only their own tasks

Slice 3: Edit a task (update service method + FormRequest + view)
    → Tests pass, a user can modify a task

Slice 4: Archive a task (soft delete + confirmation + restore)
    → Tests pass, full lifecycle complete without physical deletes
```

Each slice delivers working end-to-end behaviour. When a slice is a plain CRUD,
start from `python dev.py make:crud` rather than writing the boilerplate by hand,
then adapt what it generated.

### Contract-First Slicing

When the JSON API and its consumer (a Forge view with vanilla JS, a mobile client,
another module) are developed in parallel:

```
Slice 0: Define the contract (Resource fields, error codes + message keys, route paths)
Slice 1a: Implement the endpoint against the contract + HTTP tests
Slice 1b: Implement the consumer against fixture data matching the contract
Slice 2: Integrate and test end to end
```

### Risk-First Slicing

Tackle the riskiest or most uncertain piece first:

```
Slice 1: Prove the payment gateway plugin can authorize a sandbox charge (highest risk)
Slice 2: Build the checkout service on the proven plugin
Slice 3: Add retries through a queued job and webhook reconciliation
```

If Slice 1 fails, you learn it before investing in Slices 2 and 3.

## Implementation Rules

### Rule 0: Simplicity First

Before writing code, ask: "What is the simplest thing that could work?"

After writing it, review it:
- Can this be done in fewer lines?
- Are these abstractions earning their complexity?
- Would a staff engineer ask "why didn't you just..."?
- Am I building for hypothetical future requirements or for this task?
- Does the engine already ship this (CRUD builder, FormRequest, Gate/Policy,
  queues, events, cache)?

```
SIMPLICITY CHECK:
✗ A generic event bus with a middleware pipeline for one notification
✓ Dispatch one queued job, or one call to the service that sends it

✗ An abstract factory for two similar services
✓ Two straightforward services sharing a small helper

✗ A config-driven form builder for three forms
✓ Three FormRequests and three Forge views
```

Three similar lines beat a premature abstraction. Implement the naive,
obviously-correct version first, and optimize only once tests prove it correct.
Simplicity never trims what the governance requires: type hints, docstrings,
translation keys, validation, authorization and `@csrf` are part of "works".

### Rule 0.5: Scope Discipline

Touch only what the task requires.

Do NOT:
- "Clean up" code next to your change
- Reorder imports in files you are not otherwise modifying
- Remove comments you do not fully understand
- Add features that are not in the spec because they "seem useful"
- Modernize syntax in files you are only reading

If you notice something worth improving outside the task, write it down instead:

```
NOTICED BUT NOT TOUCHING:
- app/Services/ReportService.py is at 340 lines, over the service cap (separate task)
- The login error flash uses a key with no es row (separate task)
→ Want me to create tasks for these?
```

### Rule 1: One Thing at a Time

Each increment changes one logical thing. Do not mix concerns.

**Bad:** one commit that adds a controller, refactors an existing service and
changes CI configuration.

**Good:** three separate commits, one per change.

### Rule 2: Keep It Green

After each increment, `python -m pytest tests` passes, `python dev.py migrate`
applies cleanly, and both gates exit 0. Never leave the codebase broken between
slices.

### Rule 3: Feature Flags for Incomplete Features

If a feature is not ready for users but its increments need to merge, hide it
behind a flag read from configuration:

```python
from craft.facades import Config


def is_task_sharing_enabled() -> bool:
    """Return whether the unfinished task sharing feature is exposed.

    Returns:
        True only when the flag is explicitly enabled in configuration.
    """
    return bool(Config.get("features.task_sharing", False))
```

Gate the route registration or the controller action on it, and hide the entry
point in the Forge view the same way. Small increments merge to the main branch
without exposing incomplete work.

### Rule 4: Safe Defaults

New code defaults to safe, conservative behaviour:

```python
def create_task(data: TaskInput, *, notify: bool = False) -> Task:
    """Create a task for the current tenant.

    Args:
        data: Validated task attributes.
        notify: Whether assignees are notified. Off unless the caller opts in.

    Returns:
        The persisted task.
    """
    ...
```

Opt-in notifications, deny-by-default policies, private-by-default visibility,
and personal data collected only when the feature actually needs it.

### Rule 5: Rollback-Friendly

Each increment is independently revertable:

- Additive changes (new files, new functions, new nullable columns) are easy to revert
- Changes to existing code stay minimal and focused
- Migrations are **forward-only** once released: each defines `down()` so an
  unreleased migration can be rolled back locally with `python dev.py migrate:rollback`,
  but a shipped mistake is fixed by a new migration. `migrate:fresh`,
  `migrate:reset`, `migrate:refresh`, `db:wipe` and `db:drop` are never used
- Renames and type changes follow expand, migrate, contract across releases, never
  a drop in the same release that adds
- Do not delete something and replace it in the same commit; separate them

## Working with Agents

When directing an agent to implement incrementally:

```
"Let's implement Task 3 from .agents/plans/todo.md.

Start with just the migration, the model and the service method, with their
unit tests. Don't touch the controller or the Forge view yet — that is the
next increment.

After implementing, run python -m pytest tests and both gates in
.claude/rules/ to verify nothing is broken."
```

State explicitly what is in scope and what is NOT in scope for each increment.

## Increment Checklist

After each increment, verify with the project's own commands:

- [ ] The change does one thing and does it completely
- [ ] All existing tests still pass: `python -m pytest tests`
- [ ] Migrations apply: `python dev.py migrate` then `python dev.py migrate:status`
- [ ] Framework lint passes where engine code changed: `ruff check engine`
- [ ] Type checking passes, where the project runs `mypy`
- [ ] Language gate exits 0: `python .claude/rules/lint_language.py`
- [ ] Structure gate exits 0: `python .claude/rules/lint_structure.py`
- [ ] Every new user-facing string is a translation key with `en`, `pt-BR` and `es` rows
- [ ] The new behaviour works as expected
- [ ] `CHANGELOG.md` has the entry, and the change is committed with a Conventional Commit message

**Note:** run each verification command after a change that could affect it.
After a successful run, do not repeat the same command unless the code changed
since; re-running on unchanged code adds no information.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "I'll test it all at the end" | Bugs compound. A bug in Slice 1 makes Slices 2-5 wrong. Test each slice. |
| "It's faster to do it all at once" | It *feels* faster until something breaks and you cannot tell which of 500 changed lines did it. |
| "These changes are too small to commit separately" | Small commits are free. Large commits hide bugs and make rollbacks painful. |
| "I'll add the feature flag later" | If the feature is incomplete, it must not be user-visible. Add the flag now. |
| "This refactor is small enough to include" | Refactors mixed with features make both harder to review and debug. Separate them. |
| "I'll seed the other two locales at the end" | A key with fewer than three rows is unfinished, and the end is where it gets forgotten. Same increment. |
| "I'll just reset the database to get a clean state" | Destructive migration commands are banned in every environment. Write a forward migration or fix the seed. |
| "Let me run the tests again just to be sure" | After a successful run, repeating the same command adds nothing unless the code changed since. |

## Red Flags

- More than 100 lines written without running tests
- Several unrelated changes in one increment
- "Let me just quickly add this too" scope expansion
- Skipping the test or verify step to move faster
- Tests or gates broken between increments
- Large uncommitted changes accumulating
- Abstractions built before the third use case demands them
- Touching files outside the task scope "while I'm here"
- New utility modules for one-time operations, or cross-cutting logic copied into a module instead of a plugin
- A destructive migration command, or a physical delete on a business entity, used to "unblock" a slice
- Running the same build or test command twice in a row with no code change in between

## Verification

After completing every increment of a task:

- [ ] Each increment was individually tested and committed
- [ ] The full suite passes: `python -m pytest tests`
- [ ] Both gates exit 0
- [ ] The feature works end to end as specified
- [ ] `CHANGELOG.md` describes the change under `## [Unreleased]`
- [ ] No uncommitted changes remain

## See Also

Per-increment verification is the local check. Before declaring a task done,
apply the project-wide Definition of Done as the final gate every increment
clears regardless of the task. See `.claude/references/definition-of-done.md`.
