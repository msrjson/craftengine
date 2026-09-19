---
name: constraint-driven-development
description: Writes the project's quality bar down as an enforced contract in CONSTRAINTS.md and stops agents quietly lowering it. Use when no quality bar is written, when asked to set up constraints or define standards, when coverage, security, accessibility or performance should become enforced numbers, when an agent keeps silencing checks or skipping tests to reach green, or when you need a threshold and have no number in mind.
---

# Constraint-Driven Development

## Overview

Other skills describe what good looks like. The `code-review-and-quality` skill
gives review axes, `test-driven-development` gives a cycle,
`security-and-hardening` gives a threat list. All of that is prose an agent reads
and may or may not follow, and none of it outlives the session.

This skill produces something different: a written record of **this project's**
bar, with numbers, that survives the conversation and can be checked mechanically.

The reason matters. When you wrote the code yourself, reading it told you whether
it was good. An agent writes more in an afternoon than anyone reads in a week, so
judgement has to move out of heads and into checks that run around the loop. Those
checks must exist, must carry numbers somebody actually chose, and must fire close
enough to the work that the agent fixes its own output.

Spec-driven development says what to build. Test-driven development proves it
works. Constraint-driven development defines "good enough to ship" before anyone
argues about it in a pull request.

A Craft Engine project never starts from zero: the governance in `.claude/rules/`
already fixes part of the bar (layer caps, language, i18n, release
non-regression) and ships two gates, `lint_language.py` and `lint_structure.py`.
`CONSTRAINTS.md` records those as enforced rows and adds the dimensions the
project chooses on top. It never restates them more loosely.

## When to Use

Apply this skill when:

- Starting a project or a significant feature and no quality bar is written down
- The user asks to "set up constraints", "add quality gates", "define our
  standards" or "stop the agent shipping junk"
- An agent produces more code than anyone reads line by line
- CI has checks, but nobody can say which ones block a merge and which are decoration
- Coverage, security, performance or accessibility numbers get argued per pull
  request instead of decided once
- You are about to run `/build auto` or any autonomous loop, and the only thing
  between it and the main branch is a test suite the same agent wrote

**When NOT to use:**

- The project already has a `CONSTRAINTS.md` and the user is not changing it —
  read it and follow it
- One-off scripts, spikes, throwaway prototypes
- The user wants a review right now (the `code-review-and-quality` skill) or a CI
  pipeline built (the `ci-cd-and-automation` skill)
- Code with an expected lifetime of two weeks — the floor below is still worth it,
  the rest is not

## Loading Constraints

The interview needs a live user. **Do not run it in non-interactive contexts**
(CI, scheduled runs, autonomous runs such as `/build auto`). If constraints are
missing there, apply the Floor below plus the governance gates, record that you
did, and flag the rest for a human.

## The Process

### Step 1: Detect before you ask

Never ask what you can read. Before the first question, gather:

| What | Where to look |
|------|---------------|
| Language, version, extras | `data/pyproject.toml` (`[project]`, `[project.optional-dependencies]`) |
| Test runner and layout | `[tool.pytest.ini_options]`, `data/tests/`, `tests/conftest.py` |
| Existing linters | `[tool.ruff]` in `pyproject.toml`, `.claude/rules/lint_language.py`, `.claude/rules/lint_structure.py` |
| Coverage today | `pytest-cov` in dev extras; run the suite once with `--cov` |
| Pre-commit hooks | `data/.pre-commit-config.yaml` |
| CI | `.github/workflows/` |
| Release rules | `.claude/rules/RELEASE_NON_REGRESSION_STANDARD.md`, `tests/test_release_non_regression.py` |
| Agent configuration | `.claude/`, `AGENTS.md`, `CLAUDE.md` |

Report what you found in two lines, then ask only what is left.

### Step 2: Four questions, each with a default

Follow the one-question-at-a-time discipline of the `interview-me` skill
(`.claude/skills/interview-me/SKILL.md`), with one change: every question has a
default, so "I don't know" is a complete answer that still yields a working config.

```
Q1: Beyond the floor and the governance gates, which of these do you want enforced?
    (a) Test coverage on new code
    (b) Security scanning (code, secrets, dependencies)
    (c) Performance budgets
    (d) Accessibility
    (e) Architecture boundaries beyond the structure gate
GUESS: (a) and (b) — pytest-cov is already a dev dependency and the app handles user input.
DEFAULT if unsure: (a) and (b).
Cost of each: (c) and (d) need a running URL, (e) needs an import contract written.
```

```
Q2: When a check fails while the agent is mid-task, should it block or warn?
GUESS: Block. You run agents unattended, and a warning nobody reads is not a warning.
DEFAULT if unsure: Block on the floor and the governance gates, warn on everything else for two weeks.
```

```
Q3: Do you have target numbers, or should I measure where you are today and hold that line?
GUESS: Measure. Most teams have no number, and an invented one gets ignored.
DEFAULT if unsure: Measure and hold. See "Ratchets" below.
```

```
Q4: What is the slowest check you will tolerate before the agent hands work back?
GUESS: About 90 seconds. Longer and people stop running it.
DEFAULT if unsure: 90 seconds at task end, unlimited in CI.
```

Stop at four. A twelve-question intake produces a config nobody understands and a
user who regrets starting.

### Step 3: Write CONSTRAINTS.md

One file at the repository root. Any agent can read it, and a change to it shows
up in review, where it belongs.

```markdown
# Constraints

Last reviewed: 2026-09-12 by @maintainer

## Floor (always enforced, no setup required)

- No new suppression comments: `# noqa`, `# type: ignore`, `# pragma: no cover`, `# nosec`, `lint-language: ignore`
- No unimplemented stubs: `raise NotImplementedError`, `except ...: pass`, a `TODO` in place of an implementation
- No bare or broad `except`
- No skipped or deleted tests without a reason in the commit message
- No secrets in source
- No destructive database commands: `migrate:fresh`, `migrate:reset`, `migrate:refresh`, `db:wipe`, `db:drop`
- This file, `.claude/rules/` and the gate configs do not get weakened to make a change pass

## Enforced with numbers

| Dimension | Rule | Checked by | Runs at |
|-----------|------|-----------|---------|
| Language | English artifacts, zero hardcoded copy | `python .claude/rules/lint_language.py` | every edit |
| Structure | Layer caps, 25-line functions, complexity ≤ 6, typed signatures | `python .claude/rules/lint_structure.py` | every edit |
| Lint | Zero errors from our ruff config | `ruff check engine` | every edit |
| Types | Zero type errors | `mypy app` | task end |
| Secrets | No secrets in source | `gitleaks detect --redact --no-banner` | every edit |
| Tests | 100% pass | `python -m pytest tests` | task end, CI |
| Coverage | Changed lines ≥ 80% covered | `python -m pytest tests --cov --cov-report=xml` + `diff-cover coverage.xml --fail-under=80` | task end, CI |
| Release | Version sync, facade integrity, database safety | `python -m pytest tests/test_release_non_regression.py` | CI |
| Security: code | No high findings | `semgrep scan --config p/python --config p/owasp-top-ten` | CI |
| Security: deps | Nothing at high or above | `osv-scanner scan source -r .` | CI |
| Accessibility | Zero critical or serious violations | `axe $PREVIEW_URL --tags wcag2a,wcag2aa,wcag21aa` | preview deploy |
| Performance | LCP ≤ 2500 ms, CLS ≤ 0.1 | `lighthouse $PREVIEW_URL --output=json --quiet` | preview deploy |

Every row names the command that produces the verdict. A dimension with a
number and no command in this column is an aspiration, not a constraint.

## Measured, not yet enforced

| Metric | Today | Direction |
|--------|-------|-----------|
| Project coverage | 62.4% | must not fall |
| Total page weight (home) | 184 kB | must not grow |

## Exceptions

| ID | Rule | Path | Reason | Owner | Expires |
|----|------|------|--------|-------|---------|
| W1 | `mypy` strict | `app/modules/legacy_reports/**` | Rewrite tracked in issue #441 | @maintainer | 2026-12-01 |
```

Then add one line to `AGENTS.md` and `CLAUDE.md`: `Read CONSTRAINTS.md before
writing code. Do not weaken it to make a change pass.`

### Step 4: Install what each dimension needs

Picking a dimension means installing something. Never leave the user with a
number and no mechanism, and never invent a checker when a de facto one exists:
these tools are listed because their rule formats and thresholds are what the rest
of the ecosystem targets, so existing configuration keeps working.

Python tools go into the project's dev extras or the CI image. Browser-side tools
(axe, Lighthouse) are **never** project dependencies: a Craft project has no Node
toolchain and no `npm`, so they run from a CI image or from Chrome DevTools.

| Dimension | Tool | Install | Run | Gate on |
|-----------|------|---------|-----|---------|
| Language | project gate | already there | `python .claude/rules/lint_language.py` | non-zero exit |
| Structure | project gate | already there | `python .claude/rules/lint_structure.py` | non-zero exit |
| Lint | ruff | dev extra (already there) | `ruff check engine` / `ruff check app` | any error |
| Types | mypy | `pip install mypy` | `mypy app` | any error |
| Coverage | pytest-cov + diff-cover | pytest-cov already there; `pip install diff-cover` | `python -m pytest tests --cov --cov-report=xml` then `diff-cover coverage.xml --compare-branch=origin/main --fail-under=80` | coverage of changed lines |
| Security: code | Semgrep | `pipx install semgrep` | `semgrep scan --config p/python --config p/owasp-top-ten` | any high finding |
| Security: secrets | gitleaks | CI image or system package | `gitleaks detect --redact --no-banner` | any finding |
| Security: dependencies | osv-scanner (or pip-audit) | CI image, or `pip install pip-audit` | `osv-scanner scan source -r .` / `pip-audit` | high or above |
| Performance: page | Lighthouse | CI image, or Chrome DevTools locally | `lighthouse $URL --output=json --quiet` | LCP, CLS, performance score |
| Performance: page weight | Lighthouse | same | `total-byte-weight` audit in the same JSON report | per-page byte budget |
| Accessibility | axe-core | CI image, or the Lighthouse accessibility category | `axe $URL --tags wcag2a,wcag2aa,wcag21aa` | zero critical or serious |
| Architecture | import-linter | `pip install import-linter` | `lint-imports` | any broken contract |
| Assertion quality | mutmut | `pip install mutmut` | `mutmut run` with `paths_to_mutate` set to the changed modules | mutation score |

Five things that bite if you skip them:

1. **`--redact` on gitleaks is not optional.** Without it the matched secret lands
   in the agent's transcript, which is how a leaked key ends up in a log, a summary
   or a commit message. Report the rule and the location, never the value.
2. **Lighthouse and axe need a URL.** They only work against a running app, so they
   belong to the runtime stage against a preview deploy or a local
   `python dev.py serve` started first. If the project has no URL — a plugin
   package, a CLI tool — say so and drop the dimension rather than inventing a
   check that cannot run.
3. **Scope the expensive ones to the diff.** Mutation testing on the whole engine
   takes hours and gets switched off; on the modules a change touched it takes
   minutes. Semgrep also accepts a path list.
4. **Coverage needs no second test run.** Read the `coverage.xml` the suite already
   wrote and intersect it with `git diff` (that is what diff-cover does). Running
   the suite twice to get a number is the fastest way to make people hate this.
5. **Semgrep registry rules are free to run; check the licence before
   redistributing them.** Opengrep is a drop-in fork with the same rule format and
   JSON output if that matters to your legal team.

Wire each tier somewhere reproducible without an agent. Fast checks go into
`.pre-commit-config.yaml` (run from `data/`, the application root); task-end and
full checks go into the CI workflow:

```yaml
repos:
  - repo: local
    hooks:
      - id: language-standard
        name: English-only code + zero hardcoded copy
        entry: python .claude/rules/lint_language.py
        language: system
        pass_filenames: false
      - id: structure-standard
        name: Layer caps, typing and complexity
        entry: python .claude/rules/lint_structure.py
        language: system
        pass_filenames: false
      - id: ruff
        name: ruff
        entry: ruff check engine
        language: system
        pass_filenames: false
      - id: gitleaks
        name: secrets
        entry: gitleaks detect --redact --no-banner
        language: system
        pass_filenames: false
```

Adjust the gate paths to where the rules actually live relative to `data/` in
your checkout. The tiers are what matter: **fast** runs after an edit (gates,
ruff, secrets), **task** runs when the agent thinks it is done (fast plus pytest
with changed-line coverage), **full** runs in CI (task plus Semgrep, dependency
scan, release non-regression test, runtime checks).

The commands now live in two places: the `Checked by` column of `CONSTRAINTS.md`
and the hook/CI files. `CONSTRAINTS.md` is canonical: it carries the reason next to
each command and it shows up in review. The hook and CI files mirror it; when they
drift, the file wins.

### Step 5: Wire it to the lifecycle

The single biggest mistake is running everything everywhere. A check that stalls
the agent gets switched off, and a gate people switched off is worse than none,
because the bar still looks like it exists.

| Phase | Command | What runs | Budget |
|-------|---------|-----------|--------|
| BUILD | `/build` | Language and structure gates, ruff, secrets, the floor | under 5 s, changed files only |
| VERIFY | `/test` | Related tests, coverage on changed lines | under 90 s |
| REVIEW | `/review-change` | Everything, plus the guards below | minutes |
| SHIP | `/ship` | Direction checks, release non-regression, no regressions | CI |

Two rules keep this tolerable:

1. **Scope to the diff.** Check the lines this change touched, not the whole
   repository. Changed-line coverage is a number the agent can move; project
   coverage is one it inherited.
2. **Cost decides placement.** Anything over a few seconds leaves the edit loop.
   Mutation testing on the whole codebase takes hours; on the modules a change
   touched it takes minutes, and that is the difference between a check people run
   and one they do not.

### Step 6: Guard the bar itself

Someone will point out that if the agent writes the code and the checks, the checks
prove nothing. Half right, and worth engineering around.

Agents do not craft clever loopholes. They hit a red check and take the cheapest
road to green. Watch the diff for these five moves at review time:

1. **The threshold moved.** A budget lowered, a severity dropped, a check removed
   from the fast tier, a rule added to `[tool.ruff.lint] ignore`, a token added to
   the language gate's allowlist, a cap raised in the structure gate config.
   Compare `CONSTRAINTS.md`, `.claude/rules/` and the gate configs against the
   branch point.
2. **A test got easier.** `@pytest.mark.skip` or `xfail` added, `pytest.skip()`
   called, a test file deleted, assertions removed from tests that stayed.
3. **A checker got silenced.** A new `# noqa` or `# type: ignore`. Five
   suppressions deserve special attention because they switch off a check you rely
   on: `# pragma: no cover` drops code from coverage instead of testing it,
   `# pragma: no mutate` hides a surviving mutant, `# nosec` and `nosemgrep` and
   `gitleaks:allow` do it for security findings, and `lint-language: ignore` does it
   for the language standard.
4. **Work is unfinished.** `raise NotImplementedError`, an `except` whose body is
   `pass` turning a failure into silence, a `TODO` standing where the implementation
   should be.
5. **An exception appeared.** A new row in the Exceptions table nobody discussed.

None of this needs tooling beyond `git diff`. Tightening the bar is silent;
loosening it is loud.

Unlike the numbered dimensions, the floor has no de facto tool, so an agent asked
to enforce it tends to write a checker from scratch, and two agents write two
different ones. A reference implementation of these five checks ships with this
skill in `.claude/skills/constraint-driven-development/references/floor-guard.md`
(diff-scoped, exit `0`/`1`/`2`, patterns adaptable). Adapt it rather than
reinventing it, for the same reason every dimension names a de facto tool: the
mechanism stays identical across runs and projects.

**Not all checks are equally circular.** Rank them by one question: can the agent
make this pass by writing code that does not work?

- **External** — axe-core encodes WCAG, osv-scanner reads a vulnerability database,
  Lighthouse measures a real browser. The agent cannot argue with these.
- **Project** — the language and structure gates, ruff config, import contracts.
  A human owns the files.
- **Suite** — your own tests. The most useful, and the only genuinely circular kind.

A bar made entirely of the third kind is worth less than one with an outside
opinion in it. Check that at least one external constraint is present.

### Step 7: Ratchets, when you don't have a number

Set 80% coverage on a codebase at 62% and you get a red build forever, then a team
that learns to ignore red builds.

The alternative needs no decision: record where you are and refuse to get worse.
Put it in the "Measured, not yet enforced" table with today's number and a
direction. Every check compares against the recorded value, not an aspiration.
When a number improves, update it; when it drops, that is the finding.

This also answers a fair objection. Models are rewarded for passing tests, which
can be evaluated in seconds. Architectural rot shows up over months and never
reaches the weights. A ratchet is the missing penalty, written where the build can
see it.

## Sane Defaults

When the user has no opinion, use these. They are chosen so most codebases meet
them on day one.

| Constraint | Default | Why this number |
|------------|---------|-----------------|
| Coverage of changed lines | ≥ 80% | High enough to force a test, low enough to allow a config line |
| Project coverage | today's value, must not fall | No argument needed to adopt |
| Mutation score (if used) | ≥ 60% to start | Typical for a suite never mutated before; 80% is mature |
| Dependency vulnerabilities | nothing at high or above | Below that is mostly noise |
| LCP | ≤ 2500 ms | Core Web Vitals "good" threshold |
| CLS | ≤ 0.1 | Same |
| Accessibility | zero critical or serious axe violations | Moderate and minor are often debatable |
| Function size / complexity | 25 lines, complexity ≤ 6 | Already fixed by the Craft governance; not negotiable here |
| Exception lifetime | 90 days | Long enough to plan the fix, short enough to remember |
| Ratchet tolerance | 0.5% | Absorbs drift when an unrelated file moves the number |

State the number and the reason together. A threshold without a rationale gets
deleted by the next person who hits it.

## Escalation Path

Constraints come in three levels of teeth. Start at the first.

1. **Written only.** `CONSTRAINTS.md` exists and agents read it. Costs nothing,
   catches honest mistakes, relies on compliance.
2. **Scripted.** The fast tier in `.pre-commit-config.yaml` and the task/full tiers
   in CI. Deterministic, no new dependency.
3. **Tool-backed.** A dedicated runner that handles diff scoping, budgets, ratchets
   and the guard checks. Use it when the configuration outgrows a few hook entries.
   The floor-guard reference is the starting point for the guard half.

Most projects should stop at level 2. Move to 3 when you maintain more than about
thirty lines of check-running glue.

**A first run can be floor-only.** The floor guard is diff-only and needs no
installs, and the governance gates already exist, so both can be enforced on day
one while numbered dimensions are added as each tool is installed. Security tools
that install machine-wide (gitleaks, osv-scanner) can run in CI only if you prefer
clean workstations; declare where each dimension runs in the `Runs at` column.

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "We'll add constraints once the code settles" | Code settles around whatever was allowed while it was moving |
| "The tests are the constraints" | Tests you wrote prove you agree with yourself; they say nothing about changed-line coverage, dependency risk or page weight |
| "The gates in `.claude/rules/` are enough" | They cover language and structure. Coverage, security, accessibility and performance are not theirs to judge |
| "We can't hit 80% coverage" | Then don't set 80%. Set today's number and hold it |
| "This will slow the agent down" | Only if slow checks sit in the fast loop. That is a placement error, not an argument against constraints |
| "I'll remember what our standards are" | The agent won't, and it writes most of the code |
| "Constraints will block us shipping" | An exception with an owner and a date unblocks you. Deleting the constraint unblocks everyone forever |

## Red Flags

Stop and reconsider if you notice:

- The interview ran past four questions, or produced a config the user cannot explain
- A budget was set that the codebase fails today, with no plan to reach it
- A dimension in `CONSTRAINTS.md` has a number but no tool behind it
- A checker was hand-rolled when a de facto one exists, so the team's existing config is ignored
- A browser tool was added as a project `npm` dependency
- Every constraint is judged by the project's own test suite, with no external opinion
- `CONSTRAINTS.md`, a gate config or `.claude/rules/` changed in the same commit as the feature that was failing
- An exception has no owner, or an expiry more than a year out
- The agent proposed relaxing a threshold instead of fixing the code
- Slow checks landed in the edit loop and someone started committing with `--no-verify`
- Nobody has opened `CONSTRAINTS.md` since it was written

## Verification

The skill was applied correctly when:

- [ ] `CONSTRAINTS.md` exists at the repository root, and every number in it has a stated reason
- [ ] The floor is enforced and passes on the current codebase without changes
- [ ] The language and structure gates are listed as enforced rows
- [ ] Every dimension the user picked has a tool installed and a command that runs today
- [ ] Each constraint says where it runs, and the fast tier stays under a few seconds
- [ ] At least one constraint is external (not judged by this project's own tests)
- [ ] Measured-only metrics record today's value and a direction
- [ ] Exceptions have an owner and an expiry date
- [ ] `AGENTS.md` or `CLAUDE.md` points at the file
- [ ] A trial run on the current branch produces no failures the user disagrees with

## See Also

- The `interview-me` skill (`.claude/skills/interview-me/SKILL.md`) — the one-question-at-a-time discipline the intake borrows
- The `code-review-and-quality` skill (`.claude/skills/code-review-and-quality/SKILL.md`) — how to review; this skill decides what the review enforces
- The `ci-cd-and-automation` skill (`.claude/skills/ci-cd-and-automation/SKILL.md`) — the pipeline these constraints run in
- The `test-driven-development` skill (`.claude/skills/test-driven-development/SKILL.md`) — the suite coverage and mutation constraints measure
- The `security-and-hardening` skill (`.claude/skills/security-and-hardening/SKILL.md`) — what the security dimension should contain
- The `performance-optimization` skill (`.claude/skills/performance-optimization/SKILL.md`) — where the performance numbers come from
- `.claude/references/definition-of-done.md` — the standing bar every task clears
