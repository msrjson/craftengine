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

### L3. Two language gates disagree about `engine/`

**Measured 2026-09-25:** `engine/cli/app.py` alone holds 84 violations under
the global gate (78 LANG-C console sentences, 6 LANG-A). New engine code this
session follows the pattern that passes both gates: developer messages live in
`engine/support/diagnostics.py` (code -> template) and exceptions carry a code
and params. Migrating the console output to the same catalog is the concrete
plan if the owner chooses "migrate".


The global hook reproves any `engine/` file it touches for pre-existing
violations, while `data/language-standard.toml` deliberately scopes `engine/`
out with a measured backlog of 252 violations. Every edit to `engine/` in the
4.0.0 work was flagged by the hook for violations it did not introduce.
**Owner decision required:** exempt engineer-facing CLI output (precedent: the
toml already exempts `tools/lint_language.py`), migrate the 252, or make the
hook read the project's toml.

### L4. `data/` is not identical to a generated project - done 2026-09-25

Documented in `data/README.md` ("This repository is not a generated project"):
which extra tables this tree creates and where a generated project gets them.

### L5. The engine writes to tables a generated project does not have - done 2026-09-25

`craft new` now ships forward-only migrations for the security tables and
`scheduler_runs` (2aec34b); `claim_window` reports a missing table; `craft
doctor` lists missing engine tables in projects generated earlier.

### L6. Agent-resilience audit: what is left

The 2026-09-25 audit of `engine/` ranked 20 places where a plausible agent
mistake failed silently or late. Fixed this session: attribute assignment not
saved, mass-assignment drops silent, password stored in plaintext on update,
middleware parameters untyped (`throttle:10`, `auth:api`), role checks denying
everyone without the mixin, FormRequest not injected, `make:crud`/`make:admin`
printing wrong URLs and a nonexistent command, actions returning None, unknown
Forge directives and undefined variables, facade/container/config/identity
errors without the cause, table-name inference, missing translation keys
untraced, template helpers hiding misconfiguration, and `craft doctor`.
Still open:
- **Validator messages are English f-strings** (`engine/validation/validator.py`
  138, 179-265), so a generated form's field errors are not translated.
- **Validation rules without their argument pass silently:** `regex`, `min`,
  `max`, `max_file_size` with no value (`engine/validation/validator.py`
  244, 420, 465, 469); an unknown rule raises but suggests nothing.
- **`FormRequest.data()` swallows every exception** and validates `{}`, which
  produces misleading "required" errors (`engine/validation/form_request.py`).
- **Translation lookups query per key.** One `SELECT` per string per locale
  tried; the standard asks for a cached bundle per locale.
- **Relations read as properties:** `post.user.name` reaches a bound method
  and fails with a generic `AttributeError`; no hint that relations are
  methods.

### L7. A 500 in production shows the exception message

`ExceptionHandler.to_payload` sends `str(exception)` as `message` for every
status, debug or not (`engine/exceptions/handler.py`, `to_payload`). A
database error's text, or a `MisconfigurationError` naming internal classes,
reaches the visitor. Traces are already debug-only; the message should be too
for 5xx. Security-relevant; not changed in this session because several tests
and error views read that field.

### L8. Flaky concurrency test

`tests/test_connection_concurrency.py::TestInMemorySqliteSharesOneSession::
test_threads_share_the_session_and_therefore_the_data` failed once with
`IndexError: tuple index out of range` in about 20 runs on 2026-09-25, on a
loaded machine, before and independent of that day's changes.

---

## Also open

- **Third-party comparison document:** `data/documentation/market_evaluation.md`
  is a comparison with other frameworks in its entirety, against the project
  rule not to cite them. Owner to decide whether it stays.
- **Site DNS:** on 2026-09-24 `craftengine.org` did not resolve from the
  development machine, while other domains did. Confirm the domain's
  nameservers at the registrar.
- **Site blocked by corporate proxies:** the current registration dates from
  2026-09-18 (GoDaddy, Cloudflare DNS), so web filters classify
  `craftengine.org` as a Newly Registered Domain and block it, usually for the
  first 30 days (until about 2026-10-18). The earlier owners (2017-2025) only
  parked it, and the archive shows no abusive content. To shorten the wait,
  submit the domain as Software/Technology to the main categorizers (Palo Alto,
  Fortinet, Zscaler, Cisco Talos, Broadcom, Trellix).
  **Done when:** the site opens from a corporate network.

---

## 🤖 Done automatically

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
