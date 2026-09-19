---
description: Simplify code for clarity and maintainability — reduce complexity without changing behavior
argument-hint: [optional scope: file, directory or commit range]
---

Follow the `code-simplification` skill (`.claude/skills/code-simplification/SKILL.md`).

Scope: $ARGUMENTS — if empty, simplify the recently changed code (`git diff`, `git diff --staged`,
and the commits on the current branch not yet on the main branch).

Simplify the target code while preserving its exact behavior:

1. Read the project conventions: `.claude/rules/AGENTS.md`,
   `.claude/rules/CRAFT_ENGINEERING_GOVERNANCE.md` and the project `CLAUDE.md`
2. Identify the target code — recent changes unless a broader scope was given
3. Understand the code's purpose, layer, callers, edge cases and pytest coverage before touching it
   (check git blame and `CHANGELOG.md` for the original context)
4. Run `python .claude/rules/lint_structure.py` to list cap and complexity violations in scope
5. Scan for simplification opportunities:
   - Deep nesting -> guard clauses or extracted helpers
   - Functions over 25 lines (15 in a controller action) or complexity over 6 -> split by
     responsibility, helpers prefixed `_`
   - Files over their layer cap -> focused sub-controllers or services
   - Chained conditional expressions or long `if`/`elif` dispatch -> `if` chain, `match` or a
     typed lookup
   - Generic or non-English names -> descriptive names from the glossary
   - Duplicated logic -> a shared function, or a plugin in `app/plugins/` when cross-cutting
   - Hand-rolled engine features -> `paginate()`, `make:crud`, a `FormRequest`
   - Dead code -> remove after confirming it is unreferenced
6. Never trade governance for brevity: SQL stays in repositories or the ORM, markup stays in Forge
   templates, user-facing text stays in translation keys, services stay container-resolved, type
   hints and docstrings stay
7. Apply each simplification incrementally and run `python -m pytest tests` after each change
8. Verify the whole result:

   ```bash
   python -m pytest tests
   ruff check engine
   python .claude/rules/lint_language.py
   python .claude/rules/lint_structure.py
   ```

9. Add a `CHANGELOG.md` entry under `## [Unreleased]` (`Changed`) and keep the refactor in its own
   Conventional Commit, separate from feature or bug-fix work

If tests fail after a simplification, revert that change and reconsider — never edit a test to make
a simplification pass. Use `/review-change` (the `code-review-and-quality` skill) to review the
result.
