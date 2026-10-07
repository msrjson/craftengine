---
description: Break an approved spec into small verifiable tasks with acceptance criteria and dependency ordering
argument-hint: [module id or focus area]
---

Apply the `planning-and-task-breakdown` skill (`.claude/skills/planning-and-task-breakdown/SKILL.md`).

$ARGUMENTS

Read the existing spec (`.agents/plans/SPEC.md`, or `.agents/plans/SPEC-<module-id>.md`
selected through `.agents/plans/CAPABILITY-MAP.md`) and the relevant parts of the
codebase. If the spec does not fix the architecture (modules, services, plugins,
data shape), stop and settle it with the user before planning. If no spec exists,
tell the user to run `/spec` first.

Then:

1. Enter plan mode — read only, no code changes
2. Identify the dependency graph (migration → model → service → controller,
   FormRequest, Resource → routes → Forge views), and what the engine already
   generates (`make:crud` and the other `make:*` generators)
3. Slice work vertically (one complete path per task, not horizontal layers)
4. Write tasks with acceptance criteria and verification steps
   (`python -m pytest tests`, `python .claude/rules/lint_language.py`,
   `python .claude/rules/lint_structure.py`), listing new translation keys and the
   `CHANGELOG.md` entry inside the task that needs them
5. Add checkpoints between phases
6. Present the plan for human review

Save the plan to `.agents/plans/plan.md` and the task list to `.agents/plans/todo.md`
at the repository root (never inside `data/`), unless the project designates an
external tracker.

If `.agents/plans/plan.md` or `.agents/plans/todo.md` already exists with unchecked
tasks for different work, stop and ask before writing — never silently overwrite an
incomplete plan.
