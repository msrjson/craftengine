---
name: documentation-and-adrs
description: Records architecture decisions and the reasoning behind them in ADRs, docstrings, README and CHANGELOG. Use when making a decision that is expensive to reverse, changing a public API or facade, shipping user-visible behavior, or capturing context future engineers and agents will need.
---

# Documentation and ADRs

## Overview

Document decisions, not only code. The most valuable documentation records the *why*: the
context, the constraints and the trade-offs that produced a design. Code shows *what* was
built; documentation explains *why it was built this way* and *which alternatives were
rejected*. Future contributors and agents working in a Craft Engine project depend on that
context to avoid re-deciding settled questions or undoing deliberate choices.

On Craft projects every committed document is English (README, ADRs, `CHANGELOG.md`,
`docs/`, `audit/`, `documentation/`, `.claude/`), whatever language the team speaks.

## When to Use

- Making a significant architectural decision (module boundaries, plugin vs. module, schema shape)
- Choosing between competing approaches
- Adding or changing a public API, a facade, a container binding or a CLI command
- Shipping a feature that changes user-facing behavior
- Onboarding new contributors or agents to the project
- Noticing that you explain the same thing repeatedly

**When NOT to use:** do not document obvious code, do not write comments that restate the
code, and do not write docs for a throwaway spike that will be deleted.

## Architecture Decision Records (ADRs)

ADRs capture the reasoning behind significant technical decisions. They are the highest-value
documentation you can write.

### When to Write an ADR

- Adding a major dependency, or deciding to build a capability as a plugin under `app/plugins/`
- Designing a data model or database schema (tables, tenancy scoping, soft deletes, partitioning)
- Selecting an authentication or authorization strategy (session, API token, Gate/Policy layout)
- Deciding on an API architecture (resource shape, versioning prefix, error envelope, pagination)
- Choosing hosting, queue backend, cache backend or deployment topology
- Any decision that would be expensive to reverse: a migration is forward-only, so a schema
  decision is always expensive to reverse

### Match the existing convention first

Before creating an ADR, inspect the repository for an established convention: existing ADRs,
the project's rules in `.claude/rules/`, `CLAUDE.md` / `AGENTS.md`, and any ADR tooling or
configuration file. An established convention overrides the defaults below. Match:

- **Location and format** — for example `docs/adr/*.md`, `documentation/decisions/*.md`, or a
  reStructuredText layout. Keep the directory, file extension and markup already in use.
- **Numbering and naming** — continue the existing sequence and filename pattern
  (`ADR-004-title.md`, `0004-title.md`, and so on). Never restart at 001 or add a second scheme.
- **Section headings** — reuse the project's heading set instead of imposing this template.

If the evidence conflicts (two directories, two numbering schemes), surface the conflict rather
than silently introducing a third. Only when no convention exists, apply the default below.

### ADR Template

Store ADRs in `docs/decisions/` with sequential numbering, unless the project already uses
another location (see above):

```markdown
# ADR-001: Use PostgreSQL as the primary database

## Status
Accepted | Superseded by ADR-XXX | Deprecated

## Date
2026-01-15

## Context
We need a primary database for the task management application. Requirements:
- Relational data model (users, tasks, teams with foreign keys)
- ACID transactions for task state changes
- Full-text search on task content
- Tenant isolation enforced at the database, not only in application code
- A managed hosting option, because the team has limited operations capacity

## Decision
Use PostgreSQL through the Craft ORM, with SQLite only as the test database.

## Alternatives Considered

### A document store
- Pros: flexible schema, fast to start
- Cons: our data is inherently relational; relationships would be managed by hand
- Rejected: relational data in a document store leads to duplication or complex lookups

### SQLite in production
- Pros: zero configuration, embedded, fast reads
- Cons: limited concurrent writes, no row-level security, no managed hosting
- Rejected: unsuitable for a multi-tenant web application in production

### MySQL
- Pros: mature, widely supported
- Cons: weaker JSONB, full-text search and row-level security support for our needs
- Rejected: PostgreSQL fits the tenancy and search requirements better

## Consequences
- Schema evolves through forward-only migrations (`python dev.py migrate`)
- `tsvector` columns replace a separate search service
- Row-level security policies back tenant isolation (`tenant_scoped` tables)
- Tests run on SQLite, so PostgreSQL-only features need integration tests on PostgreSQL
- The team needs PostgreSQL knowledge (a standard skill, low risk)
```

### ADR Lifecycle

```
PROPOSED -> ACCEPTED -> (SUPERSEDED or DEPRECATED)
```

- **Never delete old ADRs.** They are the historical record of why the system looks the way it does.
- When a decision changes, write a new ADR that references and supersedes the old one, and
  update the old one's `Status` line to point at its replacement.

## Inline Documentation

### When to Comment

Comment the *why*, not the *what*. Comments are English, always:

```python
# BAD: restates the code
# Increment the counter by one.
counter += 1

# GOOD: explains non-obvious intent
# The rate limit uses a sliding window: reset at the window boundary rather
# than on a fixed schedule, so a burst cannot straddle two fixed windows.
if now - window_start > WINDOW_SIZE_SECONDS:
    counter = 0
    window_start = now
```

### When NOT to Comment

```python
# Do not comment self-explanatory code.
def calculate_total_cents(items: list[CartItem]) -> int:
    """Return the cart total in minor units."""
    return sum(item.price_cents * item.quantity for item in items)

# Do not leave TODO comments for work you should do now.
# TODO: add error handling   <- add it

# Do not leave commented-out code; git keeps the history.
# def old_implementation(): ...   <- delete it
```

Commented-out code and parked hacks are build failures under the project's governance, not
notes for later.

### Document Known Gotchas

```python
def bind_tenant(connection: Connection, tenant_id: int) -> None:
    """Bind the tenant for row-level security on this pooled connection.

    IMPORTANT: call this after the connection is checked out of the pool and
    before the first query. A connection returned to the pool keeps its
    session variable, so skipping the reset in `release()` leaks one tenant's
    rows to the next request that borrows the connection.

    See ADR-003 for the tenancy design rationale.

    Args:
        connection: The connection checked out for the current request.
        tenant_id: The authenticated tenant's primary key.
    """
```

## API Documentation

For public interfaces (HTTP endpoints, facades, service methods consumed by other modules):

### Docstrings with Type Hints (Preferred for Python)

Every public class and function carries type hints on every parameter and return and a
Google-style docstring:

```python
def create_task(self, data: CreateTaskInput, owner: User) -> Task:
    """Create a task owned by `owner`.

    Args:
        data: Validated creation data; `title` is required, `description` optional.
        owner: The authenticated user who will own the task.

    Returns:
        The persisted task with its server-generated id and timestamps.

    Raises:
        TaskTitleTakenError: If the owner already has an open task with this title
            (`code` TASK_TITLE_TAKEN, `message_key` task.create.title_taken).
        AuthorizationException: If the owner may not create tasks.

    Example:
        >>> task = task_service.create_task(CreateTaskInput(title="Weekly report"), user)
        >>> task.id
        42
    """
```

Document errors by their `code` and `message_key`, never by a rendered sentence: the sentence
lives in the translation store and differs per locale.

### OpenAPI for HTTP APIs

```yaml
paths:
  /api/v1/tasks:
    post:
      summary: Create a task
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreateTaskInput'
      responses:
        '201':
          description: Task created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Task'
        '422':
          description: Validation failed
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorEnvelope'
components:
  schemas:
    ErrorEnvelope:
      type: object
      required: [error]
      properties:
        error:
          type: object
          required: [code, message_key]
          properties:
            code: { type: string, example: VALIDATION_FAILED }
            message_key: { type: string, example: validation.request.failed }
            params: { type: object }
```

Keep the spec next to the code that implements it and update both in the same change. See the
`api-and-interface-design` skill (`.claude/skills/api-and-interface-design/SKILL.md`) for the
contract itself.

## README Structure

Every project has a README that covers:

```markdown
# Project Name

One paragraph describing what this project does and who it is for.

## Quick Start
1. Clone the repository
2. Create a virtual environment: `python -m venv .venv`
3. Install dependencies: `pip install -e .`
4. Configure the environment: copy `.env.example` to `.env`, then `python dev.py key:generate`
5. Apply migrations: `python dev.py migrate`
6. Start the server: `python dev.py serve`

## Commands
| Command | Description |
|---------|-------------|
| `python dev.py serve` | Start the development server |
| `python dev.py migrate` | Apply forward-only migrations |
| `python dev.py route:list` | List registered routes |
| `python -m pytest tests` | Run the test suite |
| `ruff check .` | Run the linter |
| `python .claude/rules/lint_language.py` | Language and i18n gate |
| `python .claude/rules/lint_structure.py` | Layer caps and structure gate |

## Architecture
Short overview of modules, plugins and key design decisions.
Link to ADRs for details.

## Safety
Destructive database commands (`migrate:fresh`, `migrate:reset`, `migrate:refresh`,
`db:wipe`, `db:drop`) are banned in every environment.

## Contributing
Coding standards, Conventional Commits, the gates that must pass, review process.
```

## Changelog Maintenance

Every change adds its entry under `## [Unreleased]` in `CHANGELOG.md` in the same commit, using
Keep a Changelog categories (`Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`).
Cutting a release renames that section to the versioned header and opens a fresh, empty
`## [Unreleased]` above it:

```markdown
# Changelog

## [Unreleased]

## [1.2.0] r00012 — 2026-01-20
### Added
- Task sharing: users can share tasks with team members (#123)
- E-mail notifications for task assignments, copy keyed under `email.task_assigned.*` (#124)

### Fixed
- Duplicate tasks created when the submit button is pressed repeatedly (#125)

### Changed
- Task list loads 50 items per page instead of 20 (#126)

### Security
- Comment form now carries `@honeypot` and `@antispam` (#127)
```

The version in the header matches `pyproject.toml` and `engine/__init__.py`, and the `rNNNNN`
release counter increments by exactly one per release; the tag is `vX.Y.Z-rNNNNN`.

## Documentation for Agents

Agents read documentation more consistently than humans do. Keep it accurate:

- **`CLAUDE.md` / `AGENTS.md` and `.claude/rules/`** — project conventions, gates and hard
  boundaries, so agents follow them without being told each session
- **`llms.txt` / `llms-full.txt`** — generated by `python dev.py agent:scaffold`; regenerate or
  update them when the framework surface they describe changes
- **Spec files** — keep specs current so agents build the right thing
- **ADRs** — tell agents why past decisions were made, which prevents re-deciding them
- **Inline gotchas** — keep agents out of known traps at the exact line where the trap lives

See the `context-engineering` skill (`.claude/skills/context-engineering/SKILL.md`) for how these
files are loaded.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "The code is self-documenting" | Code shows what. It does not show why, which alternatives were rejected, or which constraints apply. |
| "We'll write docs when the API stabilizes" | APIs stabilize faster when documented. The doc is the first test of the design. |
| "Nobody reads docs" | Agents do. Future engineers do. You, three months from now, do. |
| "ADRs are overhead" | A ten-minute ADR prevents a two-hour debate about the same decision six months later. |
| "Comments get outdated" | Comments on *why* are stable. Comments on *what* go stale, which is why you write only the former. |
| "The changelog can be written at release time" | By release time nobody remembers the details. The entry belongs in the same commit. |
| "The team reads Portuguese, so docs can be in Portuguese" | Committed documents are English. Conversation language and artifact language are separate axes. |

## Red Flags

- Architectural decisions with no written rationale
- Public functions, facades or endpoints without type hints or docstrings
- A README that does not explain how to install, migrate and run the project
- Commented-out code instead of deletion
- TODO comments that have survived for weeks
- No ADRs in a project with significant architectural choices
- Documentation that restates the code instead of explaining intent
- A code change with no `CHANGELOG.md` entry under `## [Unreleased]`
- Errors documented as rendered sentences instead of `code` + `message_key`
- Committed documents written in a language other than English

## Verification

After documenting:

- [ ] ADRs exist for every significant architectural decision, in the project's established location and numbering
- [ ] README covers quick start, commands, architecture overview and the banned destructive commands
- [ ] Public functions have type hints and Google-style docstrings (`Args`, `Returns`, `Raises`)
- [ ] Known gotchas are documented inline where they matter
- [ ] No commented-out code remains
- [ ] `CHANGELOG.md` has an entry under `## [Unreleased]` in the correct category
- [ ] Rules files (`CLAUDE.md`, `AGENTS.md`, `.claude/rules/`) and `llms.txt` are current and accurate
- [ ] Every committed document is English; `python .claude/rules/lint_language.py` exits 0
