---
name: git-workflow-and-versioning
description: Disciplined git workflow and release versioning for Craft projects. Use when committing, branching, splitting a messy working tree into atomic commits, opening or reviewing a pull request, working in parallel streams, cutting a release, choosing a version bump, tagging, or writing a changelog entry.
---

# Git Workflow and Versioning

## Overview

Git is the safety net. Commits are save points, branches are sandboxes, and history is
documentation. When an agent can generate a hundred lines a minute, disciplined version
control is the only thing that keeps change reviewable and reversible.

In a Craft project the git discipline is tied to the release non-regression laws: every
change carries its `CHANGELOG.md` entry, the version lives in two files that must agree, the
release counter only ever moves forward by one, and tags follow `vX.Y.Z-rNNNNN`. This skill
covers both halves: how work flows into history, and how history becomes a release.

## When to Use

Always. Every code change flows through git. Specifically:

- Before and after every slice of implementation (commit the save point)
- When the working tree has grown into an unreviewable mix of concerns
- When opening, updating or reviewing a pull request
- When running several agents or features in parallel
- When cutting a release, choosing a semantic version bump, tagging, or editing the changelog

## Core Principles

### Trunk-Based Development (recommended)

Keep the default branch (`main` or `master`, whichever the repository uses) always
deployable. Work on short-lived branches that merge back within one to three days.
Long-lived branches are hidden costs: they diverge, collect conflicts and postpone
integration until it hurts.

```
main ──●──●──●──●──●──●──●──●──●──  (always deployable)
        ╲      ╱  ╲    ╱
         ●──●─╱    ●──╱    <- short-lived branches (1-3 days)
```

Teams on a different branching model can keep it; the commit discipline below (atomic,
small, well described) matters more than the topology.

- **Development branches are costs.** Every day a branch lives it accumulates merge risk.
- **Release branches are acceptable** when a release must stabilize while the trunk moves on.
- **Feature flags beat long branches.** Merge incomplete work behind a flag instead of
  parking it on a branch for weeks (see the `ci-cd-and-automation` skill,
  `.claude/skills/ci-cd-and-automation/SKILL.md`).

### 1. Commit Early, Commit Often

Each verified increment gets its own commit. Never let a large uncommitted diff build up.

```
Work pattern:
  Implement slice -> Test -> Run gates -> Commit -> Next slice

Not this:
  Implement everything -> Hope it works -> Giant commit
```

If the next change breaks something, the last commit is a known-good state one command away.

### 2. Atomic Commits

Each commit does one logical thing and leaves the suite green:

```
# Good: each commit stands on its own
git log --oneline
a1b2c3d feat(tasks): add TaskCreateRequest validation
d4e5f6a feat(tasks): add task creation endpoint to routes/api.py
b7c8d9e feat(tasks): seed translation keys for task validation errors
f1a2b3c test(tasks): cover task creation happy path and validation errors

# Bad: everything mixed together
x1y2z3a add task feature, fix sidebar, bump deps, refactor helpers
```

### 3. Descriptive Messages — Conventional Commits, English, Imperative

Messages explain *why*, not what the diff already shows. Craft projects use Conventional
Commits in English imperative mood — the language gate treats commit text as a committed
artifact like any other.

```
# Good: explains intent
feat(auth): reject malformed email addresses at registration

Invalid addresses were reaching the users table and failing later in
the mailer. Validation now lives in RegisterRequest, consistent with the
other FormRequest classes under app/Http/Requests/Auth/. Failures return
code VALIDATION_FAILED with message_key validation.email.invalid.

# Bad: restates the diff
update RegisterRequest.py
```

**Format:**

```
<type>(<optional scope>): <short imperative description>

<optional body: why, trade-offs, what a reviewer should check>
```

**Types:**

| Type | Use for |
|---|---|
| `feat` | New capability |
| `fix` | Bug fix |
| `refactor` | Change that neither fixes a bug nor adds a feature |
| `perf` | Performance improvement with no behavior change |
| `test` | Adding or correcting tests |
| `docs` | Documentation only |
| `chore` | Tooling, dependencies, configuration |
| `ci` | Pipeline changes under `.github/workflows/` |
| `security` or `fix(security)` | Hardening or a closed vulnerability (use whichever the repository already uses) |

Breaking changes carry `!` after the type (`feat(orm)!: ...`) and a `BREAKING CHANGE:`
footer that names the migration path.

### 4. Keep Concerns Separate

Never combine formatting with behavior, or a refactor with a feature. Each is a separate
commit, and ideally a separate pull request:

```
# Good: separate concerns
git commit -m "refactor(billing): extract bank slip barcode builder into app/plugins/"
git commit -m "feat(billing): add due date to generated bank slips"

# Bad: mixed concerns
git commit -m "refactor barcode and add due date"
```

A trivial rename inside a feature commit is acceptable at the reviewer's discretion; anything
a reviewer has to reason about separately gets its own commit.

### 5. Size the Change

Target around 100 changed lines per commit or pull request. Split anything approaching 1000.
The splitting strategies live in the `code-review-and-quality` skill
(`.claude/skills/code-review-and-quality/SKILL.md`).

```
~100 lines  -> easy to review, easy to revert
~300 lines  -> acceptable for one logical change
~1000 lines -> split before asking for review
```

Craft's layer caps help here: a controller that would pass 150 lines, or an action past 15,
is already a signal that the change is doing more than one thing.

### 6. Every Change Carries Its Changelog Entry

This is a non-regression law, not a courtesy. The commit or pull request that changes
`engine/`, `app/`, `bootstrap/`, `config/`, `database/`, `routes/` or `dev.py` adds its line
under `## [Unreleased]` in `CHANGELOG.md`, in the Keep a Changelog category that fits
(`Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`). It is never batched at
release time and never reconstructed from `git log`.

```markdown
## [Unreleased]

### Fixed

- `RegisterRequest` rejected valid addresses containing `+`; the pattern now
  follows RFC 5322 local-part rules (`app/Http/Requests/Auth/RegisterRequest.py`).
```

A `Security` entry states the exposure ("X could bypass Y because Z"), not just the patch.

## Branching Strategy

### Feature Branches

```
main (always deployable)
  │
  ├── feat/task-creation      <- one concern per branch
  ├── feat/user-settings      <- parallel work
  └── fix/duplicate-tasks     <- bug fix
```

- Branch from the default branch
- Merge within one to three days; delete the branch after merge
- Prefer a feature flag over keeping an incomplete feature on a branch
- Rebase or merge the default branch in daily so conflicts stay small

### Branch Naming

English, kebab-case, `type/short-description`:

```
feat/<short-description>      -> feat/task-creation
fix/<short-description>       -> fix/duplicate-tasks
chore/<short-description>     -> chore/bump-psycopg2
refactor/<short-description>  -> refactor/auth-module
docs/<short-description>      -> docs/deployment-runbook
```

## Working with Worktrees

For parallel agent work, git worktrees give every branch its own directory:

```bash
# One worktree per branch
git worktree add ../project-task-creation feat/task-creation
git worktree add ../project-user-settings feat/user-settings

# Each directory has its own branch; agents do not step on each other
ls ../
  project/                  <- default branch
  project-task-creation/    <- feat/task-creation
  project-user-settings/    <- feat/user-settings

# After merging, clean up
git worktree remove ../project-task-creation
```

Benefits:

- Several agents can build different features at the same time
- No branch switching, no stash juggling
- A failed experiment is one `git worktree remove` away, with nothing lost elsewhere
- Changes stay isolated until they are explicitly merged

Each worktree needs its own virtual environment and its own test database settings if the
suite runs against PostgreSQL; the default SQLite test run is already isolated per checkout.

## The Save Point Pattern

```
Agent starts work
    │
    ├── Makes a change
    │   ├── Tests and gates pass? -> Commit -> Continue
    │   └── Something fails?      -> Return to the last commit -> Investigate
    │
    ├── Makes another change
    │   ├── Tests and gates pass? -> Commit -> Continue
    │   └── Something fails?      -> Return to the last commit -> Investigate
    │
    └── Feature complete -> the commits form a clean, readable history
```

You never lose more than one increment. Returning to the last save point
(`git restore .` for unstaged edits, or `git reset --hard HEAD`) is destructive to
uncommitted work: confirm there is nothing worth keeping first, and never run it on someone
else's changes.

## Change Summaries

After any modification, report a structured summary. It gives the reviewer a map and
surfaces unintended edits:

```
CHANGES MADE:
- app/Http/Requests/Tasks/TaskCreateRequest.py: added title and due_at rules
- routes/api.py: registered POST /api/v1/tasks
- database/seeders/TranslationSeeder.py: added validation.task.title_required (en, pt-BR, es)
- CHANGELOG.md: Added entry under [Unreleased]

THINGS I DIDN'T TOUCH (intentionally):
- app/Http/Requests/Auth/RegisterRequest.py: similar validation gap, separate change
- app/Http/Controllers/TaskController.py: error payload shape could be unified, separate task

POTENTIAL CONCERNS:
- due_at is validated as UTC ISO 8601; clients sending local time will be rejected
- No new dependency added
```

The "didn't touch" section proves scope discipline: it shows you saw adjacent problems and
chose not to renovate them uninvited.

## Pre-Commit Hygiene

Before every commit:

```bash
# 1. Read exactly what is staged
git diff --staged

# 2. No secrets, keys or real personal data in the diff
git diff --staged | grep -iE "password|secret|api_key|token|BEGIN .*PRIVATE KEY"

# 3. Tests
python -m pytest tests

# 4. Lint
ruff check engine        # or `ruff check .` in an application repository

# 5. Governance gates
python .claude/rules/lint_language.py
python .claude/rules/lint_structure.py

# 6. Version and changelog invariants when release files changed
python -m pytest tests/test_release_non_regression.py
```

Automate the cheap checks with `pre-commit`. A local hook that runs the language gate looks
like this (point `entry` at wherever the gate lives in the repository):

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: language-standard
        name: English-only code and zero hardcoded copy
        entry: python .claude/rules/lint_language.py
        language: system
        pass_filenames: false
      - id: structure-standard
        name: Layer caps and structural rules
        entry: python .claude/rules/lint_structure.py
        language: system
        pass_filenames: false
```

Never bypass a hook with `--no-verify`. If a hook fails, the output is what gets fixed.

## Handling Generated Files

- **Commit** what the project expects to be versioned: migrations under
  `database/migrations/`, seeders, vendored static `.js`/`.css`, lock or pinned requirement
  files if the project keeps them
- **Do not commit** `.env`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`,
  virtual environments, `dist/`, `build/`, `*.egg-info/`, coverage output, generated
  documentation builds, or editor settings that are not shared
- **Keep a `.gitignore`** that covers at least: `.env`, `.env.*` (except `.env.example`),
  `.venv/`, `__pycache__/`, `*.pyc`, `dist/`, `*.pem`, `*.key`, `.coverage`, `htmlcov/`

## Using Git for Debugging

```bash
# Find the commit that introduced a regression
git bisect start
git bisect bad HEAD
git bisect good v3.19.0-r00012
git bisect run python -m pytest tests/test_orders.py -x -q

# What changed recently
git log --oneline -20
git diff HEAD~5..HEAD -- app/

# Who last changed a line, and why
git blame app/Services/OrderService.py

# Search history by message
git log --grep="bank_slip" --oneline
```

`git bisect run` with a single failing test is the fastest regression hunt there is; pair it
with the `debugging-and-error-recovery` skill
(`.claude/skills/debugging-and-error-recovery/SKILL.md`).

## Release and Versioning

Commits are how *you* track change; a version is how *consumers* track it. The moment anyone
depends on the code — another service, an installed package, a deployed tenant — "latest on
main" no longer answers "what am I running and is it safe to upgrade?". The version number,
the release counter, the tag and the changelog together are that answer.

### Semantic Versioning

Version everything with consumers as `MAJOR.MINOR.PATCH`:

```
  MAJOR  breaking change — consumers must change code or data to upgrade
  MINOR  new functionality, backward-compatible — safe to upgrade
  PATCH  bug fix, backward-compatible — safe to upgrade
```

The number is a promise. A patch that changes behavior consumers relied on is a major change
in disguise (Hyrum's Law — see the `api-and-interface-design` skill,
`.claude/skills/api-and-interface-design/SKILL.md`). In a Craft project the public contract
includes the facades in `craft.facades`, the container binding keys (`db`, `router`, `view`,
`auth`, `antispam`, `firewall`, ...), CLI command names, translation keys, error `code`
values and API field names. Changing any of those without a deprecation window is a major
bump. When unsure, assume breaking.

### The Release Counter

On top of the semantic version, Craft carries a monotonic release counter:

- `__release__ = "rNNNNN"` in `engine/__init__.py` (or the application's equivalent)
- It increments by **exactly one** on every cut release, whatever the semantic bump
- It is never reset, never skipped, never decremented

```
v3.19.0-r00012  ->  v3.19.1-r00013   (patch, counter +1)
v3.19.1-r00013  ->  v4.0.0-r00014    (major, counter still +1)
```

### Cutting a Release

The version lives in two files that must agree, and the changelog header must match both:

1. **Fold the changelog.** Rename `## [Unreleased]` to `## [X.Y.Z] rNNNNN — YYYY-MM-DD` and
   open a fresh, empty `## [Unreleased]` directly above it.
2. **Bump the version** in `pyproject.toml` (`[project].version`) and in `engine/__init__.py`
   (`__version__`), and increment `__release__` by one.
3. **Run the gates** — the non-regression test asserts the version sync, the `rNNNNN` format
   and that the changelog contains both `## [X.Y.Z] rNNNNN` and `## [Unreleased]`:

   ```bash
   python -m pytest tests
   python -m pytest tests/test_release_non_regression.py
   ruff check engine
   python .claude/rules/lint_language.py
   python .claude/rules/lint_structure.py
   ```

4. **Commit** in one concern: `chore(release): cut vX.Y.Z-rNNNNN`.
5. **Tag** with an annotated tag in the exact scheme, and push it:

   ```bash
   git tag -a v3.21.0-r00014 -m "Release 3.21.0 (r00014)"
   git push origin v3.21.0-r00014
   ```

If the pipeline creates the tag from the files (reading `pyproject.toml` and
`engine/__init__.py` and failing when they disagree), do not also tag by hand — pick one
source of truth and let the other be derived. Either way the tag, both files and the
changelog header can never disagree.

### Keep a Changelog Written for Humans

A changelog is not `git log`. It is the curated answer to "what changed, and do I care?" —
newest release on top, grouped by `Added / Changed / Deprecated / Removed / Fixed / Security`,
each entry phrased around consumer impact.

```markdown
## [3.21.0] r00014 — 2026-09-20

### Added
- Bulk task import from CSV at `POST /api/v1/tasks/import`, validated by `TaskImportRequest`.

### Fixed
- Recurring scheduled tasks drifted by the server's UTC offset after a restart.

### Deprecated
- `OrderService.total()` — use `OrderService.calculate_total_cents()`; the alias is removed in the next release.
```

Write the entry in the same change as the code, while the impact is fresh. Breaking changes
get a migration note and a deprecation window (the `deprecation-and-migration` skill,
`.claude/skills/deprecation-and-migration/SKILL.md`); shipping the release is the
`shipping-and-launch` skill's job (`.claude/skills/shipping-and-launch/SKILL.md`).

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "I'll commit when the feature is done" | One giant commit cannot be reviewed, bisected or reverted cleanly. Commit each slice. |
| "The message doesn't matter" | Messages are documentation. The next engineer or agent needs the why. |
| "I'll squash it all later" | Squashing destroys the narrative. Build a clean incremental history from the start. |
| "Branches add overhead" | Short-lived branches are free. Long-lived ones are the cost — merge within days. |
| "I'll split this change later" | Big changes are harder to review, riskier to deploy, harder to revert. Split before review. |
| "I don't need a .gitignore" | Until `.env` with production credentials lands in history. Set it up on day one. |
| "It's a tiny fix, bump the patch" | Check what consumers can observe. A behavior they relied on changing is a major, whatever the diff size. |
| "The changelog is just the commit log" | Commits are for authors; the changelog is for consumers, curated by impact. |
| "I'll write the changelog at release time" | It is a non-regression law to write it with the change. Reconstructed entries miss half the impact. |
| "The counter doesn't matter for a patch" | The counter moves +1 on every cut release. A skipped or reused counter breaks traceability. |
| "I'll bump the version in pyproject.toml only" | The non-regression test fails and the release job refuses a mismatch. Both files, same commit. |

## Red Flags

- Large uncommitted changes accumulating across several concerns
- Commit messages like "fix", "update", "misc", or in any language other than English
- Formatting changes mixed with behavior changes
- A change to application or engine code with no `CHANGELOG.md` entry under `[Unreleased]`
- No `.gitignore`, or `.env`, virtual environments or build output committed
- Long-lived branches diverging significantly from the default branch
- Force-pushing to shared branches, or `--no-verify` to get past a hook
- A breaking change shipped under a minor or patch bump
- `pyproject.toml` and `engine/__init__.py` disagreeing on the version
- A release counter that was reset, skipped, reused or decremented
- A tag that does not follow `vX.Y.Z-rNNNNN`, or a release with no tag at all
- A changelog that is just pasted commit messages

## Verification

For every commit:

- [ ] The commit does one logical thing and the suite is green at that commit
- [ ] Message is a Conventional Commit in English imperative and explains the why
- [ ] `python -m pytest tests`, `ruff check`, `lint_language.py` and `lint_structure.py` pass
- [ ] No secrets or real personal data in the diff
- [ ] No formatting-only changes mixed with behavior changes
- [ ] `CHANGELOG.md` has the entry under `## [Unreleased]` in the right category
- [ ] `.gitignore` covers the standard exclusions

For every release:

- [ ] The bump matches the change: breaking -> major, additive -> minor, fix -> patch
- [ ] `pyproject.toml` version equals `engine/__init__.py` `__version__`
- [ ] `__release__` is exactly the previous counter plus one
- [ ] `CHANGELOG.md` has `## [X.Y.Z] rNNNNN — YYYY-MM-DD` and a fresh empty `## [Unreleased]` above it
- [ ] `tests/test_release_non_regression.py` passes
- [ ] The tag is `vX.Y.Z-rNNNNN`, annotated, and created from one source of truth
