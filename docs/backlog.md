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

---

## 🤖 Done automatically

Work done during the 4.0.0 cut that was not in the original request, recorded
so it is not mistaken for unexplained change. Each was found by running the
code rather than reading it, and each is in the v4.0.0-r00017 history.

**Found by walking the generated code end to end in a project from `craft new`:**

- `craft migrate` failed with "database is locked" on file-backed SQLite. The
  console booted two applications, so migration DDL ran on one connection while
  the migrator held its transaction on another; PostgreSQL masked it but ran
  migration DDL outside the transaction. Fixed at the root in `get_app()`.
- Every generated login answered 500: the generated bootstrap registered 14
  engine providers against this repository's 23, missing AntiSpam and
  Honeypot. Both bootstraps now call one list,
  `engine/providers/engine_providers.py`.
- The generated `AuthController` called two APIs that do not exist
  (`Validator.make`, `AntiSpam.verify(..., ip_address=...)`) and flashed old
  input as an empty dict. Rewritten on the engine's API through the generated
  FormRequests.
- `role:admin` refused everyone, administrators included: the generated user
  had no `has_role`. Added `AuthorizableMixin` to the engine.
- `make:admin` linked to `/panel` and extended `layouts.panel`, both demo-only.
- `make:crud` printed its API URL but never registered the route when
  `routes/api.py` was absent.
- `craft new` generated an empty project from an installed package: templates
  were not package data, and setuptools drops hidden files such as
  `.env.example`.
- `make:auth` registered no routes when `routes/web.py` did not exist - the
  suite's only failing test when this work began.

**Found along the way:**

- The engine's RBAC console commands imported `app.Models.*` in 21 places;
  they now resolve models through `craft.auth.registry`.
- The schema tenancy strategy lived in the demo application; it moved into the
  engine as `craft.http.tenant_schema`.
- The bundled `plugins/audit-log` wrote nothing once the demo's `SystemLog`
  model was gone; it writes through the `DB` facade.
- `/ready` disclosed the database driver, pool census and cache store without
  authentication, and ran a query plus a cache write on every hit. Reduced
  payload without `HEALTH_READINESS_TOKEN`; one result shared per interval.
- `documentation/ai_agents.md` taught `Validator.make`, the non-existent call
  the generated controller made; `llms.txt` linked a missing page and described
  a removed login route.
- The origin-based CSRF test hardcoded port 9000 and passed only where a local
  `.env` set it. Every container run in this work read that `.env`, so none
  reproduced CI until the suite was run with it moved aside.
- The CI template language pass scanned demo view directories that no longer
  exist and exited 2.
- A write-ahead-log change added to fix the SQLite lock did not fix it and
  broke read/write replica handling; it was removed.

**Decided with the owner during the work:** the framework stays in the public
`msrjson/craftengine` rather than moving to a new repository (keeping stars,
links and history; older shapes remain reachable by tag), the cut is 4.0.0,
identity models are generated rather than shipped, the admin panel is a
generator, and the site carries the gear-and-ignition mark.
