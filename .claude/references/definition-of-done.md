# Definition of Done

A standing, project-wide bar that every change must clear before it counts as done.
Acceptance criteria vary per task and answer "did we build the right thing?". The
Definition of Done is the same every time and answers "is this finished to our
standard?". Use it as the final gate in the `planning-and-task-breakdown`,
`incremental-implementation` and `shipping-and-launch` skills
(`.claude/skills/<skill>/SKILL.md`).

For Craft Engine projects this bar sits on top of the governance in `.claude/rules/`:
`AGENTS.md`, `CRAFT_ENGINEERING_GOVERNANCE.md`, `LANGUAGE_AND_I18N_STANDARD.md` and
`RELEASE_NON_REGRESSION_STANDARD.md`. Where one of those is more specific, it wins.

## Definition of Done vs. Acceptance Criteria

| | Acceptance Criteria | Definition of Done |
|---|---|---|
| Scope | Specific to one task or spec | Applies to every increment |
| Changes | Different for each item | Fixed and reused |
| Answers | "Did we build *this thing*?" | "Is it *ready*?" |
| Owner | Defined when planning the task | Defined once for the project |
| Example | "A user can reset the password through an e-mailed link" | "Tests and gates pass, no regressions, changelog updated" |

The two are complementary. A task is done only when **its** acceptance criteria are met
**and** the standing Definition of Done is satisfied. Skipping either leaves work that
looks finished but is not.

## The Standing Checklist

Apply this to every change before declaring it done.

### Correctness

- [ ] All acceptance criteria for the task are met
- [ ] Code runs and behaves as intended, verified at runtime (the app boots with
      `python dev.py about`; the route or command was exercised), not just imported
- [ ] New behavior is covered by pytest tests that fail without the change and pass with it
- [ ] Bug fixes include a reproduction test that failed before the fix
- [ ] `python -m pytest tests` passes; no regressions, no skipped or weakened tests
- [ ] Dialect-sensitive changes also pass against PostgreSQL (`CRAFT_TEST_DB=pgsql`,
      disposable database)
- [ ] Edge cases and error paths are handled, not just the happy path
- [ ] Errors carry a `code` and a `message_key`; no rendered sentence leaves the domain layer

The depth behind these items lives in the `test-driven-development` skill
(`.claude/skills/test-driven-development/SKILL.md`) and
`.claude/references/testing-patterns.md`.

### Quality

- [ ] Code reveals intent through naming and structure; comments explain *why*, not *what*
- [ ] Layer caps hold: controller 150 lines per file and 15 per action, service 300,
      repository 250, any function 25 lines with cyclomatic complexity at most 6
- [ ] Layer purity: no SQL in controllers or services, no HTML in Python; views are Forge
      templates
- [ ] The ecosystem is used, not re-implemented: CRUD through the CRUD builder, services
      resolved from the container, cross-cutting logic in `app/plugins/`
- [ ] Type hints on every signature and Google-style docstrings on every public class and
      function
- [ ] No bare `except:` or `except Exception:`; errors are logged with entity and user or
      tenant id
- [ ] No duplicated business logic
- [ ] No dead code, debug output or commented-out blocks left behind
- [ ] Changes are scoped to the task; no unrelated refactors slipped in
- [ ] Gates pass: `ruff check engine`, `python .claude/rules/lint_structure.py`
- [ ] Frontend changes are vanilla or vendored static `.js` and `.css` — no TypeScript, no
      Node build pipeline

The depth behind these items lives in the `code-review-and-quality` skill (the five-axis
review) and the `code-simplification` skill (reducing complexity without changing
behavior).

### Language and Localization

- [ ] Every committed artifact is English: identifiers, comments, docstrings, tests,
      schema, commit messages, documents
- [ ] No user-facing text is hardcoded in Python, templates, migrations, seeders or tests
- [ ] Every new translation key has database rows for `en` (source), `pt-BR` (default) and
      `es`, written by a migration or seeder in the same change
- [ ] `python .claude/rules/lint_language.py` exits 0
- [ ] New domain terms are added to the glossary in the same change

### Integration

- [ ] The change works with the rest of the system, not just in isolation
- [ ] Database changes are forward-only migrations; nothing depends on `migrate:fresh`,
      `migrate:reset`, `migrate:refresh`, `db:wipe` or `db:drop`
- [ ] Business entities are soft-deleted, never physically deleted
- [ ] Configuration changes are reflected in `config/` defaults and `.env.example`
- [ ] Queue jobs serialize their payload to JSON and are safe to retry
- [ ] Backward compatibility is preserved for public facades, container bindings and API
      contracts, or the break is deprecated and documented
- [ ] Multi-tenant code isolates tenant data at the query and service layers

### Security and Privacy

- [ ] Untrusted input is validated through a FormRequest; mass-assignable fields are
      limited to what `validated()` returns
- [ ] Authorization goes through a Gate ability or a Policy
- [ ] State-changing forms carry `@csrf`; public forms carry `@honeypot` or `@antispam`
- [ ] Secrets and tokens are compared in constant time (`hmac.compare_digest`) and never
      logged
- [ ] Personal data is minimized, purpose-bound and absent from logs (LGPD/GDPR)

See the `security-and-hardening` skill and `.claude/references/security-checklist.md`.

### Documentation

- [ ] `CHANGELOG.md` has an entry under `## [Unreleased]` in the right Keep a Changelog
      category (`Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`)
- [ ] Public interfaces, CLI commands and user-facing behavior are documented
- [ ] Architectural decisions worth preserving are recorded (see the
      `documentation-and-adrs` skill)
- [ ] Documentation describes the current state in timeless language, not the change history
- [ ] The commit follows Conventional Commits in English imperative, one concern per commit

### Ship-Readiness

- [ ] Security implications reviewed for any untrusted input, authentication or data handling
- [ ] Observability in place for new critical paths — structured logs, metrics, traces (see
      the `observability-and-instrumentation` skill and
      `.claude/references/observability-checklist.md`)
- [ ] A rollback path exists for anything risky (see the `shipping-and-launch` skill)
- [ ] For a release: version synchronized between `pyproject.toml` and `engine/__init__.py`,
      `__release__` incremented by exactly one, tag `vX.Y.Z-rNNNNN`, `## [Unreleased]`
      promoted and reopened
- [ ] The human has reviewed and approved before merge or deploy

## How to Apply

- **Per task:** confirm Correctness, Quality and Language and Localization before checking
  the task off.
- **Per feature:** confirm Integration, Security and Privacy, and Documentation before
  considering the feature complete.
- **Per release:** the full checklist is the floor; the `shipping-and-launch` skill and
  `RELEASE_NON_REGRESSION_STANDARD.md` add the release gates on top.

Tailor the list to the project once, then reuse it unchanged. A Definition of Done that is
renegotiated every sprint is not a Definition of Done.

## Red Flags

- "It's done, I just haven't run it yet": unverified work is not done.
- "Tests pass" used as a synonym for done while gates, changelog, translations or runtime
  verification are skipped.
- A gate weakened, a rule exempted or a test skipped to reach green.
- A different bar applied depending on deadline pressure.
- Work deferred because it is large, repetitive or tedious — volume is not a reason to do less.
- Acceptance criteria treated as the whole bar, with no standing quality floor.
- A subset of the requested work presented as complete.
- "Done" declared before human review on changes that need it.
