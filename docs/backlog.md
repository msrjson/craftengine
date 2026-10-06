# Backlog - CraftEngine (history)

**Updated:** 2026-10-03T23:05:00Z

**Open work no longer lives here.** It is a queue of task files under
[`backlog/`](../backlog/README.md), one file per item, each named and stamped with
its UTC creation time and carrying its own History. Agents pick from
`backlog/bugfix/` first, then `backlog/pending/`.

This file keeps the record of items closed before the queue existed and the
`Done automatically` log. The earlier backlog in `.agents/docs/backlog.md`
predates 4.0.0 and stays as history.

## Revision history

- 2026-10-03T23:05:00Z - the queue became mandatory: rules in
  `.claude/rules/BACKLOG_QUEUE_STANDARD.md`, gate `.claude/rules/lint_backlog.py`
  wired as a Claude hook and a Git `pre-commit`.
- 2026-10-03T22:31:30Z - open items migrated to `backlog/` (L3, L6 leftover, L8, the P2 CI
  confirmation, the owner questions, the site items); this file became history.

---

## Priority (closed)

### P1. Generated code breaks the project's own language rules - done 2026-09-25

Generated views and controllers use keys; `make:auth`/`make:admin` seed `en`,
`pt-BR` and `es` rows through forward-only migrations; `tests/test_generated_copy.py`
and the onboarding journey prove it. Validation messages still come from the
engine's English `Validator` defaults - see L6.


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

- **Measured 2026-09-25:** 18 strings in `auth_scaffolder.py` stubs, 91 across
  the 15 `admin_templates` files (CRUD Builder index 28, groups 32, roles 9,
  result 9, permissions 4, controllers 9; two JS strings in the CRUD Builder,
  one of them concatenated). No test asserts any of this copy.
- **Prerequisites found:** Forge registers only `__()` (`engine/view/forge.py:380`);
  `t()`/`trans()` are in the gate config but raise `UndefinedError` in a
  template. A generated project has no `locales` table, no unique
  `(key, locale)` index, no translation seeder, and defaults to `en` with a
  stray `pt` (the `pt` part is fixed, see Done automatically). A missing key
  returns the raw key with no log (`engine/support/translation.py:121`). The
  gate never sees the stubs (`*.stub` matches no glob, `engine/` is not a
  root), a generated project receives no gate or config, and the template
  rule needs 8+ characters on one line, so a stricter test than the gate is
  needed to prove the conversion.
- **Unrendered copy:** `heading`/`subheading` in the admin controllers never
  reach the generated layout, and `?error=conditions` is never shown.

### P2. PostgreSQL is not tested in CI - done locally 2026-09-25, CI unconfirmed

The suite no longer deletes, truncates or drops (3a7c62f); `tests/test_fixture_safety.py`
enforces it and `conftest.py` runs PostgreSQL in a fresh `craft_test_*` database
per session. Verified in the container against PostgreSQL 18, twice in a row:
`1758 passed, 4 skipped` (the skips are refusal paths for other drivers); SQLite
`1696 passed, 66 skipped`. **Moved to the queue:** `backlog/pending/p1-20261003-223120-confirm-postgres-ci-and-auto-release.md`. **Still to confirm:** the GitHub `test-postgres` job and
the automatic `release` job on the next push - not pushed from this session.
Residue by design: one `craft_test_*` database per session and one
`craft_rls_probe_*` role (random password, LOGIN removed at test end) on a
development server; nothing is dropped. The scanner reads text only: engine APIs
that delete rows the test created (`BelongsToMany.detach()`, the queue removing a
finished job) are engine behaviour, not test cleanup - see the owner question below.


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
- **Measured 2026-09-25:** about 190 destructive statements across 30 test
  files (largest: `test_security_firewall_honeypot.py` 30, `test_postgres_integration.py` 20,
  `test_framework.py` 14, `test_tenancy_rls.py` 13, `test_tenancy_wiring.py` 12,
  `test_rbac.py` 9). The conftest fixtures `two_tenants` and
  `unprivileged_postgres_role` delete/drop and are used by no test.
- **Chosen approach:** a fresh, uniquely named database per session
  (`craft_test_<utc>_<uuid8>_<worker>`), created with `CREATE DATABASE` before
  `import engine` and never dropped; `DB_DATABASE` becomes only the maintenance
  database to connect through. Tests stop deleting: unique emails, slugs, IPs,
  queue and task names per test; scratch tables get unique names; whole-table
  counts are scoped to the test's own rows. Tests of the delete APIs themselves
  (`QueryBuilder.delete`/`truncate`, `Model.delete`, `force_delete`) move to a
  private in-memory SQLite manager, as `test_query_builder.py` already does.
- **Rejected:** per-test transaction rollback. Connections are per thread, the
  kernel serves requests through `run_in_threadpool`, and `Connection` has no
  nested savepoints (`engine/orm/connection.py:927-938`), so every TestClient
  test would see none of the fixture rows and commit its own writes.
- **CI gap found on the way:** `config/database.py:49` defaults `sslmode` to
  `require` and the `postgres:18` service has no TLS; the job needs
  `DB_SSLMODE: disable` or it fails to connect even after the guard goes.

### P3. Decide the engine's scope: "bare" or "Slim" - decided 2026-09-25: slim

Recorded in `docs/adr/0002-slim-engine-optional-extras.md`, with every
candidate subsystem sized. Next (queued as `backlog/pending/p2-20261003-223122-slim-engine-step-0-dependency-hygiene.md`): step 0 of its plan (dependency hygiene and
lazy imports, no API break), then one subsystem per commit with a deprecation
release before each removal.


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

## Lower-risk items (closed)

### L1. `make:admin` is the most fragile generator - done 2026-09-25

`TestGeneratedAdminWriteActions` in the onboarding journey performs every
write the panel exposes (grant a permission to a role, create a group, add a
member, grant a group a role, grant a conditional permission, refuse invalid
conditions with the message shown), checks each in the database, proves a
member inherits the group's role, and proves an account without the role gets
403 and changes nothing and a post without a CSRF token is refused.


It inherited demo code (`PanelPage`, the CRUD Builder screen). Only the happy
path is tested: signing in and loading each screen. Granting a permission to a
role, creating a group, adding members and granting group roles or conditional
permissions are not exercised.
**Done when:** the journey test covers every write action the panel exposes,
including a refused one for an account without the role.

### L2. Thin coverage beyond the happy path - done 2026-09-25

`TestGeneratedAuthenticationEdges` covers CSRF rejection, validation failure,
duplicate registration and generator re-runs end to end; it found the missing
`unique:users,email` rule (500 on a duplicate) and errors lost without a
`Referer`. `make:crud --force` re-runs stay covered by `test_crud_builder.py`.


Coverage is 76%, with one journey test per generator. Error cases and edges -
validation failures, duplicate registration, CSRF rejection on generated forms,
generator re-runs with `--force` - are not covered end to end.

### L4. `data/` is not identical to a generated project - done 2026-09-25

Documented in `data/README.md` ("This repository is not a generated project"):
which extra tables this tree creates and where a generated project gets them.

### L5. The engine writes to tables a generated project does not have - done 2026-09-25

`craft new` now ships forward-only migrations for the security tables and
`scheduler_runs` (2aec34b); `claim_window` reports a missing table; `craft
doctor` lists missing engine tables in projects generated earlier.

### L7. A 500 in production shows the exception message - done 2026-09-25

Without `APP_DEBUG`, a 5xx answers with the generic title; the `code` of a
coded exception is still exposed. The test that asserted the leak now asserts
its absence.

## 🤖 Done automatically

**2026-10-06 (extension kinds, owner order):**

- Added the `connector` extension kind (`make:connector`, `app/connectors`) and made
  `make:module` generate a model and a migration, so a module is born with its schema.
  Tests: generated one-of-each lifecycle, connector webhook under `api/*` (CSRF-exempt)
  and its removal on deactivation, connector-to-module dependency blocking deactivation,
  uninstall keeping rows, a second install refused. Framework container: all green.
  Published as v4.6.0-r00026; the demo moved to it and its two slices closed
  (`backlog/done/*demo-*`): five CLI-generated extensions and 27 matrix tests, 55 passed
  on SQLite and on PostgreSQL.

**2026-10-05 to 2026-10-06 (extension model, CRM demo):**

- Found by the CRM demo (`msrjson/craftengine-demo`), which installs the framework
  from its release like any project; all fixed in 4.4.1 with regression tests: the
  package lacked the auth and shared templates; an extension added after boot never
  served; `make auth` / `make admin` left half a scaffold on failure; `make admin`
  never created the `admin` role it tells you to assign; `regex:` split its pattern on
  commas; `redirect.back()` was an open redirect; route collisions were decided by load
  order; CSRF refusals rendered hardcoded English.
- Found by the demo running on its real `APP_URL` after 4.4.1: `redirect.back()`
  trusted only the `Host` header, so behind a reverse proxy a form with errors went to
  `/`; fixed under `[Unreleased]` (accepts the `APP_URL` host too).
- Added the pre-release gate `.claude/scripts/rehearse-demo.sh` (the demo's whole suite
  against the candidate, on SQLite and PostgreSQL) and made it a step of the release
  procedure in `data/CONTRIBUTING.md`.
- Moved the bundled `plugins/audit-log` example out of the framework into the demo,
  and the site repository from `website/` to `data-website/`.
- The demo was not reachable (`/login` 404): it ran engine 4.4.0, whose package lacked
  the auth templates. Pinned it to the published v4.4.1, generated sign-in and admin,
  and created a local admin account; 28 demo tests pass in its container.

**2026-10-03:**

- Found while migrating to the queue: two L6 leftovers were already fixed in
  the code - rules without their argument now raise
  (`engine/validation/validator.py:86`, `REQUIRED_ARGUMENTS`), and
  `FormRequest.data()` catches only `ValueError`/`TypeError` and logs
  (`engine/validation/form_request.py:80`). They were not queued.
- Found while migrating: the working tree holds uncommitted changes that undo
  v4.2.0-r00020, including the translation bundle cache; queued as an owner
  decision instead of a task.

**2026-09-25:**

- Found by the new Forge check: the login and registration views `make:auth`
  generates used `@for`/`@endfor`, which Forge does not compile, so failed
  sign-ins showed the directive as text.
- Found by the new documented-commands test: `make:admin` printed
  `role:assign`, a command that does not exist.
- Found while fixing attribute assignment: `AuthenticatableMixin` hashed
  passwords only on insert, so every update path stored plaintext.
- Found while writing the doctor check: the sign-in form `make:auth`
  generates runs honeypot and anti-spam against tables no generated project
  had.

- Locale drift closed (aa84d45): `pt` collapsed into `pt-BR` in the seeder,
  config, skeleton stubs and `SetLocale`; a request for `pt`/`pt-PT` now lands
  on `pt-BR` instead of the default locale.


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
