---
name: planning-and-task-breakdown
description: Breaks approved work into small, ordered, verifiable tasks. Use when a spec or clear requirements exist and must become implementable tasks, when a task feels too large to start, when scope must be estimated, or when work could run in parallel.
---

# Planning and Task Breakdown

## Overview

Decompose work into small, verifiable tasks with explicit acceptance criteria. A
good breakdown is the difference between an agent that finishes reliably and one
that leaves a tangle behind. Every task must be small enough to implement, test
and verify in one focused session.

On a Craft Engine project the plan starts from an **approved architecture**:
modules, services, plugin boundaries and data shape come from the spec (see the
`spec-driven-development` skill, `.claude/skills/spec-driven-development/SKILL.md`).
If the spec does not fix them, stop and settle them before slicing tasks.

## When to Use

- A spec exists and must be broken into implementable units
- A task feels too large or too vague to start
- Work must be parallelized across agents or sessions
- Scope needs to be communicated to a human
- The implementation order is not obvious

**When NOT to use:** single-file changes with obvious scope, or when the spec
already contains well-defined tasks.

## The Planning Process

### Step 1: Enter Plan Mode

Before any code, work read-only:

- Read the spec and the relevant parts of the codebase
- Identify existing patterns: how neighbouring modules structure controllers,
  services, FormRequests, Resources, policies and Forge views
- Check what the engine already ships (CRUD builder via `python dev.py make:crud`,
  generators such as `make:model`, `make:migration`, `make:service`,
  `make:request`, `make:policy`) so tasks reuse it instead of hand-rolling it
- Map dependencies between components
- Note risks and unknowns

**Do NOT write code during planning.** The output is a plan document saved to
`.agents/plans/plan.md` and a task list recorded in the task list target (see
Output Files; default `.agents/plans/todo.md`), not an implementation. Planning
artifacts live at the repository root, never inside `data/`.

### Step 2: Identify the Dependency Graph

Map what depends on what:

```
Migration (database/migrations)
    │
    ├── Model (app/Models) + translation key seed rows
    │       │
    │       ├── Repository / query layer
    │       │       │
    │       │       └── Domain service (app/Services, resolved from the container)
    │       │               │
    │       │               ├── Controller + FormRequest + Resource
    │       │               │       │
    │       │               │       └── Routes (routes/web.py, routes/api.py)
    │       │               │               │
    │       │               │               └── Forge views + vanilla JS/CSS
    │       │               │
    │       │               └── Jobs / events / listeners
    │       │
    │       └── Policy (Gate authorization)
    │
    └── Seeders / factories
```

Implementation order follows the graph bottom-up: foundations first.

### Step 3: Slice Vertically

Do not build all the schema, then all the services, then all the views. Build one
complete feature path at a time.

**Bad (horizontal slicing):**
```
Task 1: Write every migration
Task 2: Write every service
Task 3: Write every controller and route
Task 4: Write every view and wire it up
```

**Good (vertical slicing):**
```
Task 1: Customer can register (users migration + service + FormRequest + controller + view)
Task 2: Customer can sign in (session guard wiring + controller + view)
Task 3: Customer can create an order (orders migration + service + API route + view)
Task 4: Customer can list their orders (query + policy + Resource + view)
```

Each vertical slice delivers working, testable behaviour end to end.

### Step 4: Write Tasks

Every task follows this structure, whether it goes into the markdown task list or
into an external tracker item (see Output Files):

```markdown
## Task [N]: [Short descriptive title]

**Description:** One paragraph explaining what this task accomplishes.

**Acceptance criteria:**
- [ ] [Specific, testable condition]
- [ ] [Specific, testable condition]

**Verification:**
- [ ] Focused tests pass: `python -m pytest tests/test_orders.py`
- [ ] Full suite passes: `python -m pytest tests`
- [ ] Gates clean: `python .claude/rules/lint_language.py` and `python .claude/rules/lint_structure.py`
- [ ] Manual check: [what to verify in the running app, `python dev.py serve`]

**Dependencies:** [Task numbers this depends on, or "None"]

**Files likely touched:**
- `database/migrations/<timestamp>_create_orders_table.py`
- `app/Services/OrderService.py`
- `tests/test_orders.py`

**Estimated scope:** [Small: 1-2 files | Medium: 3-5 files | Large: 5+ files]
```

Tasks that introduce user-facing text list the translation keys they create, and
their seed rows for `en`, `pt-BR` and `es` belong to the same task. Tasks that
change behaviour include their `CHANGELOG.md` entry under `## [Unreleased]`.

### Step 5: Order and Checkpoint

Arrange tasks so that:

1. Dependencies are satisfied (foundation first)
2. Each task leaves the system in a working state, with migrations applied forward
3. A verification checkpoint follows every 2-3 tasks
4. High-risk tasks come early (fail fast): a new plugin integration, a dialect-sensitive
   query, a data migration over existing rows

Add explicit checkpoints to the task list target:

```markdown
## Checkpoint: After Tasks 1-3
- [ ] `python -m pytest tests` passes
- [ ] `ruff check engine` passes (framework work) and both gates exit 0
- [ ] `python dev.py migrate:status` shows every migration applied
- [ ] Core user flow works end to end in `python dev.py serve`
- [ ] Review with the human before proceeding
```

## Task Sizing Guidelines

| Size | Files | Scope | Example |
|------|-------|-------|---------|
| **XS** | 1 | Single function or config change | Add a validation rule to a FormRequest |
| **S** | 1-2 | One component or endpoint | Add a JSON endpoint with its Resource |
| **M** | 3-5 | One feature slice | Customer registration flow |
| **L** | 5-8 | Multi-component feature | Search with filtering and pagination |
| **XL** | 8+ | **Too large — break it down further** | — |

An L or larger task is split. Agents perform best on S and M tasks. Remember that
the layer caps make oversized files a defect on their own: a controller over 150
lines or a service over 300 is split in the same task that grew it.

**When to break a task down further:**
- It would take more than one focused session (roughly 2+ hours of agent work)
- Its acceptance criteria do not fit in 3 bullets or fewer
- It touches two or more independent subsystems (for example auth and billing)
- Its title contains "and" (a sign it is two tasks)

## Output Files

- **Plan document:** `.agents/plans/plan.md`. Always markdown: design decisions,
  risks and open questions do not map cleanly onto individual tracker items.
- **Task list:** each task goes to the **task list target** defined below.

Create `.agents/plans/` at the repository root if it does not exist.

**Never overwrite an incomplete plan.** Before writing `.agents/plans/plan.md` or
`.agents/plans/todo.md`, check whether they exist and still contain unchecked tasks:

- Same work being replanned (the user asked to revise or extend this plan) →
  update the existing files in place.
- Different work → **stop and ask.** The unchecked tasks may be mid-build in
  another session. Do not delete, overwrite or rename the files on your own;
  present the conflict and let the user decide (finish the old plan, explicitly
  discard it, or name where the new plan goes).

The same rule applies to an external tracker: never bulk-close or delete another
plan's open items to make room.

### Task List Target

The task list target is where tasks and checkpoints are recorded. It is defined
here once; every other mention in this skill defers to it.

- **Default: a checklist-style markdown file at `.agents/plans/todo.md`.** This is
  what the `/build` command and other downstream tooling expect. Use it unless the
  project says otherwise.
- **External tracker:** if the project's agent rules (`CLAUDE.md`, `AGENTS.md`) or
  the user designate an issue tracker (for example GitHub Issues), create one item
  per task instead of writing `todo.md`. Map the Step 4 structure onto the
  tracker's fields: acceptance criteria and verification in the item body,
  dependencies through the tracker's linking mechanism ("blocked by"). Record the
  Step 5 checkpoints as items too, or as a checklist in the plan document if the
  tracker has no natural equivalent.

When using an external tracker, say so in `.agents/plans/plan.md` ("Tasks tracked
in GitHub project X") so later steps and sessions know where to look, and keep the
plan's Task List section as an ordered index of item IDs or links, not a duplicate
checklist.

## Plan Document Template

```markdown
# Implementation Plan: [Feature/Project Name]

## Overview
[One paragraph summary of what we're building]

## Architecture Decisions
- [Modules and services involved, and why]
- [Plugins used or introduced, resolved from the container]
- [Schema changes: new tables/columns, forward-only, soft deletes for business entities]
- [Personal data touched and how it is protected — or "none"]

## Task List

### Phase 1: Foundation
- [ ] Task 1: ...
- [ ] Task 2: ...

### Checkpoint: Foundation
- [ ] Tests pass, gates exit 0, migrations applied

### Phase 2: Core Features
- [ ] Task 3: ...
- [ ] Task 4: ...

### Checkpoint: Core Features
- [ ] End-to-end flow works

### Phase 3: Polish
- [ ] Task 5: ...
- [ ] Task 6: ...

### Checkpoint: Complete
- [ ] All acceptance criteria met
- [ ] Every new translation key has en / pt-BR / es rows
- [ ] CHANGELOG.md updated under ## [Unreleased]
- [ ] Ready for review

## Risks and Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| [Risk] | [High/Med/Low] | [Strategy] |

## Open Questions
- [Question needing human input]
```

When tasks live in an external tracker, keep the Task List section as an ordered
index of item IDs or links instead of a duplicate checklist.

## Parallelization Opportunities

When several agents or sessions are available:

- **Safe to parallelize:** independent feature slices in different modules, tests
  for already-implemented behaviour, documentation
- **Must be sequential:** migrations (their timestamps define order), shared
  container bindings or service providers, dependency chains
- **Needs coordination:** features sharing an API contract or a plugin interface
  (define the contract first, then parallelize)

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "I'll figure it out as I go" | That is how you get a tangled mess and rework. Ten minutes of planning saves hours. |
| "The tasks are obvious" | Write them down anyway. Explicit tasks surface hidden dependencies and forgotten edge cases. |
| "Planning is overhead" | Planning is the task. Implementation without a plan is just typing. |
| "I can hold it all in my head" | Context windows are finite. Written plans survive session boundaries and compaction. |
| "The translations and changelog can be a final cleanup task" | A key with fewer than three rows is unfinished, and a change without its changelog entry violates the release standard. They belong to the task that creates them. |
| "The old `plan.md` is stale, I'll just replace it" | Unchecked tasks may be mid-build in another session. Overwriting destroys work state that exists nowhere else. Stop and ask. |

## Red Flags

- Starting implementation without a written task list
- Overwriting a `plan.md` or `todo.md` that still has unchecked tasks for different work, without asking
- Writing `todo.md` when the project designated an external tracker (or scattering tasks across both)
- Plan files saved inside `data/`
- Tasks that say "implement the feature" without acceptance criteria
- No verification steps in the plan
- A task that hand-rolls CRUD the CRUD builder already generates
- All tasks are XL
- No checkpoints between tasks
- Dependency order not considered

## Verification

Before starting implementation, confirm:

- [ ] Every task has acceptance criteria
- [ ] Every task has a verification step
- [ ] Task dependencies are identified and ordered correctly
- [ ] Tasks are recorded in the task list target (default `.agents/plans/todo.md`)
- [ ] No pre-existing incomplete plan was overwritten without explicit user confirmation
- [ ] No task touches more than about 5 files
- [ ] Checkpoints exist between major phases
- [ ] The architecture the plan relies on was approved in the spec
- [ ] The human has reviewed and approved the plan

## See Also

Acceptance criteria are per task and answer "did we build the right thing?". They
sit on top of the project-wide Definition of Done, the standing bar every task
clears before it counts as done. See `.claude/references/definition-of-done.md`.
