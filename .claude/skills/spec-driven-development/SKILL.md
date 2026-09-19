---
name: spec-driven-development
description: Writes a structured specification before any code is written. Use when starting a new project, module, feature or significant change with no spec yet, when requirements are vague or ambiguous, or when one request bundles several independently testable capabilities that need a capability map first.
---

# Spec-Driven Development

## Overview

Write the specification before the code. The spec is the single source of truth
shared by you and the human engineer: what is being built, why, for whom, and how
everyone will know it is finished. Code written without one is a guess that
happens to compile.

On a Craft Engine project the spec also fixes the **architecture before the
business logic**: modules, services, plugin boundaries and data shape are agreed
in writing before a single line of domain code exists. A confirmed shape is cheap;
a rewritten module is not.

## When to Use

- Starting a new project, business module or feature
- Requirements are ambiguous, incomplete or only exist as an idea
- The change touches several files, layers or modules
- You are about to make an architectural decision (new module, new plugin, new table)
- The work would take more than about 30 minutes to implement

**When NOT to use:** single-line fixes, typo corrections, or changes whose
requirements are unambiguous and fully self-contained.

## Where the Artifacts Live

Specs, capability maps, plans and task lists are planning artifacts, not
production code. In a Craft project they live **outside the production tree**, at
the repository root, never inside `data/`:

```
.agents/plans/
├── CAPABILITY-MAP.md      → Only when Phase 0 applies
├── SPEC.md                → Single-capability spec
├── SPEC-<module-id>.md    → One spec per module when a map exists
├── plan.md                → Implementation plan (planning-and-task-breakdown)
└── todo.md                → Task list (planning-and-task-breakdown)
```

They are committed like every other artifact, so they are written in English.

## The Gated Workflow

Four phases, preceded by a scope check (Phase 0) that activates only when a
request bundles several independently testable capabilities. Never advance until
the current phase has been validated by the human.

```
SPECIFY ──→ PLAN ──→ TASKS ──→ IMPLEMENT
   │          │        │          │
   ▼          ▼        ▼          ▼
 Human      Human    Human      Human
 reviews    reviews  reviews    reviews
```

### Phase 0: Scope Check

Most requests describe a single capability. When that is the case, skip this
phase and go straight to Specify. Phase 0 is for the exception, and it imposes no
hierarchy on single-capability work.

**Detection.** Decompose before specifying when one requirement bundles several
independently testable capabilities:

- It names distinct capabilities with their own consumers or data (identity,
  billing, notifications, reporting)
- Acceptance criteria cluster into groups that could ship and be verified separately
- One capability could be removed or replaced without rewriting the requirements
  of the others

**Propose a capability map before any spec.** Keep it small and reviewable: a
module table and a build order, not a project plan.

```markdown
# Capability Map: [Initiative Name]

| Module id | Responsibility | Depends on |
|---|---|---|
| identity | Accounts, sessions, roles | — |
| billing | Plans, tax invoices, bank slips, instant payments | identity |
| notifications | E-mail and webhook fan-out (queued jobs) | identity |
| reporting | Usage dashboards | billing, notifications |

Build order: identity → billing, notifications → reporting
```

- **Stable module ids.** Kebab-case, chosen once, never renamed mid-initiative.
  Specs, plans and downstream commands select work by id instead of guessing which
  spec is active. On Craft, a module id usually maps to one self-contained business
  module under `app/modules/` with its own routes, services and models.
- **One dependency direction, no cycles.** If two modules each need the other,
  they are one module.
- **Interfaces live at the boundary.** The map records that `billing` depends on
  `identity`; the contract between them belongs in the provider module's spec
  (see the `api-and-interface-design` skill,
  `.claude/skills/api-and-interface-design/SKILL.md`).
- **Cross-cutting capabilities are plugins, not modules.** Document validation,
  check digits, QR rendering or a payment gateway go under `app/plugins/` and are
  resolved from the container. Mark them as such in the map.

**The map is gated like every phase.** The human reviews module boundaries,
dependency direction and build order before any module spec is written. A wrong
map is expensive; reviewing ten lines is not.

**Then recurse per module.** Run Specify → Plan → Tasks → Implement for each
module in dependency order. Save the approved map as
`.agents/plans/CAPABILITY-MAP.md` and each module spec next to it, named by module
id (`SPEC-identity.md`, `SPEC-billing.md`). The map, not filename guessing, is the
index of what exists.

### Phase 1: Specify

Start from the high-level vision. Ask clarifying questions until the requirements
are concrete.

**Surface assumptions immediately.** Before writing any spec content, list them:

```
ASSUMPTIONS I'M MAKING:
1. This is a server-rendered web feature (Forge views), plus a JSON API for the same data
2. Authentication uses the existing session guard, not API tokens
3. The database is PostgreSQL in production and SQLite in the test suite
4. Customers are in Brazil, so CPF/CNPJ are collected and LGPD applies
→ Correct me now or I'll proceed with these.
```

Never fill ambiguous requirements silently. The whole point of the spec is to
surface misunderstandings before code exists, and an unstated assumption is the
most dangerous misunderstanding there is.

**Write a spec covering these six core areas:**

1. **Objective** — What are we building and why? Who is the user? What does
   success look like?

2. **Commands** — Full executable commands with flags, not tool names.
   ```
   Dev server:  python dev.py serve
   Migrate:     python dev.py migrate
   Status:      python dev.py migrate:status
   Tests:       python -m pytest tests
   Lint:        ruff check engine
   Language:    python .claude/rules/lint_language.py
   Structure:   python .claude/rules/lint_structure.py
   ```

3. **Project Structure** — Where source, tests and docs belong.
   ```
   app/Models              → Craft ORM models (Active Record)
   app/Http/Controllers    → Thin HTTP layer (150 lines/file, 15 lines/action)
   app/Http/Requests       → FormRequest validation
   app/Http/Resources      → JSON resource shaping
   app/Services            → Domain services (300 lines/file)
   app/plugins/            → Cross-cutting capabilities, resolved from the container
   database/migrations     → Forward-only schema changes
   resources/views         → Forge templates
   routes/web.py, api.py   → Route declarations
   tests/                  → pytest suite (SQLite in memory by default)
   ```

4. **Code Style** — One real snippet beats three paragraphs. Include naming,
   typing, docstrings, and how errors and user-facing text are expressed.
   (`DomainError` below stands for the project's own typed error base, the one
   described in `.claude/rules/LANGUAGE_AND_I18N_STANDARD.md`.)

   ```python
   class InvoiceAlreadyPaidError(DomainError):
       """Raised when a payment is captured for an invoice that is already settled."""

       code = "INVOICE_ALREADY_PAID"
       message_key = "billing.invoice.already_paid"
       http_status = 409


   def calculate_invoice_total(items: list[InvoiceItem]) -> int:
       """Return the invoice total in minor units.

       Args:
           items: The invoice lines, each priced in minor units.

       Returns:
           The sum of every line total, in cents.
       """
       return sum(item.unit_price_cents * item.quantity for item in items)
   ```

   Conventions to state explicitly: English identifiers, type hints on every
   signature, Google-style docstrings, money as integer minor units plus ISO-4217
   currency, UTC timestamps, no hardcoded user-facing text (translation keys with
   `en`, `pt-BR` and `es` rows), errors carrying `code` + `message_key`, no SQL in
   controllers or services, no HTML in Python, no bare or broad `except`.

5. **Testing Strategy** — Framework (pytest), where tests live (`tests/`),
   coverage expectations, and which level covers which concern: unit tests for
   services and plugins, HTTP tests against the ASGI app for controllers, a
   PostgreSQL run for dialect-sensitive queries.

6. **Boundaries** — Three tiers:
   - **Always do:** run the test suite and both gates before committing; add a
     `CHANGELOG.md` entry under `## [Unreleased]`; put `@csrf` on every
     state-changing form; seed every new translation key in all three locales
   - **Ask first:** schema changes, new dependencies, new plugins, changes to CI,
     anything that touches personal data
   - **Never do:** commit secrets; run `migrate:fresh`, `migrate:reset`,
     `migrate:refresh`, `db:wipe` or `db:drop`; physically delete business
     entities; weaken a gate or delete a failing test to get to green

**Spec template:**

```markdown
# Spec: [Project/Feature Name]

## Objective
[What we're building and why. User stories or acceptance criteria.]

## Tech Stack
[Craft Engine version, Python 3.14, PostgreSQL version, plugins and optional extras used]

## Architecture
[Modules, services, plugins, data shape — confirmed before domain code]

## Commands
[Serve, migrate, test, lint, gates — full commands]

## Project Structure
[Directory layout with descriptions]

## Code Style
[Example snippet + key conventions]

## Testing Strategy
[pytest levels, test locations, coverage requirements]

## Personal Data
[Which personal data is processed, legal basis, retention, access control — or "none"]

## Translation Keys
[New keys, each with en / pt-BR / es values]

## Boundaries
- Always: [...]
- Ask first: [...]
- Never: [...]

## Success Criteria
[How we'll know this is done — specific, testable conditions]

## Open Questions
[Anything unresolved that needs human input]
```

**External spec systems:** this workflow is format-agnostic. If the project
already uses another specification format, keep that format and its storage
conventions instead of creating a duplicate `SPEC.md`. This skill owns the
clarification, the content and the approval gates; the existing system owns how
the approved spec is stored.

**Reframe instructions as success criteria.** Translate vague requirements into
concrete conditions:

```
REQUIREMENT: "Make the dashboard faster"

REFRAMED SUCCESS CRITERIA:
- Dashboard LCP < 2.5s on a throttled 4G profile (Lighthouse)
- The dashboard action issues at most 5 queries (no N+1; eager loading in place)
- Server response time for GET /dashboard < 300ms at p95
- No layout shift during load (CLS < 0.1)
→ Are these the right targets?
```

A measurable goal lets you loop, retry and problem-solve toward it instead of
guessing what "faster" means.

### Phase 2: Plan

With the approved spec, produce a technical implementation plan:

1. Identify the major components (migrations, models, services, plugins,
   controllers, views, jobs) and their dependencies
2. Determine the implementation order: what must exist first
3. Note risks and how to mitigate them
4. Identify what can be built in parallel and what must be sequential
5. Define verification checkpoints between phases

> Follow the `planning-and-task-breakdown` skill
> (`.claude/skills/planning-and-task-breakdown/SKILL.md`) for the dependency graph
> and vertical slicing mechanics; it is the canonical source. The steps above are
> a summary, and when they diverge that skill wins.
>
> **Output convention:** save the plan to `.agents/plans/plan.md` and record the
> task list in the task list target defined by that skill (default
> `.agents/plans/todo.md`; a project may designate an external tracker). Create
> `.agents/plans/` if it does not exist. `/plan-tasks` and `/build` expect these
> defaults.

The plan must be reviewable: the human reads it and answers "yes, that is the
right approach" or "no, change X".

### Phase 3: Tasks

Break the plan into discrete, implementable tasks:

- Each task fits in a single focused session
- Each task has explicit acceptance criteria
- Each task has a verification step (test, gate, manual check)
- Tasks are ordered by dependency, not by perceived importance
- No task changes more than about 5 files

> The `planning-and-task-breakdown` skill is the canonical source for task sizing
> and ordering. The template below is the lightweight inline form; when they
> diverge, that skill wins.

**Task template:**

```markdown
- [ ] Task: [Description]
  - Acceptance: [What must be true when done]
  - Verify: [e.g. python -m pytest tests/test_invoices.py, python .claude/rules/lint_structure.py]
  - Files: [Which files will be touched]
```

### Phase 4: Implement

Execute tasks one at a time following the `incremental-implementation` skill
(`.claude/skills/incremental-implementation/SKILL.md`) and the
`test-driven-development` skill (`.claude/skills/test-driven-development/SKILL.md`).
Use the `context-engineering` skill (`.claude/skills/context-engineering/SKILL.md`)
to load only the spec sections and source files each step needs, instead of
flooding the session with the whole spec.

## Keeping the Spec Alive

The spec is a living document, not a one-off artifact:

- **Update when decisions change.** If the data model must change, update the
  spec first, then implement.
- **Update when scope changes.** Features added or cut are reflected in the spec.
- **Commit the spec.** It lives in version control next to the code, under
  `.agents/plans/`.
- **Reference the spec in pull requests.** Link the section each change implements.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "This is simple, I don't need a spec" | Simple tasks don't need *long* specs, but they still need acceptance criteria. A two-line spec is fine. |
| "I'll write the spec after I code it" | That is documentation, not specification. The value is in forcing clarity *before* the code. |
| "The spec will slow us down" | A 15-minute spec prevents hours of rework. |
| "Requirements will change anyway" | That is why the spec is living. An outdated spec still beats no spec. |
| "The user knows what they want" | Even clear requests carry implicit assumptions. The spec surfaces them. |
| "The architecture will emerge while I code" | On Craft, layer caps, plugin boundaries and schema are expensive to move later. Confirm the shape first. |
| "It's one big feature; splitting it is overhead" | If acceptance criteria cluster into independently testable groups, a monolithic spec forces every task to reason over the whole contract. A ten-line capability map is the cheap alternative. |
| "I'll decompose during planning" | Planning slices tasks within a spec. By then the oversized artifact exists; module boundaries and dependency direction must be decided before it is written. |

## Red Flags

- Writing code without any written requirements
- Asking "should I just start building?" before "done" is defined
- Implementing features not present in any spec or task list
- Architectural decisions (new module, new table, new plugin) made without being documented
- Skipping the spec because "it's obvious what to build"
- A spec that says nothing about personal data on a feature that collects it
- New user-facing copy in the spec with no translation keys listed
- A spec or plan saved inside `data/`
- One spec whose requirements span several independently testable capabilities
- Module boundaries or build order decided implicitly during implementation because
  no capability map was approved up front

## Verification

Before moving to implementation, confirm:

- [ ] The spec covers all six core areas
- [ ] The architecture (modules, services, plugins, data shape) is written down and approved
- [ ] The human has reviewed and approved the spec
- [ ] Success criteria are specific and testable
- [ ] Boundaries (Always / Ask first / Never) are defined
- [ ] Personal data handling is stated, or explicitly "none"
- [ ] The spec is saved under `.agents/plans/` at the repository root
- [ ] If the request bundles several independently testable capabilities, a
      capability map (module ids, dependency direction, build order) was approved
      before any module spec was written
- [ ] Every module spec traces to a module id in the approved map
