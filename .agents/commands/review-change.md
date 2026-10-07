---
description: Review the current change on six axes — correctness, readability, architecture, security, performance and Craft governance
argument-hint: [optional scope: file, directory, commit range or branch]
---

Follow the `code-review-and-quality` skill (`.claude/skills/code-review-and-quality/SKILL.md`),
acting as the `code-reviewer` persona (`.claude/agents/code-reviewer.md`).

Scope: $ARGUMENTS — if empty, review the staged changes, then unstaged changes, then the commits on
the current branch that are not on the main branch (`git diff`, `git diff --staged`,
`git log main..HEAD`).

Review the change across all six axes:

1. **Correctness** — Does it match the spec? Edge cases and error paths handled? Do the pytest tests
   verify the behavior?
2. **Readability** — Clear English names consistent with the glossary? Straightforward logic with
   guard clauses? No dead or commented-out code?
3. **Architecture** — Follows existing patterns and the core -> modules -> plugins tiers? Clean
   boundaries? Right abstraction level? Does a refactor reduce complexity rather than move it?
4. **Security** — Input validated through a `FormRequest`? Authorization via Gate or policy?
   Secrets out of code and logs? `@csrf` on state-changing forms, `@honeypot`/`@antispam` on public
   forms, `hmac.compare_digest` for tokens? Personal data protected (LGPD/GDPR)? Use the
   `security-and-hardening` skill (`.claude/skills/security-and-hardening/SKILL.md`).
5. **Performance** — No N+1 queries (eager-load with `with_()`)? No unbounded fetches? Pagination on
   list endpoints? Use the `performance-optimization` skill
   (`.claude/skills/performance-optimization/SKILL.md`).
6. **Craft governance**
   - Layer caps: controller 150 lines/file and 15 lines/action, service 300, repository 250, any
     function 25 lines with cyclomatic complexity <= 6
   - No SQL in controllers or services; no HTML in Python (markup in Forge templates)
   - Plain CRUD through `python dev.py make:crud`; services resolved from the container;
     cross-cutting logic in `app/plugins/`
   - Type hints on every signature, Google docstrings, no bare or broad `except`
   - No hardcoded user-facing text; every new translation key has `en`, `pt-BR` and `es` rows in
     the same change; errors carry `code` + `message_key`
   - `CHANGELOG.md` entry under `## [Unreleased]`
   - Migrations forward-only (no `migrate:fresh`, `migrate:reset`, `migrate:refresh`, `db:wipe`,
     `db:drop`); soft deletes for business entities
   - Frontend is vanilla or vendored `.js`/`.css` — no TypeScript, npm or Node build

Run the gates and include their real results:

```bash
python -m pytest tests
ruff check engine
python .claude/rules/lint_language.py
python .claude/rules/lint_structure.py
```

Label every finding **Critical**, **Required**, **Optional** or **Nit**. A red gate, a destructive
migration or hardcoded user-facing copy is Critical.

Output a structured review using the template in `.claude/agents/code-reviewer.md`, with specific
`file:line` references and a fix recommendation for every Critical and Required finding. Do not
edit files — this command reports; fixes are a separate step.
