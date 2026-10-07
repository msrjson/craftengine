---
description: Run the TDD workflow with pytest — write failing tests, implement, verify. For bugs, use the Prove-It pattern.
argument-hint: [feature or bug description]
---

Apply the `test-driven-development` skill
(`.claude/skills/test-driven-development/SKILL.md`) to: $ARGUMENTS

First, read `pyproject.toml` and `tests/conftest.py` to learn the runner configuration
and the fixtures the suite provides. Use `.claude/references/testing-patterns.md` for
pytest idioms.

For new features:

1. Write tests that describe the expected behavior (they must FAIL)
2. Run them and confirm they fail for the expected reason:
   `python -m pytest tests/test_<subject>.py -x`
3. Implement the minimum code to make them pass
4. Refactor while keeping tests green, within the layer caps (function 25 lines,
   complexity 6, controller action 15 lines)

For bug fixes (Prove-It pattern):

1. Write a test that reproduces the bug (must FAIL)
2. Confirm the test fails
3. Implement the fix at the root cause
4. Confirm the test passes
5. Run the full suite for regressions: `python -m pytest tests`

For dialect-sensitive changes (JSONB, row-level security, locking, extensions), also run
the suite against a disposable PostgreSQL database with `CRAFT_TEST_DB=pgsql` and the
`DB_*` connection variables set.

For browser-related issues, also apply the `browser-testing-with-devtools` skill
(`.claude/skills/browser-testing-with-devtools/SKILL.md`) to verify the rendered page
with Chrome DevTools.

Before reporting done, run the gates and report their real output:

- `python -m pytest tests`
- `ruff check engine`
- `python .claude/rules/lint_language.py`
- `python .claude/rules/lint_structure.py`

Never skip, `xfail` or weaken a test to reach green. Add a `CHANGELOG.md` entry under
`## [Unreleased]` for the behavior change or fix.
