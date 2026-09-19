---
name: using-agent-catalog
description: Routes a piece of work to the right skill, agent or slash command from the Craft Engine agent catalog, and explains how to install them. Use when starting a session, or when you need to decide which workflow applies to the task at hand.
---

# Using the Agent Catalog

## Overview

The Craft Engine agent catalog is a set of engineering workflows organized by
development phase. It ships three kinds of installable entries plus shared references:

| Kind | What it is | Installed at | Role |
|---|---|---|---|
| **Skill** | A workflow with steps and exit criteria | `.claude/skills/<name>/SKILL.md` | The *how* |
| **Agent** | A persona with one perspective and one report format | `.claude/agents/<name>.md` | The *who* |
| **Command** | A slash command, the user-facing entry point | `.claude/commands/<name>.md` | The *when* |
| **Reference** | A checklist or pattern catalog linked from the others | `.claude/references/<name>.md` | Shared knowledge |

This meta-skill is the router: it maps the task in front of you to the entry that
encodes the right process, and it defines the operating behaviors that apply no matter
which entry is active. It routes; it does not do the work. Once the right entry is
identified, load it and follow it.

## When to Use

- At the start of a session, before touching code
- When a new task arrives and it is not obvious which workflow applies
- When a task changes shape mid-way (a feature turns into a bug hunt, a review turns up a
  security question)
- When a skill, agent or command referenced somewhere is not installed yet

## Installing Catalog Entries

Entries live inside the framework and are copied into a project on demand:

```bash
python dev.py agent:list                     # every entry: kind, name, description
python dev.py agent:list --kind skill        # filter by kind: agent, skill, command, reference
python dev.py agent:install interview-me idea-refine spec-driven-development
python dev.py agent:install code-reviewer security-auditor test-engineer ship
python dev.py agent:install --all            # the whole catalog
python dev.py agent:install --all --force    # overwrite entries that already exist
```

Rules of the installer, as implemented in `engine/cli/agent_catalog`:

- Names are given without a slash or extension: the `/ship` command installs as `ship`.
- References are always installed with any selection, because skills and agents link to
  them. They cannot be requested by name.
- An install that would overwrite an existing agent, skill or command is refused before
  anything is written; pass `--force` to replace it.
- An unknown name refuses the whole install; check the spelling with `agent:list`.
- `python dev.py agent:scaffold` primes the whole `.claude/` layout for a project,
  catalog included.

Before invoking an entry, confirm its file exists under `.claude/`. If it does not,
install it rather than improvising the workflow from memory.

## Skill Discovery

When a task arrives, identify the phase and route it:

```
Task arrives
    |
    |-- Don't know what you want yet? ----------> interview-me
    |-- Rough concept, need variations? --------> idea-refine
    |-- New project, feature or change? --------> spec-driven-development      (/spec)
    |-- No quality bar written down? -----------> constraint-driven-development (/constraints)
    |-- Have a spec, need tasks? ---------------> planning-and-task-breakdown  (/plan-tasks)
    |-- Implementing code? ---------------------> incremental-implementation   (/build)
    |     |-- UI work (Forge, vanilla JS/CSS)? -> frontend-ui-engineering
    |     |-- API or interface work? -----------> api-and-interface-design
    |     |-- Need better context loaded? ------> context-engineering
    |     |-- Must verify framework facts? -----> source-driven-development
    |     `-- High stakes or unfamiliar code? --> doubt-driven-development
    |-- Writing or running tests? --------------> test-driven-development      (/test)
    |     `-- Browser-based verification? ------> browser-testing-with-devtools
    |-- Something broke? -----------------------> debugging-and-error-recovery
    |-- Reviewing code? ------------------------> code-review-and-quality      (/review-change)
    |     |-- Too complex? ---------------------> code-simplification          (/code-simplify)
    |     |-- Security concerns? ---------------> security-and-hardening
    |     `-- Performance concerns? ------------> performance-optimization     (/webperf for pages)
    |-- Committing, branching, versioning? -----> git-workflow-and-versioning
    |-- CI/CD pipeline work? -------------------> ci-cd-and-automation
    |-- Deprecating or migrating? --------------> deprecation-and-migration
    |-- Writing docs or ADRs? ------------------> documentation-and-adrs
    |-- Adding logs, metrics, alerts? ----------> observability-and-instrumentation
    `-- Deploying or launching? ----------------> shipping-and-launch          (/ship)
```

## Intent Map

The same routing as a lookup table, covering every skill, agent and command in the
catalog.

### Skills

| When the user says or the task is... | Skill | File |
|---|---|---|
| "Build me X" with no who, why or success criteria; "interview me", "grill me" | `interview-me` | `.claude/skills/interview-me/SKILL.md` |
| "Refine this idea", "ideate on X", "stress-test my plan" | `idea-refine` | `.claude/skills/idea-refine/SKILL.md` |
| A new feature or change with no written requirements | `spec-driven-development` | `.claude/skills/spec-driven-development/SKILL.md` |
| "What is our quality bar?", no written constraints for the project | `constraint-driven-development` | `.claude/skills/constraint-driven-development/SKILL.md` |
| A spec exists and needs ordered, verifiable tasks | `planning-and-task-breakdown` | `.claude/skills/planning-and-task-breakdown/SKILL.md` |
| Implementing a task slice by slice | `incremental-implementation` | `.claude/skills/incremental-implementation/SKILL.md` |
| Forge templates, forms, vanilla JS/CSS, accessibility | `frontend-ui-engineering` | `.claude/skills/frontend-ui-engineering/SKILL.md` |
| Routes, JSON resources, FormRequests, error contracts, public module interfaces | `api-and-interface-design` | `.claude/skills/api-and-interface-design/SKILL.md` |
| The agent is missing project context, or drowning in it | `context-engineering` | `.claude/skills/context-engineering/SKILL.md` |
| Using a framework API, command or directive that must be verified in `engine/` first | `source-driven-development` | `.claude/skills/source-driven-development/SKILL.md` |
| High-stakes or unfamiliar change; a decision that needs cross-examination | `doubt-driven-development` | `.claude/skills/doubt-driven-development/SKILL.md` |
| Writing tests first, proving a bug with a failing test | `test-driven-development` | `.claude/skills/test-driven-development/SKILL.md` |
| Verifying a page in a real browser (console, network, DOM, performance traces) | `browser-testing-with-devtools` | `.claude/skills/browser-testing-with-devtools/SKILL.md` |
| An error, a failing suite, unexpected behavior | `debugging-and-error-recovery` | `.claude/skills/debugging-and-error-recovery/SKILL.md` |
| Reviewing a diff or pull request before merge | `code-review-and-quality` | `.claude/skills/code-review-and-quality/SKILL.md` |
| Code over the layer caps, too nested, too clever | `code-simplification` | `.claude/skills/code-simplification/SKILL.md` |
| Auth, CSRF, anti-spam, secrets, input validation, personal data | `security-and-hardening` | `.claude/skills/security-and-hardening/SKILL.md` |
| Slow queries, N+1, cache, heavy pages | `performance-optimization` | `.claude/skills/performance-optimization/SKILL.md` |
| Commits, branches, CHANGELOG entries, version and release tags | `git-workflow-and-versioning` | `.claude/skills/git-workflow-and-versioning/SKILL.md` |
| Pipelines running pytest, ruff and the language and structure gates | `ci-cd-and-automation` | `.claude/skills/ci-cd-and-automation/SKILL.md` |
| Retiring an API, renaming a column with expand/contract, moving users off old code | `deprecation-and-migration` | `.claude/skills/deprecation-and-migration/SKILL.md` |
| README, guides, ADRs, docstrings | `documentation-and-adrs` | `.claude/skills/documentation-and-adrs/SKILL.md` |
| Structured logs, metrics, traces, alerts | `observability-and-instrumentation` | `.claude/skills/observability-and-instrumentation/SKILL.md` |
| Going to production, launch checklist, rollback plan | `shipping-and-launch` | `.claude/skills/shipping-and-launch/SKILL.md` |
| Which workflow applies? How do I install one? | `using-agent-catalog` | `.claude/skills/using-agent-catalog/SKILL.md` |

### Agents

Agents are personas: one perspective, one report. Invoke them directly for a single
perspective on a single artifact. **Agents never invoke other agents**; composition is
the job of the user or a command.

| When you need... | Agent | File |
|---|---|---|
| A multi-axis review of a change (correctness, readability, architecture, security, performance, governance) | `code-reviewer` | `.claude/agents/code-reviewer.md` |
| Vulnerability detection, threat modeling, OWASP-style audit, privacy exposure | `security-auditor` | `.claude/agents/security-auditor.md` |
| Test strategy, missing coverage, tests for existing code, the Prove-It pattern for bugs | `test-engineer` | `.claude/agents/test-engineer.md` |
| A Core Web Vitals audit of pages: loading, rendering, network | `web-performance-auditor` | `.claude/agents/web-performance-auditor.md` |

### Commands

| Command | Use it to | Wraps |
|---|---|---|
| `/spec` | Write a structured specification before any code | `spec-driven-development` |
| `/constraints` | Define and enforce the project's quality bar | `constraint-driven-development` |
| `/plan-tasks` | Break a spec into small, verifiable, ordered tasks | `planning-and-task-breakdown` |
| `/build` | Implement tasks incrementally: build, test, verify, commit | `incremental-implementation` + `test-driven-development` |
| `/test` | Run the test-first workflow; for bugs, prove them with a failing test | `test-driven-development` (with `test-engineer`) |
| `/review-change` | Run a multi-axis review of the current change | `code-review-and-quality` (with `code-reviewer`) |
| `/code-simplify` | Reduce complexity without changing behavior | `code-simplification` |
| `/webperf` | Audit browser-facing pages for performance; not for CLI or server-only code | `web-performance-auditor` |
| `/ship` | Pre-launch gate: fan out to `code-reviewer`, `security-auditor` and `test-engineer` in parallel, then merge into a go/no-go decision with a rollback plan | `shipping-and-launch` |

### References

Checklists linked from skills and agents, always installed with any selection:

| Reference | Consult when |
|---|---|
| `.claude/references/definition-of-done.md` | Deciding whether any change is finished |
| `.claude/references/testing-patterns.md` | Structuring pytest tests, fixtures and factories |
| `.claude/references/security-checklist.md` | Reviewing or hardening anything that handles input, auth or secrets |
| `.claude/references/performance-checklist.md` | Measuring and fixing query, cache or page performance |
| `.claude/references/accessibility-checklist.md` | Building or reviewing Forge templates and forms |
| `.claude/references/observability-checklist.md` | Adding logs, metrics and alerts |
| `.claude/references/orchestration-patterns.md` | Composing agents, or adding a command that coordinates several |

## Core Operating Behaviors

These apply at all times, across every skill. They are non-negotiable.

### 1. Surface Assumptions

Before implementing anything non-trivial, state your assumptions explicitly:

```
ASSUMPTIONS I'M MAKING:
1. <assumption about requirements>
2. <assumption about architecture: module, service, plugin boundary, data shape>
3. <assumption about scope>
-> Correct me now or I'll proceed with these.
```

Do not silently fill in ambiguous requirements. The most common failure is a wrong
assumption carried forward unchecked. Surfacing uncertainty early is cheaper than rework.
On Craft projects the governance adds a hard point here: for anything beyond a local
fix, confirm the architecture (modules, services, plugin boundaries, data shape) before
writing domain code.

### 2. Manage Confusion Actively

When you meet inconsistencies, conflicting requirements or an unclear spec:

1. **Stop.** Do not continue on a guess.
2. Name the specific confusion.
3. Present the trade-off or ask the clarifying question.
4. Wait for the resolution before continuing.

**Bad:** silently picking one interpretation and hoping.
**Good:** "The spec says X, but `app/Http/Controllers/OrderController.py` does Y. Which
one wins?"

### 3. Push Back When Warranted

You are not a yes-machine. When an approach has clear problems:

- Point out the issue directly
- Explain the concrete downside, quantified where possible ("this adds one query per
  row, about 200 queries on the index page", not "this might be slower")
- Propose an alternative
- Accept the human's decision if they override it with full information

Sycophancy is a failure mode. "Of course!" followed by implementing a bad idea helps no
one. Honest technical disagreement is worth more than false agreement. The one thing
that is never negotiated away is the gate: requests to hardcode user-facing copy, run a
destructive migration command or weaken a lint rule get the compliant version plus a
one-line explanation.

### 4. Enforce Simplicity

The natural tendency is to overcomplicate. Resist it actively.

Before finishing any implementation, ask:

- Can this be done in fewer lines?
- Are these abstractions earning their complexity?
- Would a staff engineer look at this and ask "why didn't you just..."?
- Does the framework already ship it (CRUD builder, FormRequest validation, a facade, a
  plugin)? Re-implementing it by hand is not neutral.

If you wrote 1,000 lines where 100 would do, you have failed. Prefer the boring,
obvious solution. The structural caps are a backstop, not a target: 25 lines per
function, complexity 6, 15 lines per controller action.

### 5. Maintain Scope Discipline

Touch only what you were asked to touch.

Do NOT:

- Remove comments you do not understand
- "Clean up" code orthogonal to the task
- Refactor adjacent systems as a side effect
- Delete code that looks unused without explicit approval
- Add features that are not in the spec because they "seem useful"

The job is surgical precision, not unsolicited renovation. Scope discipline limits
*breadth*, never *completeness*: everything that is in scope gets done in full.

### 6. Verify, Don't Assume

Every skill ends with a verification step, and a task is not complete until it passes.
"Seems right" is never enough; there must be evidence. On a Craft project the evidence
is:

```bash
python -m pytest tests
ruff check engine
python .claude/rules/lint_language.py
python .claude/rules/lint_structure.py
```

Per-skill verification is the local check. The project-wide bar for *every* change,
whichever skill is active, is the Definition of Done in
`.claude/references/definition-of-done.md`: tests pass, gates are clean, no regressions,
behavior verified at runtime, a `CHANGELOG.md` entry under `## [Unreleased]`, docs
updated. It complements each task's acceptance criteria rather than replacing them.

## Failure Modes to Avoid

Subtle errors that look like productivity but create problems:

1. Making wrong assumptions without checking
2. Not managing your own confusion, plowing ahead when lost
3. Not surfacing inconsistencies you notice
4. Not presenting trade-offs on non-obvious decisions
5. Being sycophantic toward approaches with clear problems
6. Overcomplicating code and APIs
7. Modifying code or comments orthogonal to the task
8. Removing things you do not fully understand
9. Building without a spec because "it's obvious"
10. Skipping verification because "it looks right"
11. Using a framework API from memory instead of verifying it in `engine/`
12. Improvising a workflow whose catalog entry simply was not installed

## Catalog Rules

1. **Check for an applicable entry before starting work.** Skills encode processes that
   prevent common mistakes.
2. **Skills are workflows, not suggestions.** Follow the steps in order. Do not skip
   verification.
3. **Several skills can apply in sequence.** A feature may run `idea-refine` ->
   `spec-driven-development` -> `planning-and-task-breakdown` ->
   `incremental-implementation` -> `test-driven-development` ->
   `code-review-and-quality` -> `code-simplification` -> `shipping-and-launch`.
4. **When in doubt, start with a spec.** For a non-trivial task with no spec, begin with
   `spec-driven-development` (`/spec`).
5. **The user orchestrates.** Commands compose agents and skills; agents never call
   other agents, and there is no router agent. This skill routes by telling you which
   entry to load, not by delegating to one. See
   `.claude/references/orchestration-patterns.md`.

## Lifecycle Sequence

For a complete feature, the typical sequence is:

```
1.  interview-me                      -> Extract what the user actually wants
2.  idea-refine                       -> Refine vague ideas into a direction
3.  spec-driven-development           -> Define what we are building          (/spec)
4.  constraint-driven-development     -> Write down the quality bar            (/constraints)
5.  planning-and-task-breakdown       -> Break into verifiable chunks          (/plan-tasks)
6.  context-engineering               -> Load the right context
7.  source-driven-development          -> Verify framework facts in engine/
8.  incremental-implementation        -> Build slice by slice                  (/build)
9.  observability-and-instrumentation -> Instrument while building (runs alongside 8-11, not after)
10. doubt-driven-development          -> Cross-examine non-trivial decisions in flight
11. test-driven-development           -> Prove each slice works                (/test)
12. code-review-and-quality           -> Review before merge                   (/review-change)
13. code-simplification               -> Reduce complexity, keep behavior      (/code-simplify)
14. git-workflow-and-versioning       -> Clean commits, CHANGELOG entry
15. documentation-and-adrs            -> Document the decisions
16. deprecation-and-migration         -> Retire old systems safely when needed
17. shipping-and-launch               -> Deploy safely                         (/ship)
```

Not every task needs every step. A bug fix may only need
`debugging-and-error-recovery` -> `test-driven-development` ->
`code-review-and-quality`. A page that feels slow may only need `/webperf` ->
`performance-optimization` -> `test-driven-development`.

## Quick Reference

| Phase | Skill | One-line summary |
|---|---|---|
| Define | interview-me | Surface what the user actually wants before any plan, spec or code |
| Define | idea-refine | Refine ideas through divergent and convergent thinking |
| Define | spec-driven-development | Requirements and acceptance criteria before code |
| Define | constraint-driven-development | A written, enforced quality bar for the project |
| Plan | planning-and-task-breakdown | Decompose into small, verifiable tasks |
| Build | incremental-implementation | Thin vertical slices, each tested before expanding |
| Build | source-driven-development | Verify framework facts in the source before using them |
| Build | doubt-driven-development | Adversarial fresh-context review of non-trivial decisions |
| Build | context-engineering | The right context at the right time |
| Build | frontend-ui-engineering | Accessible Forge templates with vanilla JS and CSS |
| Build | api-and-interface-design | Stable interfaces with explicit contracts |
| Verify | test-driven-development | Failing pytest test first, then make it pass |
| Verify | browser-testing-with-devtools | Chrome DevTools for runtime verification in the browser |
| Verify | debugging-and-error-recovery | Reproduce, localize, fix, guard |
| Review | code-review-and-quality | Multi-axis review with quality gates |
| Review | code-simplification | Keep behavior, reduce unnecessary complexity |
| Review | security-and-hardening | OWASP prevention, CSRF and anti-spam, least privilege, privacy |
| Review | performance-optimization | Measure first, optimize only what matters |
| Ship | git-workflow-and-versioning | Atomic Conventional Commits, CHANGELOG, synced versions |
| Ship | ci-cd-and-automation | Automated gates on every change |
| Ship | deprecation-and-migration | Remove old systems and migrate data forward safely |
| Ship | documentation-and-adrs | Document the why, not only the what |
| Ship | observability-and-instrumentation | Structured logs, RED metrics, traces, symptom-based alerts |
| Ship | shipping-and-launch | Pre-launch checklist, monitoring, rollback plan |
| Meta | using-agent-catalog | Route work to the right entry and install it |

## Red Flags

- Starting non-trivial work without checking which entry applies
- Reproducing a workflow from memory because its entry is not installed
- An agent asked to call another agent, or a "router" persona proposed
- Skipping a skill's verification step because the change "looks right"
- Declaring done with a gate that was not run, or that exits non-zero

## Verification

After routing a task:

- [ ] The task's phase was identified and mapped to a skill, agent or command above
- [ ] Every entry about to be used exists under `.claude/`, or was installed with
      `python dev.py agent:install <name>`
- [ ] Assumptions were surfaced before non-trivial work started
- [ ] The chosen entry's own verification steps, plus the Definition of Done, are the
      exit criteria for the task
