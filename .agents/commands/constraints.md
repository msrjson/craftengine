---
description: Define and enforce this project's quality bar — detect, interview, sane defaults, CONSTRAINTS.md
argument-hint: [check | guard | ratchet]
---

Apply the `constraint-driven-development` skill (`.claude/skills/constraint-driven-development/SKILL.md`).

$ARGUMENTS

Default behaviour with no arguments: set up constraints for this repository.

1. **Detect first.** Read `data/pyproject.toml` (version, extras, `[tool.pytest]`,
   `[tool.ruff]`), the test layout under `tests/`, `data/.pre-commit-config.yaml`,
   the gates and standards in `.claude/rules/`, current coverage output, CI
   workflows in `.github/workflows/`, and the agent configuration (`.claude/`,
   `AGENTS.md`, `CLAUDE.md`). Report what you found in two lines. Never ask for
   anything you can read.

2. **Interview, at most four questions.** One at a time, each with your best guess
   and a usable default so "I don't know" still produces a working config:
   - Which dimensions beyond the floor and the governance gates (coverage, security,
     performance, accessibility, architecture)
   - Block or warn when a check fails mid-task
   - Target numbers, or measure today's values and hold them
   - Slowest check tolerated before handing work back

   Skip the interview in non-interactive runs: apply the floor and the governance
   gates, say so, and flag the rest for a human.

3. **Write `CONSTRAINTS.md`** at the repository root with a Floor section, enforced
   numbers (the language and structure gates always among them), measured-only
   metrics with today's values, and an exceptions table with owners and expiry
   dates. Every number needs a stated reason.

4. **Install what each picked dimension needs.** A dimension with a number and no
   tool behind it is an aspiration. Use the de facto tool so existing config keeps
   working: mypy for types, ruff for lint, pytest-cov with diff-cover for
   changed-line coverage, Semgrep for code scanning, gitleaks (always `--redact`)
   for secrets, osv-scanner or pip-audit for dependencies, axe-core for
   accessibility, Lighthouse for web vitals and page weight, import-linter for
   boundaries, mutmut for assertion quality. Browser tools run from a CI image or
   Chrome DevTools, never as a project `npm` dependency. Record the exact command
   next to each rule in `CONSTRAINTS.md`. Accessibility and performance need a
   running URL; if the project has none, say so and drop the dimension rather than
   inventing a check.

5. **Place each check by cost.** Gates, ruff and secrets in the edit loop (seconds),
   as local hooks in `.pre-commit-config.yaml`. Related tests and changed-line
   coverage at task end (under 90 s). Everything else at review or in CI. Scope
   checks to the diff, not the whole repository.

6. **Point the agent at it.** Add a line to `CLAUDE.md` and `AGENTS.md` telling
   agents to read `CONSTRAINTS.md` and never weaken it to make a change pass.

7. **Verify.** Run the constraints against the current branch. If anything fails
   that the user disagrees with, fix the constraint now rather than leave a gate
   people will learn to ignore. Never loosen `.claude/rules/` to get there.

Sub-commands:
- `/constraints check` — run the current constraints against this branch and report
- `/constraints guard` — inspect the diff for a weakened bar: lowered thresholds (in
  `CONSTRAINTS.md`, gate configs or `pyproject.toml`), skipped or deleted tests,
  removed assertions, new suppression comments, unfinished stubs, swallowed
  exceptions, destructive database commands, new exceptions. Use the reference in
  `.claude/skills/constraint-driven-development/references/floor-guard.md`
- `/constraints ratchet` — record today's measured values as the floor that must not fall
