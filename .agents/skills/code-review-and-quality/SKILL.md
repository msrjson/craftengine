---
name: code-review-and-quality
description: Runs a multi-axis code review with Craft Engine governance gates. Use before merging any change, when reviewing code written by yourself, another agent or a human, or whenever a change must be judged on quality before it reaches the main branch.
---

# Code Review and Quality

## Overview

Every change is reviewed before it merges — no exceptions. The review walks six axes:
correctness, readability, architecture, security, performance, and **Craft governance**
(layer caps, layer purity, container resolution, i18n, changelog, migrations, gates).

**The approval standard:** approve a change when it clearly improves the overall health of
the codebase, even if it is not perfect. Perfect code does not exist; continuous improvement
does. Do not block a change because it is not the way you would have written it. If it
improves the codebase, follows the project's conventions and passes the governance gates,
approve it.

Governance is the one axis where "good enough" does not apply: a change that fails
`lint_language.py` or `lint_structure.py`, ships a hardcoded user-facing string, or adds a
destructive migration is not mergeable, however elegant the rest is.

## When to Use

- Before merging any pull request or change
- After finishing a feature implementation
- When another agent or model produced code you need to evaluate
- When refactoring existing code
- After any bug fix (review both the fix and its regression test)
- Before cutting a release (combine with `.claude/skills/shipping-and-launch/SKILL.md`)

## The Six-Axis Review

### 1. Correctness

Does the code do what it claims?

- Does it match the spec or task requirements?
- Are edge cases handled (`None`, empty collections, boundary values, unicode input)?
- Are error paths handled, not just the happy path?
- Do all tests pass? Do the tests actually exercise the right behavior?
- Any off-by-one errors, race conditions, or state inconsistencies?
- Async paths: does an `async` action block the event loop with synchronous I/O? Are pooled
  database connections released in worker threads?
- Queued jobs: is every payload JSON-serializable (jobs serialize to JSON)?

### 2. Readability and Simplicity

Can another engineer (or agent) understand this without the author explaining it?

- Are names descriptive, English, and consistent with the project glossary? (No `temp`,
  `data`, `result` without context; no identifiers derived from the team's language.)
- Is control flow straightforward (guard clauses, no deep nesting, no nested conditional
  expressions)?
- Is the code organized logically (related code together, clear module boundaries)?
- Any "clever" tricks that should be written plainly?
- **Could this be done in fewer lines?** A thousand lines where a hundred would do is a
  failure.
- **Do abstractions earn their complexity?** Do not generalize before the third use case.
- Would a comment clarify non-obvious intent? (Do not comment obvious code.)
- Any dead-code artifacts: unused variables, backwards-compatibility shims with no caller,
  commented-out blocks, `# removed` notes? Commented-out code is a build failure under
  governance, not a note for later.
- **Is a new conditional bolted onto an unrelated flow?** That is a design smell, not a nit.
  Push the logic into its own helper, state object or policy instead of tangling an existing
  path.
- **Do repeated conditionals on the same shape appear?** They signal a missing model or
  dispatcher. A "temporary" branch is usually permanent debt.

### 3. Architecture

Does the change fit the system's design?

- Does it follow existing patterns, or introduce a new one? If new, is it justified and
  documented (see `.claude/skills/documentation-and-adrs/SKILL.md`)?
- Does it respect the three tiers: **core engine** -> **business modules** -> **capability
  plugins**? The core never swells to host a feature.
- Is there duplication that should be shared?
- Do dependencies flow in the right direction (no circular imports)?
- Is the abstraction level right (not over-engineered, not tightly coupled)?
- **Does this refactor reduce complexity or just relocate it?** Count the concepts a reader
  must hold to follow the change. If the "cleaner" version leaves that count unchanged, it is
  not cleaner. Prefer the restructuring that makes whole branches, modes or layers disappear
  over one that re-centralizes the same logic. Prefer deleting an abstraction to polishing it.
- **Is feature-specific logic leaking into a shared or general-purpose module?** Keep logic
  in its owning layer, reuse the canonical helper instead of a near-duplicate, and do not
  normalize architectural drift.
- **Are type boundaries explicit?** Question gratuitous `Any`, `object`, blanket `Optional`,
  `cast()` calls and silent fallbacks that paper over an unclear invariant. Making the
  boundary explicit often simplifies the surrounding control flow.

### 4. Security

For depth, follow `.claude/skills/security-and-hardening/SKILL.md` and
`.claude/references/security-checklist.md`. Does the change introduce a vulnerability?

- Is user input validated at the boundary — through a `FormRequest` in
  `app/Http/Requests` rather than ad-hoc checks in the controller?
- Are secrets kept out of code, logs and version control?
- Is authorization enforced where needed (Gate abilities, policies generated with
  `make:policy`, `FormRequest.authorize()`)?
- Are queries parameterized through the ORM or query builder (never string concatenation or
  f-strings into SQL)?
- Is output escaped? Forge autoescaping stays on; any raw-output filter needs a justification.
- Does every state-changing form (`POST`, `PUT`, `PATCH`, `DELETE`) carry `@csrf`? Does every
  public form carry `@honeypot` or `@antispam`?
- Are tokens, signatures and other secrets compared with `hmac.compare_digest`, never `==`?
- Personal data: is collection minimal, purpose-bound and protected (LGPD/GDPR privacy by
  design)? Is personal data kept out of logs?
- Are new dependencies from trusted sources, maintained, and free of known vulnerabilities?
- Is data from external sources (APIs, logs, uploaded files, user content, config) treated as
  untrusted and validated before it reaches logic or rendering?

### 5. Performance

For profiling and optimization, follow `.claude/skills/performance-optimization/SKILL.md`
and `.claude/references/performance-checklist.md`.

- Any N+1 query patterns? Relations loaded in a loop instead of eager-loaded with `with_()`?
- Any unbounded loops or unconstrained fetches (`all()` on a table that grows)?
- Any list endpoint without pagination (`paginate()` on the query builder)?
- Any slow synchronous work in a request that belongs in a queued job?
- Any blocking call inside an `async` action?
- Any large objects built in hot paths, or repeated work that `Cache` should hold?
- Frontend: oversized static assets, render-blocking scripts, layout shift?

### 6. Craft Governance

These checks are binary. Each failure is at least **Required**; the ones marked *(blocks)*
are **Critical**.

**Layer caps** (enforced by `python .claude/rules/lint_structure.py`):

| Layer | Cap |
| --- | --- |
| Controller | 150 lines per file, 15 lines per action |
| Domain service | 300 lines per file |
| Repository | 250 lines per file |
| Any function or method | 25 lines, cyclomatic complexity <= 6 |

A file over its cap is split in the same change — a god controller becomes focused
sub-controllers. The threshold is never raised to fit the code.

**Layer purity:**

- No SQL, joins or direct database calls in controllers or services — they go through a
  repository or the ORM (`STRUCT-D`).
- No HTML or concatenated view strings in Python — markup lives in Forge templates under
  `resources/views` (`STRUCT-E`).
- Standard create/read/update/delete is generated through the CRUD builder
  (`python dev.py make:crud`), not hand-rolled.
- Services are resolved from the container (constructor injection, `app.make(...)`, or a
  facade), never instantiated directly inside a route or controller.
- Cross-cutting algorithms (document validation, check digits, QR rendering, slug
  sanitization, payment gateways) live in `app/plugins/`, not copied into a module.
- Frontend assets are vanilla or vendored `.js`/`.css` only — zero TypeScript, zero Node
  build pipeline, zero npm (`STRUCT-F`).

**Robustness and typing:**

- Type hints on every parameter and return (`STRUCT-H`).
- Google-style docstrings on every public class and function (`STRUCT-I`).
- No bare `except:` or `except Exception:` (`STRUCT-G`); error logs carry the entity id, the
  user or tenant id, and the original exception message.
- Money is integer minor units plus an ISO-4217 code; timestamps are UTC-aware.

**Language and i18n** (enforced by `python .claude/rules/lint_language.py`):

- Every identifier, comment, docstring, log line, commit message and committed document is
  English.
- *(blocks)* No hardcoded user-facing text in Python, templates, e-mails, migrations, seeds or
  tests. Templates call `{{ __('order.checkout.action.confirm') }}`; Python resolves keys through
  the translation service.
- Every new key has **three rows** in the `translations` table — `en` (source), `pt-BR`
  (default), `es` — written by a seeder or migration in the same change. A key with fewer
  rows is unfinished.
- Keys are lowercase `dot.case` and describe meaning, not appearance.
- Errors raised to the transport layer are typed and carry `code` (UPPER_SNAKE) plus
  `message_key`; no rendered sentence travels through the domain.
- New domain terms are added to the glossary in the same change (Brazilian terms map to the
  canonical English names — for example, a bank slip is `bank_slip`).

**Release non-regression:**

- *(blocks)* Migrations are forward-only. No `migrate:fresh`, `migrate:reset`,
  `migrate:refresh`, `db:wipe` or `db:drop` anywhere — code, scripts, docs, CI or tests.
- *(blocks)* Business entities are soft-deleted (`SoftDeletes`, `deleted_at`, `is_active`);
  no physical `DELETE` or `TRUNCATE` on business tables.
- A column rename follows expand -> migrate -> contract across releases, never an in-place
  rename.
- `CHANGELOG.md` has an entry under `## [Unreleased]` in the right Keep a Changelog category
  (`Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`).
- If the change cuts a release: `pyproject.toml` version equals `engine/__init__.py`
  `__version__`, `__release__` is exactly the previous `rNNNNN` + 1, and the tag is
  `vX.Y.Z-rNNNNN`.
- Public facades (`Auth`, `DB`, `Route`, `View`, `Cache`, `Firewall`, `AntiSpam`, ...) keep
  backward-compatible signatures.
- Commit messages follow Conventional Commits in English imperative.

**Gates — all four must be green, with output shown, not claimed:**

```bash
python -m pytest tests
ruff check engine
python .claude/rules/lint_language.py
python .claude/rules/lint_structure.py
```

A gate is never weakened, narrowed or given an exemption to make a change pass. The fix is
the code.

## Structural Remedies

When you flag a structural problem, propose the move, not just the problem. "This is
complex" leaves the author guessing. Name a restructuring:

- **Replace a chain of conditionals** with a typed model (an `Enum`, a dataclass) or an
  explicit dispatcher.
- **Collapse duplicate branches** into one clearer flow.
- **Separate orchestration from business logic** — the controller translates HTTP, the
  service decides, the repository queries.
- **Move feature-specific logic** out of a shared module into the module or plugin that owns
  the concept.
- **Reuse the canonical helper** instead of a bespoke near-duplicate.
- **Make a type boundary explicit** so downstream branching disappears.
- **Delete a pass-through wrapper** that adds indirection without clarifying the API.
- **Extract a helper or split a file** that is at or over its layer cap.
- **Move SQL into a repository, markup into a Forge template, copy into a translation key.**

Prefer the remedy that removes moving pieces over one that spreads the same complexity
around.

## Change Sizing

Small, focused changes are easier to review, faster to merge and safer to deploy:

```text
~100 lines changed   -> Good. Reviewable in one sitting.
~300 lines changed   -> Acceptable if it is one logical change.
~1000 lines changed  -> Too large. Split it.
```

**Watch file size, not just diff size.** A small diff can push a file past its layer cap. In
Craft the caps are hard: a controller past 150 lines or a service past 300 fails the gate.
When a change grows a file close to its cap, extract helpers, sub-controllers or services
*first*, then add. Decompose, then add.

**What counts as one change:** a self-contained modification that addresses one thing,
includes its tests, its translation rows and its changelog entry, and leaves the system
working. One part of a feature, not the whole feature.

**Splitting strategies when a change is too large:**

| Strategy | How | When |
| --- | --- | --- |
| **Stack** | Submit a small change, start the next one on top of it | Sequential dependencies |
| **By file group** | Separate changes for groups needing different reviewers | Cross-cutting concerns |
| **Horizontal** | Shared code, migration or plugin first, consumers next | Layered architecture |
| **Vertical** | Smaller end-to-end slices (route -> controller -> service -> template) | Feature work |

**When large changes are acceptable:** whole-file deletions and automated refactors (a
scripted rename, a key extraction) where the reviewer verifies intent, not every line.

**Separate refactoring from feature work.** A change that refactors existing code and adds
behavior is two changes. Tiny cleanups (a rename) may ride along at the reviewer's discretion.

## Change Descriptions

Every change needs a description that stands on its own in version-control history.

**First line:** Conventional Commits, English, imperative, standalone —
`feat(billing): generate bank slip barcode on invoice issue`, not
`generating barcode`. Someone searching history must understand it without the diff.

**Body:** what changes and why. Context, decisions and reasoning the code cannot show. Link
issues, benchmark results or ADRs. Acknowledge the approach's shortcomings when they exist.

**Anti-patterns:** "fix bug", "fix build", "add patch", "move code from A to B", "phase 1",
"add helper functions", or any message not in English.

## Review Process

### Step 1: Understand the Context

Before reading code, understand the intent:

```text
- What is this change trying to accomplish?
- What spec or task does it implement?
- What behavior is expected to change?
- Which layers does it touch (route, controller, request, service, repository,
  model, migration, template, plugin)?
```

### Step 2: Review the Tests First

Tests reveal intent and coverage:

```text
- Do pytest tests exist for the change?
- Do they test behavior, not implementation details?
- Are edge cases and error paths covered?
- Are test names descriptive English (test_rejects_duplicate_payment_capture)?
- Do tests assert on translation keys or codes rather than rendered copy?
- Would the tests catch a regression if the code changed?
```

### Step 3: Review the Implementation

Walk every changed file through the six axes:

```text
For each changed file:
1. Correctness: does it do what the tests say it should?
2. Readability: can I understand it without help?
3. Architecture: does it fit the tiers and the layer boundaries?
4. Security: any vulnerability, missing @csrf, unsafe comparison?
5. Performance: any N+1, unbounded fetch, blocking call?
6. Governance: caps, purity, container, i18n rows, changelog, migrations?
```

### Step 4: Categorize Findings

Label every finding so the author knows what is required and what is optional:

| Prefix | Meaning | Author action |
| --- | --- | --- |
| **Critical:** | Blocks merge | Security vulnerability, data loss, destructive migration, hardcoded user-facing copy, broken functionality, failing gate |
| *(no prefix)* / **Required:** | Must change | Address before merge |
| **Optional:** / **Consider:** | Suggestion | Worth weighing, not required |
| **Nit:** | Minor | Author may ignore — formatting, style preference |
| **FYI** | Information | No action — context for the future |

This keeps authors from treating every comment as mandatory and burning time on suggestions.

**Lead with what matters.** Order findings by leverage: correctness, security and governance
blockers first, then structural regressions and missed simplifications, then everything else.
Do not bury a real issue under cosmetic nits. If there is one structural problem and ten nits,
the structural problem *is* the review.

### Step 5: Verify the Verification

Check the author's verification story:

```text
- Which tests ran? Was the output of python -m pytest tests shown?
- Did ruff check engine, lint_language.py and lint_structure.py exit 0?
- Were migrations applied forward with python dev.py migrate and checked
  with python dev.py migrate:status?
- Was the change exercised manually (python dev.py serve) where it has UI?
- Screenshots or before/after comparison for UI changes?
- Is the CHANGELOG.md entry present?
```

## Multi-Model Review Pattern

Different reviewers catch different things:

```text
Model A writes the code
    |
    v
Model B reviews for correctness, architecture and governance
    |
    v
Model A addresses the feedback
    |
    v
A human makes the final call
```

Models share blind spots with themselves; a second perspective catches what the author's
context hides.

**Example prompt for a review agent (such as `.claude/agents/code-reviewer.md`):**

```text
Review this change for correctness, security and Craft governance.
The spec says [X]. The change should [Y].
Check layer caps, SQL/HTML leakage, container resolution, translation
keys in en, pt-BR and es, the CHANGELOG entry and forward-only migrations.
Label every finding Critical, Required, Optional or Nit.
```

## Dead Code Hygiene

After any refactor or implementation change, look for orphans:

1. Identify code that is now unreachable or unused
2. List it explicitly
3. **Ask before deleting:** "Should I remove these now-unused elements: [list]?"

Dead code confuses future readers and agents, but silent deletion of something you are unsure
about is worse. When in doubt, ask.

```text
DEAD CODE IDENTIFIED:
- format_legacy_date() in app/Services/ReportService.py — replaced by format_date()
- resources/views/orders/legacy_card.html — replaced by orders/card.html
- LEGACY_API_URL in config/services.py — no remaining references
- translation keys order.legacy.* — no template or code references them
-> Safe to remove these?
```

Removing an unused translation key is a data change: do it through a forward migration or
seeder, not by editing rows by hand.

## Review Speed

Slow reviews block whole teams. Context-switching to review costs less than the waiting it
imposes on others.

- **Respond within one business day** — the maximum, not the target
- **Ideal cadence:** respond soon after the request arrives, unless deep in focused work. A
  typical change should complete several review rounds in one day
- **Prefer fast individual responses** over a fast final approval; quick feedback reduces
  frustration even across several rounds
- **Large changes:** ask the author to split them instead of reviewing one massive changeset

## Handling Disagreements

Resolve review disputes with this hierarchy:

1. **Technical facts and data** override opinions and preferences
2. **Project governance** (`.claude/rules/`) is the authority on layer, language, i18n and
   release rules — it is not up for negotiation in a review thread
3. **Style guides** (ruff configuration, PEP 8) are the authority on style
4. **Software design** is judged on engineering principles, not personal taste
5. **Codebase consistency** is acceptable when it does not degrade overall health — and never
   when the consistency is with a defect (legacy non-English names, hardcoded copy)

**Do not accept "I'll clean it up later."** Deferred cleanup rarely happens. Require it before
merge unless it is a genuine emergency. If surrounding issues cannot be fixed in this change,
require an issue filed and assigned.

## Honesty in Review

Whether the code came from you, another agent or a human:

- **Do not rubber-stamp.** "LGTM" with no evidence of review helps no one.
- **Do not soften real issues.** Calling a production bug "a minor concern" is dishonest.
- **Quantify problems.** "This N+1 adds one query per order row — 51 queries for the default
  page of 50" beats "this could be slow."
- **Push back on approaches with clear problems.** Sycophancy is a review failure mode. Say so
  directly and propose an alternative.
- **Accept override gracefully** on judgment calls where the author has the fuller context —
  but not on governance gates, which are not judgment calls. Comment on code, not people.

## Dependency Discipline

Dependency review is part of code review.

**Before adding any dependency:**

1. Does the Python standard library or the engine already solve this? (Often it does — the
   engine ships the ORM, validation, queues, cache, mail, storage, media and security layers.)
2. How large is it, and what does it pull in transitively?
3. Is it actively maintained (recent releases, responsive issue tracker)?
4. Does it have known vulnerabilities (`pip-audit` or your advisory source)?
5. Is the license compatible with the project?
6. Frontend: can it be vendored as a static `.js`/`.css` file? Anything that needs npm or a
   Node build step is rejected outright.

**Rule:** prefer the standard library and existing engine utilities over new dependencies.
Every dependency is a liability. A new cross-cutting capability is a plugin in
`app/plugins/`, removable without breaking the core.

**Upgrading an existing dependency** is a code change like any other, and the riskiest ones are
merged in bulk as "bump deps". Review them with the same discipline:

1. **Read the changelog, not just the version number.** Semver is a promise a maintainer may
   break — a patch release can change behavior. For a major bump, read the migration notes and
   find what breaks.
2. **One dependency per change.** Upgrade and merge individually, or in small related groups.
   When a bulk bump breaks the suite you have lost which package did it; a single-package
   change makes the cause obvious and the revert clean.
3. **Let the tests decide.** The upgrade is verified by a green `python -m pytest tests` before
   *and* after, not by "it installed". If coverage around the dependency's behavior is thin,
   that gap is the real finding — add a test first.
4. **Mind the transitive graph.** Most installed packages were never chosen directly. Review the
   resolved lock or pinned-requirements diff, not just `pyproject.toml`; one direct bump can
   drag in dozens of indirect changes.
5. **Keep the pins honest.** Commit the lock or pinned file, review its diff, never hand-edit a
   generated lock.
6. **Record it.** A dependency change gets its own `CHANGELOG.md` entry (`Changed` or
   `Security`).

For triaging vulnerability advisories and supply-chain risk (typosquatting, compromised
maintainers), follow `.claude/skills/security-and-hardening/SKILL.md` — this section covers
the upgrade *workflow*, that skill gives the security verdict.

## The Review Checklist

```markdown
## Review: [change title]

### Context
- [ ] I understand what this change does and why

### Correctness
- [ ] Matches the spec or task requirements
- [ ] Edge cases handled
- [ ] Error paths handled
- [ ] Tests cover the change adequately

### Readability
- [ ] Names are clear, English and consistent with the glossary
- [ ] Logic is straightforward (guard clauses, no deep nesting)
- [ ] No unnecessary complexity, no commented-out code

### Architecture
- [ ] Follows existing patterns and the core -> modules -> plugins tiers
- [ ] No unnecessary coupling or dependencies
- [ ] Appropriate abstraction level
- [ ] Refactors reduce complexity rather than relocate it
- [ ] No feature logic in shared modules

### Security
- [ ] No secrets in code or logs
- [ ] Input validated at the boundary (FormRequest)
- [ ] No injection: queries parameterized, Forge autoescaping on
- [ ] Authorization checked (Gate / policy)
- [ ] @csrf on state-changing forms; @honeypot or @antispam on public forms
- [ ] Secrets compared with hmac.compare_digest
- [ ] Personal data minimized and protected (LGPD/GDPR)
- [ ] External data treated as untrusted

### Performance
- [ ] No N+1 patterns (relations eager-loaded)
- [ ] No unbounded operations
- [ ] Pagination on list endpoints
- [ ] No blocking calls in async actions

### Craft Governance
- [ ] Layer caps respected (controller 150/15, service 300, repository 250, function 25, complexity <= 6)
- [ ] No SQL in controllers or services; no HTML in Python
- [ ] Plain CRUD via make:crud; services resolved from the container
- [ ] Cross-cutting logic in app/plugins/
- [ ] Type hints and Google docstrings on every public signature; no bare or broad except
- [ ] No hardcoded user-facing text; every new key has en, pt-BR and es rows
- [ ] Errors carry code + message_key
- [ ] Migrations forward-only; soft deletes for business entities
- [ ] CHANGELOG.md entry under ## [Unreleased]
- [ ] Conventional Commit message in English

### Verification
- [ ] python -m pytest tests passes
- [ ] ruff check engine passes
- [ ] python .claude/rules/lint_language.py exits 0
- [ ] python .claude/rules/lint_structure.py exits 0
- [ ] Manual verification done (if applicable)

### Verdict
- [ ] **Approve** — ready to merge
- [ ] **Request changes** — issues must be addressed
```

## See Also

- Security review depth: `.claude/references/security-checklist.md`
- Performance review checks: `.claude/references/performance-checklist.md`
- What "done" means for a change: `.claude/references/definition-of-done.md`
- Simplifying what the review flags: `.claude/skills/code-simplification/SKILL.md`
- The reviewer persona: `.claude/agents/code-reviewer.md`, invoked through `/review-change`

## Common Rationalizations

| Rationalization | Reality |
| --- | --- |
| "It works, that's good enough" | Working code that is unreadable, insecure or architecturally wrong creates compounding debt. |
| "I wrote it, so I know it's correct" | Authors are blind to their own assumptions. Every change benefits from another set of eyes. |
| "We'll clean it up later" | Later never comes. The review is the quality gate — require cleanup before merge. |
| "AI-generated code is probably fine" | Generated code needs more scrutiny, not less. It is confident and plausible even when wrong. |
| "The tests pass, so it's good" | Tests are necessary, not sufficient. They miss architecture, security, readability and governance problems. |
| "The refactor makes it cleaner" | Relocating complexity is not reducing it. If the reader holds the same number of concepts, look for the version where branches disappear. |
| "It's only a small addition to this file" | Small diffs push files past their layer cap and bolt branches onto unrelated flows. Judge the resulting structure. |
| "The string is only shown to admins" | Admins are users. Hardcoded copy is hardcoded copy — it needs a key with three rows. |
| "I'll add the pt-BR and es rows in a follow-up" | A key with fewer than three rows is unfinished. The rows ship in the same change. |
| "One raw query in the service is faster to write" | SQL in a service fails `STRUCT-D` and bypasses the repository's guarantees. Move it. |
| "The controller is 160 lines, close enough" | The cap is 150. Split it into focused sub-controllers now. |
| "The changelog entry can go in at release time" | Every change adds its entry under `## [Unreleased]` in the same commit. |
| "It's just a version bump" | A bump is a behavior change you did not write. Read the changelog; semver does not guarantee no breakage. |
| "I'll upgrade everything in one change to save time" | A bulk bump that breaks the suite hides which package did it. One dependency per change. |

## Red Flags

- Changes merged without any review
- A review that only checks whether tests pass
- "LGTM" with no evidence of actual review
- Security-sensitive changes without a security-focused review
- Large changes that are "too big to review properly" (split them)
- Bug fixes with no regression test
- Findings without severity labels
- Accepting "I'll fix it later"
- A refactor that moves code without reducing the concepts a reader must hold
- A change that grows a file toward or past its layer cap instead of decomposing it
- New conditionals scattered into unrelated code paths (a missing abstraction)
- A bespoke helper duplicating a canonical one, or feature logic placed in a shared module
- SQL in a controller or service; HTML strings in Python
- A service instantiated directly in a controller instead of resolved from the container
- A literal user-facing string in a template, exception, response payload or test
- A translation key with fewer than three locale rows
- `migrate:fresh`, `migrate:reset`, `migrate:refresh`, `db:wipe` or `db:drop` anywhere, or a
  physical delete on a business table
- No `CHANGELOG.md` entry
- A gate "fixed" by adding an exemption, raising a threshold or disabling a rule
- A bulk "bump dependencies" change with no changelog review and no per-package isolation
- A generated lock or pinned requirements file that is hand-edited, uncommitted or merged
  without reviewing its diff

## Verification

After the review is complete:

- [ ] All Critical issues are resolved
- [ ] All Required changes are resolved, or explicitly deferred with a justification and a
      filed issue (governance failures cannot be deferred)
- [ ] `python -m pytest tests` passes
- [ ] `ruff check engine` passes
- [ ] `python .claude/rules/lint_language.py` exits 0
- [ ] `python .claude/rules/lint_structure.py` exits 0
- [ ] Every new translation key has `en`, `pt-BR` and `es` rows
- [ ] `CHANGELOG.md` has the entry under `## [Unreleased]`
- [ ] The verification story is documented (what changed, how it was verified)
- [ ] Dependency upgrades were read against their changelogs, isolated per package, verified by
      a green suite, with the pinned-file diff reviewed

**Presumptive blockers:** surface each of these and propose the simpler design; escalate to
Required when the change actively makes structure worse: a refactor that relocates complexity
instead of reducing it; a change that pushes a file toward its layer cap with no
decomposition; feature logic added to a shared module; a near-duplicate of a canonical helper;
a silent fallback hiding an unclear invariant. Governance gate failures are not presumptive —
they are Required or Critical by definition.
