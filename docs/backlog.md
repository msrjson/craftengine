# Backlog - CraftEngine

Open work after **v4.0.0-r00017** (the bare engine, 2026-09-24). Ordered by
priority. Each item states the evidence and what "done" means, so whoever picks
it up - person or agent - can verify it without this conversation.

The earlier backlog lives in `.agents/docs/backlog.md` (651 lines, Portuguese,
describing the framework as "the skeleton you copy"). It predates 4.0.0 and is
not migrated here; treat it as history until someone triages it into this file.

Overall assessment of 4.0.0: a sound foundation that solves the problem it was
cut for - an agent starting a project receives nothing to reuse, so it has no
demo layout to graft work onto - but not a finished product. Item 1 matters most
for the goal of agents working without error.

---

## Priority

### P1. Generated code breaks the project's own language rules

- **Problem:** the screens written by `craft make:auth` and `craft make:admin`
  carry hardcoded English copy ("Sign in", "These credentials do not match our
  records.", field labels, button text). R2 forbids hardcoded user-facing text,
  so the language gate of a freshly generated project rejects what the framework
  just generated. For agents this is worse than it looks: the first example they
  read teaches the wrong pattern.
- **Evidence:** `data/engine/cli/auth_scaffolder.py` (`login_view_stub`,
  `register_view_stub`, `dashboard_view_stub`, `auth_controller_stub`);
  `data/engine/cli/admin_templates/resources/views/admin/**`.
- **Done when:** every user-facing string in generated views and controllers is
  a translation key; `make:auth` and `make:admin` write the `en`, `pt-BR` and
  `es` rows for their keys (migration or seeder) in the same run; a generated
  project passes `lint_language.py` for both the code and the views pass; the
  onboarding journey test asserts it.

### P2. PostgreSQL is not tested in CI

- **Problem:** the framework is developed against PostgreSQL, but the CI job
  for it exits at collection: `data/tests/conftest.py` calls `pytest.exit`
  when `CRAFT_TEST_DB=pgsql` ("Persistent database tests are disabled until
  fixtures preserve every record"). SQLite is the only real signal in CI, so
  the guarantee about the production database is whatever someone runs by hand.
  It is also why releases stopped being automatic: the `release` job needs the
  PostgreSQL job and is always skipped.
- **Evidence:** CI run 36046625355 - SQLite success, PostgreSQL failure
  (exit code 4), release skipped. v4.0.0-r00017 was tagged and released by hand.
- **Constraint:** the guard must not be bypassed. The fix is the fixtures.
- **Done when:** every fixture isolates data without physical deletion (NR-02),
  the guard is removed, the PostgreSQL job is green, and the `release` job runs
  on its own for the next release.

### P3. Decide the engine's scope: "bare" or "Slim"

- **Problem:** 4.0.0 removed the *application*, not the weight of the *engine*.
  Still shipped and registered by default: AI, agents, media, vector search,
  PQC, captcha, firewall, honeypot, anti-spam, vault, signer, queues.
  `data/pyproject.toml` still describes the framework as "batteries-included".
  That may be right, but then the comparison with a micro-framework does not
  hold. To be minimal in that sense those subsystems would have to become
  optional plugins.
- **Owner decision required.** This is a product call, not an engineering one.
- **Done when:** the scope is decided and recorded as an ADR in `docs/adr/`;
  if "minimal" is chosen, each subsystem is sized (files, tests, dependencies,
  breaking impact) before any is moved.

---

## Lower-risk items

### L1. `make:admin` is the most fragile generator

It inherited demo code (`PanelPage`, the CRUD Builder screen). Only the happy
path is tested: signing in and loading each screen. Granting a permission to a
role, creating a group, adding members and granting group roles or conditional
permissions are not exercised.
**Done when:** the journey test covers every write action the panel exposes,
including a refused one for an account without the role.

### L2. Thin coverage beyond the happy path

Coverage is 76%, with one journey test per generator. Error cases and edges -
validation failures, duplicate registration, CSRF rejection on generated forms,
generator re-runs with `--force` - are not covered end to end.

### L3. Two language gates disagree about `engine/`

The global hook reproves any `engine/` file it touches for pre-existing
violations, while `data/language-standard.toml` deliberately scopes `engine/`
out with a measured backlog of 252 violations. Every edit to `engine/` in the
4.0.0 work was flagged by the hook for violations it did not introduce.
**Owner decision required:** exempt engineer-facing CLI output (precedent: the
toml already exempts `tools/lint_language.py`), migrate the 252, or make the
hook read the project's toml.

### L4. `data/` is not identical to a generated project

`data/` still runs the demo application's migrations - users, roles,
permissions, groups, tenants, media and others - because they have already run
on existing databases and NR-02 forbids rewriting applied migrations. Someone
comparing this repository with the output of `craft new` will find tables the
generated project does not have. Document the difference in `data/README.md`,
or plan a forward-only consolidation.

---

## Also open

- **Locale drift:** `data/database/seeders/TranslationSeeder.py` seeds a `pt`
  locale alongside `pt-BR`; the governance file requires collapsing `pt` into
  `pt-BR`.
- **Third-party comparison document:** `data/documentation/market_evaluation.md`
  is a comparison with other frameworks in its entirety, against the project
  rule not to cite them. Owner to decide whether it stays.
- **Site DNS:** on 2026-09-24 `craftengine.org` did not resolve from the
  development machine, while other domains did. Confirm the domain's
  nameservers at the registrar.
