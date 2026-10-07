---
description: Implement tasks incrementally — test, build, verify, commit. Add "auto" to run the whole plan after one approval.
argument-hint: [auto]
---

Apply the `incremental-implementation` skill (`.claude/skills/incremental-implementation/SKILL.md`)
together with the `test-driven-development` skill (`.claude/skills/test-driven-development/SKILL.md`).

## Modes

- **`/build`** — implement the *next* pending task, then stop (careful, one slice at a time).
- **`/build auto`** — generate the plan if needed, get a single approval, then
  implement *every* task without stopping between them.

`$ARGUMENTS` selects the mode. Treat `auto` (canonical) or `all` as autonomous
mode; anything else, or nothing, is single-task mode. Autonomous mode is not
faster *per task* — it runs the same test-driven loop — it only removes the human
stepping *between* tasks.

## Before any task

The architecture must already be confirmed in the spec: modules, services,
plugins and data shape. If a task would require deciding one of those, stop and
ask; do not decide it while coding.

If `CONSTRAINTS.md` exists at the repository root, read it and respect it. Never
weaken it, `.claude/rules/` or a gate configuration to make a task pass.

## Default: one task

Pick the next pending task from `.agents/plans/todo.md` (or the designated tracker). Then:

1. Read the task's acceptance criteria
2. Load the relevant context (neighbouring modules, services, FormRequests,
   policies, Forge views, existing tests)
3. Write a failing pytest test for the expected behaviour (RED)
4. Implement the minimum code to pass it (GREEN), within the layer caps: typed
   signatures, Google docstrings, no SQL in controllers or services, no HTML in
   Python, services resolved from the container, user-facing text as translation
   keys seeded for `en`, `pt-BR` and `es`
5. Apply migrations forward with `python dev.py migrate` when the task adds one
6. Run the full suite: `python -m pytest tests`
7. Run the gates: `python .claude/rules/lint_language.py` and
   `python .claude/rules/lint_structure.py` (plus `ruff check engine` when
   framework code changed)
8. Add the `CHANGELOG.md` entry under `## [Unreleased]`
9. Commit with a Conventional Commit message in English imperative
10. Mark the task complete in the task list and stop

## Autonomous: the whole plan (`/build auto`)

Use this once a spec exists and you want plan and build collapsed into one run. It
removes the manual stepping between tasks — **not** the verification. Every task
still earns a passing test and its own commit.

1. **Require a spec.** Look only at known paths: `.agents/plans/SPEC.md`, or
   `.agents/plans/SPEC-<module-id>.md` indexed by `.agents/plans/CAPABILITY-MAP.md`.
   A README or an arbitrary document does **not** count. If none exists, stop and
   tell the user to run `/spec` first — do not invent requirements.
2. **Establish a clean baseline.** Run `git status --porcelain`. If there are
   uncommitted changes outside the planning artifacts under `.agents/plans/`, stop
   and ask the user to commit, stash, or say how to handle them. Per-task commits
   must not absorb unrelated local work, or the clean-rollback guarantee breaks.
3. **Plan if needed.** If `.agents/plans/plan.md` does not exist, apply the
   `planning-and-task-breakdown` skill
   (`.claude/skills/planning-and-task-breakdown/SKILL.md`) to generate it.
4. **Single checkpoint.** Present the full plan and wait for an unambiguous
   affirmative ("approve", "go", "yes"). Hedged replies ("looks reasonable",
   "I guess") are **not** approval. This is the only human gate. If you generated
   the plan, commit it now as one preparatory commit so it does not bleed into the
   first task's commit.
5. **Execute every task in dependency order.** Use each task's declared
   dependencies; if none are explicit, follow the plan's order. For each task run
   the full default loop above (RED → GREEN → migrate → suite → gates → changelog →
   commit → mark complete). Stage only the files that task touched plus its
   task-status update — never `git add -A` blindly — and make one commit per task so
   every point is a clean rollback.
6. **Stop and ask the user** (do not push through) when:
   - a test cannot be made to pass or a gate stays red without an obvious fix →
     follow the `debugging-and-error-recovery` skill
     (`.claude/skills/debugging-and-error-recovery/SKILL.md`)
   - the spec is ambiguous, or a task needs a decision the spec does not cover
     (including an architecture decision)
   - a task is high-risk or irreversible — authentication, Gate/Policy or
     permission changes, data migrations over existing rows, payments, anything
     touching personal data or secrets, deploys, release cuts, **or anything
     `git revert` cannot undo** → follow the `doubt-driven-development` skill
     (`.claude/skills/doubt-driven-development/SKILL.md`) and get explicit sign-off
   - a step would need a banned operation (`migrate:fresh`, `migrate:reset`,
     `migrate:refresh`, `db:wipe`, `db:drop`, a physical delete of a business
     entity) — never run it; find the forward-only path or ask

   After the user resolves a blocker, they re-invoke `/build auto`; it resumes from
   the next pending task.
7. **Summarize at the end:** tasks completed, tests added, migrations created,
   translation keys added, commits made, and anything skipped, flagged or left for
   the user.

If any step fails, follow the `debugging-and-error-recovery` skill
(`.claude/skills/debugging-and-error-recovery/SKILL.md`).
