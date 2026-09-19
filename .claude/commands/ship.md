---
description: Run the pre-launch checklist by fanning out to code-reviewer, security-auditor and test-engineer in parallel, then decide GO or NO-GO with a forward-only rollback plan
argument-hint: [optional scope — branch, commit range or release tag]
---

Follow the `shipping-and-launch` skill (`.claude/skills/shipping-and-launch/SKILL.md`).

Scope: $ARGUMENTS — when empty, review the staged changes plus the commits on the current branch
that are not yet on the default branch.

`/ship` is a **fan-out orchestrator**. It runs three specialist agents in parallel against the
change, then merges their reports into one go/no-go decision with a rollback plan. The agents
work independently — no shared state, no ordering — which is what makes running them in
parallel both safe and worthwhile.

## Phase 0 — Establish the facts (main context, before fanning out)

Collect what every agent and the final decision will need, and pass the relevant parts to each
agent in its prompt:

1. The diff under review: `git diff --staged` and `git log --oneline <default-branch>..HEAD`.
2. The files touched, grouped by layer: controllers, requests, services, repositories, models,
   migrations, Forge views, static `.js`/`.css`, routes, config, plugins, tests.
3. Whether the change is a release cut: does it modify `pyproject.toml`, `engine/__init__.py`
   (`__version__`, `__release__`) or fold `## [Unreleased]` in `CHANGELOG.md`?
4. The migrations added in `database/migrations/`, and the exact output of
   `python dev.py migrate --pretend` if a database is available.

## Phase A — Parallel fan-out

Spawn three subagents concurrently with the Agent tool. **Issue all three Agent calls in a
single assistant turn so they run in parallel** — sequential calls defeat the purpose of this
command.

Each call passes `subagent_type` equal to the agent's `name`:

1. **`code-reviewer`** (`.claude/agents/code-reviewer.md`) — five-axis review (correctness,
   readability, architecture, security, performance) of the diff. Include Craft governance:
   layer caps (controller 150 lines and 15 per action, service 300, repository 250, function
   25, complexity 6), no SQL in controllers or services, no markup in Python, CRUD through the
   CRUD builder, services resolved from the container, type hints and Google docstrings, no
   bare or broad `except`, English identifiers, no hardcoded user-facing copy. Output the
   standard review template with Critical / Important / Suggestion findings and `file:line`.
2. **`security-auditor`** (`.claude/agents/security-auditor.md`) — vulnerability and
   threat-model pass: OWASP Top 10, authentication, Gate/Policy authorization, tenant
   isolation, mass assignment, SQL injection through raw queries, `@csrf` on state-changing
   forms, `@honeypot`/`@antispam` on public forms, `hmac.compare_digest` for secrets and
   tokens, secrets handling, dependency vulnerabilities (`pip-audit`), personal data under
   LGPD/GDPR. Output the standard audit report with severities.
3. **`test-engineer`** (`.claude/agents/test-engineer.md`) — run `python -m pytest tests`
   (and `tests/test_release_non_regression.py` explicitly), then analyze coverage of the change:
   happy path, edge cases, validation and error paths (`code` + `message_key`), authorization
   denials, concurrency and queue behavior, and SQLite-versus-PostgreSQL differences. Output
   the standard coverage analysis with the exact failing output, if any.

Constraints of the subagent model:

- Subagents cannot spawn other subagents — do not let one agent delegate to another.
- Each subagent has its own context window and returns only its report to this session.
- If the scope needs agents that converse rather than just report, use the patterns in
  `.claude/references/orchestration-patterns.md`.

**Agent resolution.** A project-level definition in `.claude/agents/` or a user-level one in
`~/.claude/agents/` with the same `name` is what gets invoked. Customize the agents there and
`/ship` picks the customization up automatically.

## Phase B — Merge in the main context

Once all three reports are back, the main agent (never one of the specialists) synthesizes
them and verifies directly what no specialist covered:

1. **Code quality** — Aggregate Critical and Important findings from `code-reviewer`, plus any
   failing tests from `test-engineer`. Run the gates yourself and record the exit codes:
   `ruff check engine` (or `ruff check .` in an application), `python .claude/rules/lint_language.py`,
   `python .claude/rules/lint_structure.py`. De-duplicate findings raised by more than one agent.
2. **Security** — Promote every Critical or High `security-auditor` finding to a launch
   blocker. Cross-check against `code-reviewer`'s security axis.
3. **Performance** — Pull from `code-reviewer`'s performance axis (N+1 queries, missing indexes,
   work that belongs on a queue); check Core Web Vitals where pages changed, using
   `.claude/references/performance-checklist.md`.
4. **Accessibility** — Not covered by the three agents. Verify keyboard navigation, labels,
   `@error('field')` association, focus handling and contrast directly, or walk
   `.claude/references/accessibility-checklist.md`.
5. **Internationalization** — Every new user-facing string is a translation key with rows for
   `en`, `pt-BR` and `es` in the same change; no copy hardcoded in Python, Forge templates,
   e-mails or JavaScript.
6. **Database and infrastructure** — Verify directly:
   - Every migration is forward-only and additive, or an expand/migrate step; nothing drops or
     renames a column or table the previous release still reads (contract steps ship later and
     alone — see `.claude/skills/deprecation-and-migration/SKILL.md`).
   - Business entities are soft-deleted; no physical `DELETE` or `TRUNCATE` on them.
   - No `migrate:fresh`, `migrate:reset`, `migrate:refresh`, `db:wipe` or `db:drop` in code,
     scripts, workflows or runbooks.
   - Environment variables and secrets documented; health (`/health`) and readiness (`/ready`)
     endpoints available; queue workers and scheduler accounted for; feature flags have an owner
     and removal date.
7. **Release invariants and documentation** — Verify directly:
   - `CHANGELOG.md` has the change under `## [Unreleased]` in a Keep a Changelog category; for a
     release cut, the heading `## [X.Y.Z] rNNNNN — YYYY-MM-DD` exists with a fresh
     `## [Unreleased]` above it.
   - For a release cut: `pyproject.toml` version equals `engine/__init__.py` `__version__`,
     `__release__` is exactly the previous counter plus one, and the tag will be `vX.Y.Z-rNNNNN`.
   - Public facades and container bindings keep their accessors and signatures, or ship a
     deprecated alias for one release with a `Deprecated` changelog entry.
   - Commits are Conventional Commits in English; README, API docs and ADRs updated where needed.

## Phase C — Decision and rollback

Produce a single output:

```markdown
## Ship Decision: GO | NO-GO

### Gate results
- pytest (SQLite): pass | fail — [summary]
- pytest (PostgreSQL): pass | fail | not run — [reason]
- test_release_non_regression.py: pass | fail
- ruff: pass | fail
- lint_language.py: exit [code]
- lint_structure.py: exit [code]

### Blockers (must fix before ship)
- [Source: Critical finding + file:line]

### Recommended fixes (should fix before ship)
- [Source: Important finding + file:line]

### Acknowledged risks (shipping anyway)
- [Risk + mitigation + who accepted it]

### Database changes
- Migrations: [list, each marked additive | expand | migrate | contract]
- Previous release runs against the new schema: yes | no (no = blocker)

### Rollback plan
- Trigger conditions: [signals that prompt rollback, with thresholds]
- Rollback procedure: [turn off flag X | redeploy image vX.Y.Z-rNNNNN without migrations] — schema is never rewound
- Data correction, if needed: [forward migration or data-fix job; soft deletes only]
- Recovery time objective: [target]

### Specialist reports (full)
- [code-reviewer report]
- [security-auditor report]
- [test-engineer report]
```

## Rules

1. The three Phase A agents run in parallel — never sequentially.
2. Agents do not call each other. The main agent merges in Phase B.
3. A rollback plan is mandatory before any GO, and it never relies on reversing migrations,
   `migrate:reset`, or restoring a backup as the normal path.
4. Any Critical finding, any failing gate, a non-additive migration shipped alongside the code
   that depends on it, or a broken release invariant makes the default verdict NO-GO unless the
   user explicitly accepts the risk — and a failing gate is never accepted by weakening the gate.
5. **Skip the fan-out only if all of the following are true:** the change touches two files or
   fewer, the diff is under 50 lines, and it touches none of authentication, authorization,
   payments, data access, migrations, personal data, or configuration and environment. Even then
   run the gates yourself and produce the Phase C output. `/ship` exists for production-bound
   changes: when the blast radius is non-trivial, run the parallel review even if the diff looks
   small.
