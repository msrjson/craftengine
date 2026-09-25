# Changelog

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: `MAJOR.MINOR.PATCH` plus a release counter (`rNNNNN`) that
increments on every cut release, tracked in `engine/__init__.py`
(`__version__`, `__release__`) and `pyproject.toml`.

**Every change to `engine/`, `app/`, `bootstrap/`, `config/`, `database/`,
`routes/`, or `dev.py` gets an entry here, in the same change/PR that makes
it** — not batched later, not left for the release cut to reconstruct from
memory or `git log`. This applies to humans and AI agents alike: a bug fixed,
a feature added, a dependency bumped, a vulnerability closed. If it isn't
here, an agent reading this file has no way to know it happened without
re-deriving it from the diff — which is exactly the blind spot this file
exists to remove. See "Versioning and releases" in `CONTRIBUTING.md` for the
full policy (categories to use, what counts as security-relevant, how
`[Unreleased]` gets folded into a release).

## [Unreleased]

### Added

- `craft.exceptions.MisconfigurationError(code, hint, **params)`: an HTTP 500 carrying a
  stable code and the exact fix, raised where the engine used to degrade silently.
- A route action parameter annotated with a `FormRequest` subclass receives an instance that
  has already been authorized and validated (403/422 before the action runs). Before, a
  parameter named `request` got the raw request, so `request.input(...)` skipped every rule,
  and any other name was left unbound. `validated()` caches its result.

### Security

- Hash a changed password on update. `AuthenticatableMixin` hashed only on insert, so
  `user.update({"password": ...})`, `update_attributes()` and a reassigned `password`
  followed by `save()` wrote the plaintext to the column. It now hashes in `save()` too.

### Fixed

- `role:`, `permission:` and `group:` route middleware raise `MisconfigurationError`
  (`USER_MODEL_NOT_AUTHORIZABLE`, HTTP 500) naming `AuthorizableMixin` when the signed-in
  user's model has no `has_role`/`has_permission`/`in_group`. They answered 403 to everyone,
  administrators included, with nothing logged. Guests are still redirected or refused.

- Route middleware parameters are declared, typed and checked when routes are built. Engine
  middleware lists the constructor parameters its alias accepts in `alias_parameters`, and
  values are converted to each default's type. `throttle:10` passed the string `"10"` and
  raised `TypeError` from the second request on; it now yields `max_attempts=10`, and
  `throttle:30,120` also sets `decay_seconds`. A parameter on an alias that takes none
  (`auth:api`, `session:x`, `csrf:x`, `firewall:x`) raises `MiddlewareAliasError` instead
  of turning into a relative redirect or a bogus setting; so does `role:admin,editor`,
  which denied everyone. `MiddlewareAliasError` is a `KeyError`. Project middleware that
  declares nothing keeps the old rule.
- `documentation/security.md` taught `auth:api`; token authentication is the `api` alias.
- `model.column = value` followed by `save()` now writes the column. `Model` had no
  `__setattr__`, so the value landed on the instance, `save()` saw nothing dirty and wrote
  nothing, while later reads still returned the new value. Private names and names the
  class defines (`fillable`, properties, methods) keep normal attribute semantics.
- Saving a new model writes the columns assigned one by one (`model.x = ...`,
  `set_attribute`) as given; only constructor input is filtered by `fillable`, as before.
- `create()` and a new model's `save()` log `mass_assignment_discarded` with the dropped
  keys and the model's `fillable` instead of discarding them silently. Keys starting with
  `_` (`_token`, `_method`) are still dropped without a warning.
- An unknown model attribute names the closest loaded column and lists the loaded ones.

### Changed

- Collapse the `pt` locale into `pt-BR`. `APP_LOCALES`, `SUPPORTED_LOCALES`, the `SetLocale`
  fallback list and the `craft new` config stubs now offer `en`, `pt-BR` and `es` only, and
  `TranslationSeeder` no longer seeds `pt`. Rows an earlier run wrote stay in the database.
- `SetLocale` matches a requested locale to the closest offered one: exact tag, then base
  language, then the first offered variant of the same language. A visitor sending
  `Accept-Language: pt-PT` or `?lang=pt` now lands on `pt-BR` instead of the default locale.

## [4.0.1] r00018 — 2026-09-24

### Fixed

- Make the origin-based CSRF test independent of the developer's `.env`. It sent
  `Origin: http://localhost:9000` while the configured default `APP_URL` is port 8000, so it
  passed only where a local `.env` set 9000 and failed on every clean checkout, CI included.
  It now derives the origin from `app.APP_URL`. Test-only; the engine is unchanged.
- Stop tracking `.coverage`. The binary data file `pytest --cov` writes on every run was
  committed with 4.0.0 and changed in every commit since. It is now ignored, and removed from
  the index only - a local copy is left in place.

## [4.0.0] r00017 — 2026-09-24

The framework is now delivered as a bare engine. A new project starts from `craft new`
with nothing to reuse, and generators add what it needs. This is a breaking release for
any project that relied on the bundled demo application; see Removed.

### Added

- Record every route the framework attaches on the router itself, marked with its origin
  (`craft.http.router.APP_ORIGIN` / `ENGINE_ORIGIN`) and the module that registered it.
  `Kernel.register_engine_routes(refresh=False)` performs the registration,
  `Kernel.engine_routes()` and `Router.engine_routes()` return the entries, and
  `RouteEntry.describe()` renders one as a mapping. The health probes, the metrics scrape,
  the MSR manifest and the static-asset mount were appended straight onto the ASGI route
  table before this, so they answered requests that no route listing could account for.
- Ship `config/msr.py` in a generated project. The file was missing, so the manifest route
  existed with no switch anywhere in the project to find it by.

- Add `craft make:admin`, which generates the RBAC admin panel on request: admin controllers, the panel shell, `Role`, `Permission` and `Group` models, one migration holding every RBAC and ABAC table, the Forge views, the `/admin/*` routes appended to `routes/web.py` behind `auth` and `role:admin`, and the identity model entries in `config/auth.py`.
- Add root agent instructions (`AGENTS.md`) and a route listing with middleware details and JSON output.
- Add a CI check that rejects destructive SQL in seeders and forward migrations.
- Give every published documentation page a meta description taken from its own opening
  paragraph, plus Open Graph and Twitter metadata; `docs:build --base-url` adds canonical
  URLs and writes `sitemap.xml`.
- Resolve the application's identity models through `engine/auth/registry.py`, configured
  under `auth.models` in `config/auth.py`. The engine no longer hardcodes where a project
  keeps its `User`, `Role`, `Permission` and `Group`.
- Add `engine/support/branding.py`, holding the Craft Engine wordmark and brand palette as
  the single source for the console banner and a generated project's starter page.

- `craft new <name>` generates a bare project: configuration, three empty providers, one
  route and the migrations the engine itself needs - no models, controllers, theme or seeded
  data. The console is also installed as `craft`; `dev` keeps working.
- `make:auth` writes the `User` model, its migration and the `config/auth.py` entries, so the
  screens it generates work in a project that has no user model yet.
- `craft.auth.models.AuthenticatableMixin` (password hashing on every insert path) and
  `AuthorizableMixin` (`has_role`, `has_permission`, `can`, delegating to the AccessResolver
  and denying when none is available). The `role:` and `permission:` middleware call these.
- `engine/providers/engine_providers.py`: the one list of engine providers every bootstrap
  registers, so a generated project can no longer fall behind this repository's.
- The schema tenancy strategy (`MULTI_TENANCY_STRATEGY=schema`) now lives in the engine as
  `craft.http.tenant_schema`, beside the rls strategy; it lived in the demo application.
- `make:auth`, `make:admin` and `make:crud` write a bare `layouts/app.forge.py` when the
  project has none - a valid document with a title and a content slot, and no theme.
- The CraftEngine mark and palette in `docs/brand/`.

### Changed

- **Breaking:** the health probes (`/health`, `/ready`) and the MSR JSON manifest
  (`/.well-known/msr.json`) no longer answer unless the application asks for them. Set
  `HEALTH_ROUTES_ENABLED=true` or `MSR_ENABLED=true` to restore either. A project upgrading
  from an earlier release keeps its own `config/framework.py`, whose `HEALTH_ROUTES_ENABLED`
  still reads `True` until it is changed; a project with no `config/msr.py` loses the
  manifest until it adds one. Nothing answering a request that nobody declared is the point:
  readiness discloses the database driver, the cache store and the pool census on every hit,
  and the manifest publishes the exact version of the installation.

- Preserve existing authentication routes and controllers when `make:auth` runs; generated applications also receive the `/signin` navigation alias.
- Seed only missing translations, without clearing existing records or overwriting edited values.
- Refuse schema-wide migration reset and rollback operations regardless of database name or environment.
- Pause persistent-database test execution until its legacy fixtures can isolate data without physical deletion.

### Fixed

- The code `make:auth` generated did not run in a generated project: sign-in answered 500
  (AntiSpam and Honeypot were not registered, and the controller called `Validator.make` and
  `AntiSpam.verify(..., ip_address=...)`, neither of which exists), old input was flashed as an
  empty dict, and the dashboard called Python's `hasattr` inside a template.
- `make:admin` generated a panel nobody could enter: `role:admin` found no `has_role` on the
  generated user and refused everyone, `/admin` redirected to a `/panel` that only the demo had,
  and the views extended a `layouts.panel` that nothing generated.
- `make:crud` skipped registering its JSON API when `routes/api.py` was absent, while still
  printing the API's URL; it now creates the file. Its screens no longer carry theme classes.
- `craft new` generated an empty project from an installed package: the templates were not
  declared as package data, and setuptools' globs drop hidden files such as `.env.example`.
- `make:auth` registered no routes when `routes/web.py` did not exist yet.
- The bundled `plugins/audit-log` imported the demo's `SystemLog` model and silently wrote
  nothing without it; it writes through the `DB` facade.
- `documentation/ai_agents.md` taught `Validator.make(data, rules)`, which does not exist.
- Boot the console against a single application, so `craft migrate` no longer fails with "database is locked" on a file-backed SQLite database: the second application kept its own database connection, and migration DDL ran on it while the migrator held its transaction on the other.
- Stop deleting duplicate cooldown history during unique-index migration; fail with an explicit reconciliation error instead.
- Correct agent context that described the synchronous ORM as asynchronous or the runtime as supporting Python 3.11.

### Removed

- **Breaking:** the demo application. The admin and control panels, the login and
  registration screens, the documentation-site controller, the demo models, services and
  seeders, and the bundled theme are gone; generate what a project needs with `make:auth`,
  `make:admin` and `make:crud`. `v3.23.0-r00016` is the last release carrying them.
  Migrations are all kept, because they have already run on existing databases.
- Stop scaffolding a non-functional MCP configuration that launched `route:list` as though it were an MCP server.

### Security

- Stop disclosing the installation's infrastructure on `/ready`. The probe now answers
  `{"status": ...}` and the HTTP code to every caller; the database driver, the cache store
  class and the connection-pool census are returned only to one presenting
  `HEALTH_READINESS_TOKEN` as a bearer token, compared with `hmac.compare_digest`. The token
  is optional - without one nobody gets the detail - and a wrong token is answered with the
  reduced payload rather than a 404, because a health check the orchestrator cannot reach is
  not a health check.
- Cap what probing costs. Each readiness run issues a `SELECT 1` and a cache write, so an
  unauthenticated path converted request rate directly into database load. One result is now
  shared across every request that arrives within `HEALTH_READINESS_CACHE_SECONDS`
  (default 5; zero restores per-hit checks), bounding the cost by time instead of traffic.

## [3.23.0] r00016 — 2026-09-19

### Added

- **Out-of-the-box AI Coding Agent Suite** (`.claude/`, `engine/cli/agent_scaffolder.py`, `documentation/ai_agents.md`): every workspace and project is born 100% pre-configured with the full development agent catalog — 4 specialized agent roles (`code-reviewer`, `security-auditor`, `test-engineer`, `web-performance-auditor`), 25 development skills, 8 workflow commands (`/spec`, `/build`, `/test`, `/ship`, `/review-change`, `/code-simplify`, `/constraints`, `/webperf`), and 8 reference checklists.
- **Automated AI Governance Contract Scaffolding** (`engine/cli/agent_scaffolder.py`, `tests/test_cli_auth_and_agent.py`): `python dev.py agent:scaffold` now automatically generates canonical `.claude/rules/AGENTS.md` and pointer `.agents/rules/AGENTS.md` to guarantee strict rules enforcement (forward-only migrations, absolute data persistence, English codebase, zero hardcoded text, and zero guessing via concrete workspace inspection).

## [3.22.0] r00015 — 2026-09-19

### Added

- **RFC-compliant static files caching** (`engine/http/static_files.py`, `engine/http/kernel.py`): introduces `CachedStaticFiles` subclassing Starlette's `StaticFiles`. Emits `Cache-Control: public, max-age=31536000, immutable` for fingerprinted asset URLs (`?v=...`) and `Cache-Control: public, max-age=300, must-revalidate` for bare URLs.
- **ICU MessageFormat & CLDR Plurals** (`engine/support/icu.py`, `engine/support/translation.py`): pure Python, zero-dependency renderer supporting `{name}` substitution and CLDR pluralization syntax `{count, plural, =0 {No items} one {# item} other {# items}}`. Integrated directly into `translate()` and `__()` helpers.
- **Application Clock & Timezone Management** (`engine/support/clock.py`, `engine/support/__init__.py`): unified application clock (`clock.now()`, `clock.now_naive()`, `clock.today()`, `clock.to_app_tz()`) synchronizing time across container environment, scheduler jobs, and database timestamps based on `APP_TIMEZONE`.
- **Server-Side DataGrid Engine** (`engine/http/datagrid.py`, `engine/http/__init__.py`): parameterized SQL compilation for complex listing filters, strict column allowlists, safe operator mappings, ordering, grouping, and direct database subtotal calculations (`aggregate_rows`).
- **Native MSR JSON manifest** (`engine/support/msr.py`, `engine/http/msr.py`, `engine/http/kernel.py`, `config/msr.py`, `engine/cli/app.py`, `database/migrations/2026_09_19_000001_seed_msr_manifest_translations.py`, `documentation/msr.md`): every application serves an [MSR JSON 2.0](https://msrjson.org) manifest at `GET`/`HEAD /.well-known/msr.json`, mounted outside the middleware stack with `Access-Control-Allow-Origin: *`. It is built from `config/msr.py` (`MSR_*` variables), the version in `pyproject.toml` with its date from `CHANGELOG.md`, and the translation keys `msr.entity.tagline`/`summary`/`text` in every configured locale (seeded in `en`, `pt-BR` and `es`; the migration adds them to existing databases without overwriting edited copy). Unknown optional fields are omitted; an unresolvable required field — a `localhost` domain included — answers 404 instead of publishing a guess. A hand-written `public/.well-known/msr.json` wins, and an application route on the path takes precedence. `dev msr:show` prints the manifest and `dev msr:validate` checks it against the canonical schema fetched live; `jsonschema` joins the `dev` extra and a new `msr` extra.
- **MSR JSON manifest for craftengine.org** (`deploy/do-app.yaml`): the site publishes <https://craftengine.org/.well-known/msr.json>, an [MSR JSON 2.0](https://msrjson.org) manifest that lets software registries and AI agents list the framework. The manifest lives in the site repository (`msrjson/craftengine.org`); the app spec adds an ingress rule that keeps the `/.well-known` prefix and answers any origin (CORS, `GET`/`HEAD`), as the protocol requires. Domain verification is declared `pending`.
- **Brazil Validator Plugin v2.0.0** (`app/plugins/brazil_validator/`): upgraded with the new 2026 Receita Federal Alphanumeric CNPJ standard (IN RFB 2.229/2024), full 27-state Inscrição Estadual (SINTEGRA specification), RG validation, and CEP/Phone normalizers while maintaining 100% backward compatibility with `DocumentValidatorEngine`.

### Changed

- **Clean initial workspace skeleton for developers & AI agents** (`app/`, `database/`, `resources/`, `routes/`): eliminated demo blog models, controllers, views, policies, events, seeders, and routes from the base workspace skeleton, preventing agents from building hybrid "2-in-1" applications. Reference modules (`cms`, `billing`) and plugins (`brazil_validator`, `qrcode_generator`, `seo_optimizer`) relocated to `documentation/examples/` as isolated architectural blueprints.
- **Documentation points at the official repository** (`README.md`, `CONTRIBUTING.md`, `public/docs/`): every source link and the rebuilt static site now resolve to <https://github.com/msrjson/craftengine> — the GitHub organization was renamed from `msr-standard` to `msrjson`, and both the former `msr-standard/craftengine` and `craftengines/framework` paths redirect there. The site was regenerated with `python dev.py docs build`, which reads the URL from `engine/support/docs.py` and `engine/support/docs_site.py`.
- **Official site at <https://craftengine.org>** (`deploy/do-app.yaml`, `deploy/docs.Dockerfile`): one DigitalOcean App Platform app with two static sites — no database, no server runtime. `/` serves the presentation site from its own private repository (`msrjson/craftengine.org`); `/docs` serves this documentation, rebuilt from `documentation/` on every push to `master`.
- **ASCII-only comments in configuration** (`config/app.py`, `config/security.py`, `config/session.py`): em dashes in explanatory comments replaced with `--`, clearing the seven `LANG-A` violations that made `.claude/rules/lint_language.py` exit non-zero. No behavior change.

## [3.21.0] r00014 — 2026-09-16

### Security

- **Argon2id replaces bcrypt as the default password hash** (`engine/auth/password.py`, `pyproject.toml`): OWASP-recommended memory-hard hash for new passwords; bcrypt and PBKDF2 remain verify-only for existing hashes, `needs_rehash()` upgrades them on next login.
- **AES-256-GCM credential vault** (`engine/security/vault.py`, `Vault` facade): encrypts values that must not sit in the database in plaintext (a third-party API key, an OAuth client secret) — never a hand-rolled cipher. Key derived from `APP_KEY` via HKDF-SHA256 with a domain-separation label distinct from session signing.
- **Context-bound signed tokens** (`engine/auth/signer.py`, `Signer` facade): for password resets and email verification — binds purpose (one token cannot double as another kind) and context (an IP/session, so a leaked token cannot be redeemed elsewhere), plus optional expiry.
- **TOTP two-factor authentication** (`engine/auth/totp.py`): RFC 6238-compliant, pure stdlib, verified against the RFC's own official test vectors.
- **Sensitive-value redaction in every log line** (`engine/support/redaction.py`, `engine/support/logging.py`): known-sensitive field names and secret-shaped patterns (bearer tokens, card numbers) are scrubbed before a record leaves the process — the single formatter funnel every `craft.*` logger passes through, so `engine/exceptions/handler.py`'s exception logging is covered without a separate change.
- **Firewall pipeline hardening** (`engine/security/firewall.py`, `config/firewall.py`): CIDR-range whitelist/blacklist rules, decaying reputation scores (an old incident stops weighing an IP down forever), shadow mode (detect and log without blocking, for testing a new rule), health-check path exemption.
- **Atomic sliding-window login-cooldown upsert** (`engine/security/honeypot.py`) — closes Slice 0 item 0.11: the failed-login counter used to read-then-write in two statements, letting concurrent attempts (exactly what brute-force tooling produces) lose an increment. Now a single `INSERT ... ON CONFLICT ... DO UPDATE ... RETURNING` statement, with a real sliding window (a stale streak resets instead of accumulating forever). Usernames are now hashed (SHA-256) before storage instead of kept in clear.
- **Database session store with idle timeout and revocation** (`engine/http/session.py`, new `sessions` table): unlike the cookie/file stores, a row here can be revoked from outside the browser that holds it (admin action, "log out everywhere," a password change), and idle time is tracked independent of the cookie's own absolute lifetime.
- **Step-up authentication** (`engine/auth/step_up.py`, `fresh:<seconds>` route middleware alias): a sensitive action (change password, view billing, grant admin) now requires the session to have authenticated within a configurable recent window, not just "logged in."
- **Origin-based CSRF as a second layer** (`engine/http/middleware.py`): `Origin`/`Referer`, when present, is checked against the app's own origin before the token — an independent signal an attacker who obtained a valid token (e.g. via same-origin XSS) still cannot forge, since the browser sets these headers itself.
- **Per-prefix Content-Security-Policy with report-only mode** (`config/security.py`): different path prefixes can carry different CSP rules (longest-prefix match), and a policy can be rolled out in `Content-Security-Policy-Report-Only` before it enforces.
- **Reverse-proxy IP spoofing** (`engine/security/net.py`, `engine/security/firewall.py`, `engine/http/request.py`): `Request.ip()` and the firewall used to trust the left-most `X-Forwarded-For` entry, which a client controls. Reads from the right now, skipping a configurable number of trusted proxy hops (`config/app.py: trusted_proxy_hops`, `TRUSTED_PROXY_HOPS`).
- **Captcha code readable in markup** (`engine/security/captcha.py`): the challenge is rendered as a distorted PNG (Pillow) instead of plain-text rotated `<span>` characters a script could read straight from the DOM.
- **SQL LIKE-binding percent escaping** (`engine/orm/connection.py`): `normalize_placeholders()` now escapes literal `%` in the query text when bindings are present, so a bound `%` cannot be misread as a driver format specifier.
- **Error responses leaked internals** (`engine/http/kernel.py`): unhandled exceptions now return a stable `code`/`message_key` instead of `str(exc)`; the full exception is still logged server-side.
- **Tenant write predicate silently degraded** (`engine/orm/tenant_scoped.py`, `engine/orm/tenancy.py`): a `TenantScoped` instance with no tenant on its loaded row now raises `UnaddressableTenantRowError` on `save()`/`delete()` instead of falling back to an unscoped `WHERE id = ?`.
- **Unbound/suspended/mismatched tenant host silently resolved anyway** (`engine/http/middleware.py`, `engine/orm/tenancy.py`, new migration `2026_09_16_000001_add_status_to_tenants.py`): `ScopeTenant.resolve()` used to fall through to the authenticated user's tenant whenever a non-reserved subdomain matched no tenant, and treated a suspended tenant identically to one that never existed. Now raises `UnboundTenantHostError` (404), `TenantSuspendedError` (403), or `TenantHostMismatchError` (403 — host names one tenant, the session belongs to another) instead of letting the request proceed with the wrong tenant, or none at all, bound. New `tenants.status` column distinguishes "suspended" from "never existed"; `is_active` is kept for backward compatibility.

### Fixed

- **Exception chaining in token validation** (`engine/auth/signer.py`): added `from None` to `InvalidTokenError` raises inside `except ValueError` and `except (ValueError, UnicodeDecodeError)` blocks, satisfying Ruff B904 and preventing internal exception context leakage.
- **Destructive database operations on a permanent database** (`engine/migrations/safety.py`, `engine/cli/app.py`, `engine/migrations/migrator.py`): `migrate fresh/reset/refresh` and `db wipe --force` now refuse (NR-02) unless the target database is disposable (in-memory SQLite, a `_test` suffix, or explicitly allowlisted via `DB_DISPOSABLE_DATABASES`).
- **Scoped container instances leaked across concurrent requests** (`engine/container/application.py`, `engine/http/kernel.py`): scoped bindings now live in a `ContextVar` opened per request (`Container.begin_request_scope()`/`end_request_scope()`) instead of a class-level dict shared by every in-flight request.
- **Lost updates on concurrent model edits** (`engine/orm/model.py`): `Model` now tracks dirty state (`sync_original()`, `get_dirty()`, `is_dirty()`) and `save()` writes only the changed columns, so two editors touching different fields on the same row no longer clobber each other.
- **RGBA-to-JPEG export inverted transparent regions** (`engine/media/image.py`): transparent pixels are composited over white before the RGB conversion instead of a bare `convert("RGB")`.
- **Settings shared across tenants** (`engine/support/settings.py`): values are namespaced per tenant (`storage_key()`) with fallback to the installation-wide value, instead of one shared dictionary for every tenant.
- **A caught statement failure aborted the whole PostgreSQL transaction** (`engine/orm/connection.py`): each statement inside a transaction now runs under its own `SAVEPOINT`, so a caught failure rolls back only that statement.
- **`TenantScoped` combined with `SoftDeletes` silently dropped one mixin's guarantee** (`engine/orm/model.py`, `engine/orm/tenant_scoped.py`, `engine/orm/soft_deletes.py`): both mixins now compose through a shared, cooperative `_base_query()`/`_write_predicate()` chain regardless of declaration order; `SoftDeletes.delete()`/`force_delete()`/`restore()` address their row through `_write_predicate()` instead of a hardcoded `WHERE id = ?`, so they inherit tenant-safe addressing automatically.
- **`QueryBuilder.insert()`/`.truncate()` bypassed tenant safety** (`engine/orm/query_builder.py`): `insert()` now stamps the bound tenant on a tenant-scoped model (explicit value still wins, matching `force_create()`'s existing data-import precedent); `truncate()` now refuses (`DestructiveOperationRefused`) on a tenant-scoped model, since it has no `WHERE` clause by construction.
- **`BelongsToMany.attach()`/`.detach()`/`.sync()` bypassed tenant safety** (`engine/orm/relationships.py`): pivot-table writes now stamp and scope by the bound tenant when the pivot table itself carries a tenant column; a pivot without one is unaffected.

### Added

- **Multi-agent pytest harness** (`tests/conftest.py`): per-worker test database naming for parallel runs (always ending in `_test`, so the existing disposable-database check accepts it), a refusal to run against a non-disposable database, a PostgreSQL advisory lock coordinating schema-mutating fixtures across workers, a shared `two_tenants` fixture, a `client_for_host()` test-client helper, and an `unprivileged_postgres_role` fixture for row-level-security enforcement tests.
- **Tenant scope guardian** (`engine/orm/tenant_guardian.py`, `config/database.py: tenancy.guardian_mode`, `TENANCY_GUARDIAN_MODE`): a second-layer check behind row-level security — `warn` (default) logs when a request proceeds with no tenant bound, `strict` raises `TenantScopeUnboundError`. Console/queue-job contexts are exempt. Wired into `ScopeTenant.handle()`.
- **Transaction-mode pooler detection and `statement_timeout`** (`engine/orm/connection.py`, `config/database.py: tenancy.statement_timeout_ms`, `DB_STATEMENT_TIMEOUT_MS`): once per process, probes for a PgBouncer-style transaction-mode pooler in front of a PostgreSQL connection (which does not guarantee `SET`/session state, including tenant binding, persists across statements) and logs a structured warning — detection only, never enforcement. `statement_timeout` is applied to every checked-out connection independent of the probe result.
- **`db:audit-rls` CLI regression coverage** (`tests/test_tenancy_wiring.py`): the existing `dev.py db:audit-rls` command (inheritance-class reporting, declared exclusions, CI-friendly exit code) is now pinned by tests against a properly tenant-scoped table and a deliberately unprotected one.
- **Development agent catalog** (`engine/cli/agent_catalog/`, `engine/cli/app.py`, `engine/cli/agent_scaffolder.py`):
  - Installable Markdown catalog adapted to Craft Engine: 4 agents (`code-reviewer`, `security-auditor`, `test-engineer`, `web-performance-auditor`), 25 workflow skills (spec, planning, incremental build, TDD, debugging, review, simplification, security, performance, observability, API design, frontend, documentation and ADRs, git and release, CI, deprecation and migration, shipping, and the `using-agent-catalog` router), 9 commands (`/spec`, `/plan-tasks`, `/build`, `/test`, `/review-change`, `/code-simplify`, `/constraints`, `/ship`, `/webperf`) and 7 shared reference checklists.
  - `python dev.py agent:list [--kind]` lists the catalog; `python dev.py agent:install NAME... | --all [--force]` installs into `.claude/`, checking every conflict before writing.
  - `agent:scaffold` now installs the whole catalog alongside the context files.
  - Catalog files ship as package data (`pyproject.toml`); third-party license notice in `engine/cli/agent_catalog/references/third-party-notices.md (installed with every selection)`.
  - `tests/test_agent_catalog.py` covers content completeness, frontmatter, install selection, overwrite refusal and the CLI commands.
- **Live performance & concurrency benchmark report** (`documentation/market_evaluation.md`, `.agents/docs/benchmark-2026-09-16.md`): live load testing across standard endpoints demonstrating ~290–308 req/s under 100 concurrent clients (+820% to +1,930% throughput increase vs. August 2026 baseline, zero timeouts or errors) and full-stack framework comparison matrix.

## [3.20.0] r00013 — 2026-09-08

Authentication Scaffolding (`make:auth`), AI Agent Discovery Protocol (`agent:scaffold`), `llms.txt` Standards, and Framework Tooling.

### Added

- **Authentication Generator (`make:auth`)** (`engine/cli/auth_scaffolder.py`, `engine/cli/app.py`):
  - Scaffolds a complete authentication slice: `app/Http/Controllers/Auth/AuthController.py`, `app/Http/Requests/Auth/LoginRequest.py`, `app/Http/Requests/Auth/RegisterRequest.py`.
  - Scaffolds server-rendered Forge authentication views under `resources/views/auth/` (`login.forge.py`, `register.forge.py`, `dashboard.forge.py`) featuring `@csrf`, `@honeypot`, and `@error('field')` error presentation.
  - Idempotently wires authentication web routes into `routes/web.py` (`/login`, `/register`, `/logout`, `/dashboard`).
  - Supports `--views` flag for view-only generation and `--force` for safe overwrites.

- **AI Agent Tooling & Discovery (`agent:scaffold`)** (`engine/cli/agent_scaffolder.py`, `engine/cli/app.py`):
  - Added `python dev.py agent:scaffold` (and `agent:rules`) command to bootstrap full context for AI coding assistants (Cursor, Claude Code, Windsurf, AGY).
  - Generates `.cursorrules` in project root with high-density framework rules, Active Record patterns, and database safety invariants.
  - Generates standard `llms.txt` and `llms-full.txt` files (following the llmstxt.org specification) in repository root and `documentation/` for instant LLM indexing.
  - Generates `.agents/mcp.json` configuration snippet for Model Context Protocol integrations.

- **Developer Documentation & Guides**:
  - `documentation/ai_agents.md`: Comprehensive guide for configuring and utilizing AI coding agents with Craft Engine.
  - Updated `documentation/cli.md` with `make auth` and `agent:scaffold` documentation.
  - Updated `documentation/validation.md` with complete form validation directives, file rules, and redirect error bag usage.

- **Automated Test Coverage** (`tests/test_cli_auth_and_agent.py`):
  - Comprehensive unit test suite covering `build_auth`, `scaffold_agent_stack`, idempotency, and `--force` safeguards.

## [3.19.0] r00012 — 2026-09-08

Form Validation, Anti-Spam Security Subsystem, Python 3.14+ Modernization, and Release Non-Regression Governance.

### Added

- **Comprehensive Form Validation Subsystem** (`engine/validation/`):
  - Extended validation rules: `required_without`, `required_without_all`, `prohibited`, `prohibited_if`, `prohibited_unless`, `ip`, `ipv4`, `ipv6`, `json`, `digits`, `digits_between`, `decimal`, `starts_with`, `ends_with`, `timezone`, `spam_free`, `honeypot`, `file`, `image`, `mimes`, `max_file_size`, `min_file_size`, `alpha_spaces`, `no_html`, and `text`.
  - `MessageBag` and `ViewErrorBag` (`engine/validation/error_bag.py`) providing structured error querying (`has`, `first`, `get`, `all`, `any`, `keys`, `items`, `values`), full dict compatibility, and seamless template inspection.
  - Dynamic rule extensibility via `Validator.extend(name, callback, message)` allowing domain modules and capability plugins to register custom validation algorithms.
  - Enhanced `FormRequest` (`engine/validation/form_request.py`) with native `antispam` flag, action binding, and `error_bag()` access.

- **Enterprise Anti-Spam Subsystem** (`engine/security/antispam.py`, `AntiSpam` facade):
  - Cryptographic time-traps: HMAC-SHA256 signed timestamp tokens (`generate_time_token`, `verify_time_token`) preventing instant bot submissions (< 2.0s) and expired stale form submissions (> 24h).
  - Obfuscated honeypot traps (`generate_fields`): Screen-reader and accessible markup (`aria-hidden="true"`, `tabindex="-1"`, `autocomplete="new-password"`) that captures automated scrapers and headless submission bots while remaining completely invisible to human users.
  - Content heuristics scoring: Scans form submissions for spam patterns (casino, pharma, phishing patterns), excessive hyperlink density (> 35%), and known disposable email providers (`tempmail`, `mailinator`, etc.).
  - Integrated audit persistence: Trapped bot submissions record `FORM_SPAM_TRAP` events into the `security_events` table for correlation with WAF and IP cooldowns.

- **Forge Template Engine Form Directives** (`engine/view/forge.py`):
  - `@error('field') ... {{ message }} ... @enderror` directive for streamlined field validation error rendering.
  - `@honeypot` and `@antispam` directives for one-line injection of hidden honeypot fields and time tokens.
  - Global template helpers: `honeypot_field()`, `antispam_fields()`, `errors` (automatic `ViewErrorBag` injection from session flash).

- **Fluent HTTP Redirect Responses** (`engine/http/response.py`):
  - `RedirectResponse` with chaining: `.with_errors(validator_or_dict)` and `.with_input(request.all())`.
  - `redirect.back(request, fallback="/")` helper for safe referer navigation following form validation failures.

- **Release Non-Regression Governance Standard** (`.claude/rules/RELEASE_NON_REGRESSION_STANDARD.md` and `.agents/rules/RELEASE_NON_REGRESSION_STANDARD.md`):
  - Seven Non-Regression Laws (NR-01 to NR-07) enforcing version synchronization, monotonic `rNNNNN` counter increments, absolute database persistence (banned drop/wipe commands), mandatory pre-release testing gates, immutable changelog contracts, facade backward compatibility, and form security standards.
  - Automated non-regression test suite (`tests/test_release_non_regression.py`).

### Fixed

- Fixed Ruff `B009` constant attribute access in `engine/orm/sluggable.py`.
- Prevented character encoding failure on Windows cp1252 consoles during language linter runs.
- Enforced constant-time secret comparison (`hmac.compare_digest`) across all security challenge tokens.

## [3.18.0] r00011 — 2026-08-27

High availability: the work needed before a second instance of the application
can be run safely, and before an incident on one of them can be diagnosed.

### Added

- **Health probes**, mounted outside the middleware stack so a probe costs no
  session load, no CSRF check and no user lookup (`engine/http/health.py`).
  - `/health` is liveness and touches nothing external: a probe that checked
    the database would get every healthy web instance restarted during a
    database incident, turning one outage into two.
  - `/ready` is readiness — a database round-trip, a cache round-trip and the
    connection pool census — and answers `503` when a critical check fails, so
    an instance that cannot serve is taken out of rotation instead of returning
    errors. Extensible with `HealthCheck`; an application route on either path
    takes precedence over the built-in one.
  - Configured by `HEALTH_ROUTES_ENABLED`, `HEALTH_LIVENESS_PATH`,
    `HEALTH_READINESS_PATH`.

- **ASGI lifespan with graceful shutdown** (`engine/http/kernel.py`). The
  lifespan is handled by the outer application rather than the inner Starlette
  instance, which is rebuilt whenever the route table changes — a shutdown hook
  on a replaced instance would never run. The connection pool is closed after
  the server has drained in-flight requests.

- **Cooperative worker shutdown** (`engine/support/shutdown.py`). `queue work`
  and `schedule work` finish the job in hand on `SIGTERM` and exit, instead of
  being killed mid-job and leaving the job reserved until the stale sweep
  reclaimed it — with any side effect it had already performed repeated on the
  retry. A second signal still exits immediately.

- **Request correlation** (`engine/support/context.py`,
  `RequestContext` middleware). Every request gets an identifier, returned as
  `X-Request-ID`, carried on every log line it produces and handed to error
  reporters. An inbound identifier is echoed so a trace survives a hop between
  services, but only after validation: the header is attacker-controlled, and a
  newline in one forges log entries. Held in a `ContextVar`, not a
  thread-local, because a pooled worker thread is reused by the next request.

- **Structured logging** (`engine/support/logging.py`). `LOG_FORMAT=json` emits
  one object per line with the request context as real fields and anything
  passed through `extra=` alongside it; `text` keeps the readable format and
  appends the request id. The `stderr` channel defaults to JSON.

- **Metrics** in the Prometheus text format (`engine/support/metrics.py`),
  **off by default**: the payload names every route the application serves and
  how often each is hit, which is reconnaissance if reachable from outside.
  `craft_requests_total`, `craft_request_duration_seconds`,
  `craft_exceptions_total` and a `craft_db_pool_connections` gauge. Routes are
  labelled by matched pattern, never raw path, so `/posts/{id}` is one series
  rather than one per post. Enabled with `METRICS_ENABLED`, optionally guarded
  by `METRICS_TOKEN` (a request without it gets `404`, not `401`).

- **Pluggable error reporting**. `ExceptionHandler.reporter(callback)`
  registers a sink — Sentry or any other — called with the exception and the
  request context, so the framework carries no vendor and a report names the
  request instead of arriving as an anonymous stack trace. Only server faults
  reach a reporter, and a reporter that raises is logged and skipped.

- **Migration advisory lock**. `migrate` and `rollback` take a session-scoped
  advisory lock on PostgreSQL, so every container in a deployment can run the
  same command at boot: the first migrates, the rest wait and find nothing
  pending. Bounded by `MIGRATION_LOCK_TIMEOUT` (default 120s). Session-scoped
  rather than transactional because migrations open their own transactions and
  a concurrent index build cannot run inside one. Drivers without advisory
  locks run unlocked, as before.

- **Documentation**: `documentation/observability.md`, and new
  Health checks / Rolling deploys / Threads and the connection budget sections
  in `documentation/deployment.md`.

### Fixed

- **Connection leak on `async` controller actions**. The coroutine ran on a
  throwaway single-worker executor, checking out a thread-local pooled
  connection that the request thread's `release()` never saw; the pool lost one
  slot per async request until every request timed out. It now runs on the
  request's own worker thread. As a backstop, a session whose owning thread
  dies without releasing has its slot reclaimed.

- **Stale pooled connections were reused after a failover**. Connections idle
  longer than `pool_recycle` (default 900s) are reopened, and one idle longer
  than 30s is pinged before reuse. A statement that hits a broken socket now
  discards its connection instead of returning it to the pool, where it
  previously circulated indefinitely.

- **The outer `commit()` succeeded silently after an inner rollback**. Without
  savepoints, a rollback from an inner transaction level discards the outer
  work too; the outermost `commit()` then committed an empty transaction and
  returned as if the work had been persisted. It now raises
  `TransactionRolledBackError` (`DB_TRANSACTION_ROLLED_BACK`,
  `database.transaction.rolled_back`, seeded in every locale).

### Changed

- **Connection check-in costs one round-trip instead of up to four.** The
  tenant `search_path` and tenant GUC are cleared with a single `RESET ALL` in
  autocommit, replacing two `SET` + `COMMIT` pairs; the configured
  `search_path` moved to a connection startup option so it is the session
  default `RESET` restores.

- **Thread pool sized from the connection pool** (`pool_size × 2`, minimum 8)
  instead of the runtime default of 40. Forty threads against a pool of four
  meant thirty-six queueing on `pool_timeout` rather than being turned away.
  Override with `HTTP_THREADPOOL_SIZE`.

- **PostgreSQL connection defaults**: `sslmode` is now `require` rather than
  `prefer`, which falls back to plaintext when TLS cannot be negotiated;
  `pool_size` 10 → 4 and `pool_timeout` 30 → 10 so one process fits a managed
  22-connection limit; `application_name` is set so `pg_stat_activity` can name
  the process holding connections open. `DB_SSLROOTCERT` added for
  `verify-full`.

  **Upgrade note**: a deployment that relied on `DB_POOL_SIZE=10` must now set
  it explicitly, and one that cannot offer TLS must set `DB_SSLMODE=prefer`
  deliberately.

## [3.17.3] r00010 — 2026-08-26

### Added

- **Native Business Modules & Capability Plugins Architecture**.
  - Structured business domains into modular packages under `app/modules/` (`cms` and `billing`) with native `module.py` lifecycle handlers (`register()` for IoC container bindings, `boot()` for route mounting).
  - Created stateless capability plugins under `app/plugins/` (`brazil_validator` Modulo 11 CPF/CNPJ engine, `qrcode_generator` SVG vector matrix engine, `seo_optimizer` slugification & SERP auditor) with native `plugin.py` IoC providers.
  - Enforced thin controller transport layer (< 150 lines per controller) and native HTML template rendering.
  - Added test suite `tests/test_modules_and_plugins.py` verifying plugin resolution and module isolation.

- **Engineering Governance & Code of Conduct Directive**.
  - Added `.agents/rules/ENGINEERING_GOVERNANCE.md` and `documentation/governance.md` enforcing file/function line thresholds, layer purity, 100% English codebase, and financial `bank_slip` domain standards.

## [3.17.2] r00009 — 2026-08-25

### Security

- **Sequential Integer ID Query Rejection for UUID Models**.
  - Enforced framework-wide UUIDv7 security standard by rejecting sequential integer/digit ID lookups in `Model.find_by_route_key()` and `Model.find_by_uuid()` when `uses_uuid` is enabled and table carries a UUID column.
  - Prevents ID enumeration attack vectors by requiring valid public UUIDs (UUIDv7) to resolve records on protected models.

## [3.17.1] r00008 — 2026-08-25

### Added

- **Automated Language & i18n Standard Enforcement Gate**.
  - Added `tools/lint_language.py`, `language-standard.toml`, and `language-standard.views.toml` to enforce English identifiers, comments, and translation key usage.
  - Integrated `lint_language.py` verification into `.github/workflows/deploy.yml` CI pipeline.
  - Added `.agents/rules/` and `.claude/rules/` developer standards.

## [3.17.0] r00007 — 2026-08-24

### Changed

- **Migrated runtime and baseline requirements to Python 3.14+**.
  - Updated `pyproject.toml` (`requires-python = ">=3.14"`, classifier `Programming Language :: Python :: 3.14`, and ruff `target-version = "py314"`).
  - Updated development and production Dockerfiles to `python:3.14-slim`.
  - Updated GitHub Actions CI/CD workflows to execute test matrices and doc builds on Python 3.14.
  - Updated documentation, landing page badges, security policies, and contribution guidelines to reflect Python 3.14+.

## [3.16.0] r00006 — 2026-08-24

### Added

- **The documentation is published as a site** at
  <https://msr-standard.github.io/craftengine/>, built by CI on every push to
  master. Until now the 30 guides in `documentation/` were readable only by
  cloning the repository and running the application — anyone arriving from
  GitHub read raw Markdown with no navigation between pages.
  - `craft.support.docs.DocsLibrary` — discovery, titles, navigation and
    rendering, shared by the application's `/docs` routes and the static site.
    One implementation on purpose: a link that works on the site and 404s in
    the app is the kind of difference nobody notices until a reader reports it.
  - `dev.py docs:build` renders the guides to static HTML;
    `dev.py docs:check` fails on a cross-reference that points at a page which
    does not exist. The build runs the check first and refuses to publish, so a
    dead link fails CI instead of shipping — an author never sees these, because
    the file they linked to is open in front of them while they write the link.

### Fixed

- **A production install could not boot the framework.** `engine/ai/manager.py`
  imports the Gemini and OpenAI drivers at module level and those imported
  `httpx` at module level — but `httpx` is not a runtime dependency, so
  registering the AI service provider raised `ModuleNotFoundError` on any
  install without the `dev` extra. CI found it, by being the first thing to run
  `pip install -e "."` without it. Both drivers now import the client inside
  the call that needs it and name the package when it is missing, the way every
  other optional backend here already does (boto3, redis, psycopg2, pymysql),
  and `httpx` is declared as the `ai` extra.
- **Every cross-reference between guides was already broken in the running
  application.** `/docs/orm` rendered `href="postgres.md"` verbatim, the browser
  resolved it to `/docs/postgres.md`, and the route looked for a file named
  `postgres.md.md`. Markdown links between guides are written to work on
  GitHub, and neither the app nor a static site serves paths shaped like that;
  they are now rewritten per consumer (`/docs/postgres` and `postgres.html`
  respectively), with anchors preserved. Links escaping `documentation/` — such
  as `../CHANGELOG.md` — point at the file on GitHub, where it exists.

- **The seeded tenant account could not work.** `UserSeeder` creates
  `tenant@craft.local` with `type = "tenant"`, and that user belonged to no
  tenant while the `tenants` table stayed empty — so turning multi-tenancy on
  produced an account whose every scoped query raised `TenantNotBoundError`,
  because nothing resolved a tenant for it by host or by user. The seeder now
  creates the demo tenant (`acme`) and points that account at it, idempotently.
  Seeding a user whose own configuration cannot work is worse than seeding
  nothing, because it looks finished.
- **The CHANGELOG was missing the `[3.12.0]` section and the `[3.13.0]` release
  counter.** The 3.13.0 cut overwrote the `## [3.12.0]` header rather than
  inserting a new section above it, so 712 lines of released history sat
  unlabelled. The section is restored byte-for-byte from
  `git show v3.12.0:data/CHANGELOG.md` — recovered from the repository's own
  history rather than reconstructed — and `[3.13.0]` is labelled `r00003`, the
  counter it was cut with.

## [3.15.0] r00005 — 2026-08-24

### Added

- **A fresh project is now born with row-level security wired, not merely
  available.** The isolation layer existed as a library that a new checkout
  could not reach:
  - `database/migrations/2025_01_01_000000_create_tenants_table.py` — the
    `tenants` table `t.tenant_scoped()` references by default. Without it that
    call failed outright on PostgreSQL (`relation "tenants" does not exist`),
    so the one-line contract the guide advertises did not work. The table ships
    whether or not tenancy is enabled; it costs nothing empty, and its absence
    is what turned enabling tenancy from a config change into a schema change.
  - `dev.py db:provision-role` — creates the `NOBYPASSRLS` application role
    policies actually apply to, grants it on current *and* future tables, then
    re-reads `pg_roles` and fails if the role still bypasses. Creating a role
    is not the same as the role being subject to policies.

### Fixed

- **`MULTI_TENANCY_STRATEGY` was named in error messages and documentation
  while nothing read it.** "Switch to `MULTI_TENANCY_STRATEGY=rls`" — the
  instruction the tenant middleware prints when it refuses — had no effect at
  all. It is now a real config that selects the middleware, and an unrecognised
  value stops the boot rather than silently serving every tenant from one set
  of tables.
- **`ScopeTenant` was never registered by the bootstrap**, so the row-level
  strategy could not be selected even by editing config. Only the older
  schema-per-tenant middleware was wired.
- **The release automation cut tags that did not match the documented scheme.**
  `CONTRIBUTING.md` specifies `vX.Y.Z-rNNNNN`, and the CI step read only the
  version from `pyproject.toml` — which is how `v3.12.0` and `v3.13.0` were
  tagged with no counter at all. The policy and the automation disagreed and
  the automation won silently. It now reads the counter from
  `engine/__init__.py`, and fails the build when the two files that declare the
  version disagree with each other.

- **CI had been red since 2026-08-19 and no release was shipping.** The
  `Lint (ruff)` step failed, and because the release job depends on it
  (`needs: [test-sqlite, test-postgres, docker-build]`), it was skipped on
  every push - which is why tag `v3.13.0` exists on GitHub with no matching
  Release. Five violations, four of them pre-existing:
  - `engine/ai/contracts.py` used `Union` without importing it, and
    `engine/mail/drivers/log.py` used `Optional` without importing it. Both
    survive at runtime thanks to `from __future__ import annotations`, but
    they break `typing.get_type_hints()` and any reading of the annotations.
  - `engine/security/honeypot.py` computed `now_str` in `is_blocked()` and
    never used it.
  - `engine/storage/drivers/s3.py` re-raised `ImportError` inside an `except`
    without `from`, hiding the original cause.
  - `engine/orm/query_builder.py` used `zip()` without `strict=` in the
    similarity computation; the dimension check just above is what makes the
    operation meaningful, and a silent truncation would score a mismatched
    vector as a partial hit instead of excluding it.

## [3.14.0] r00004 — 2026-08-20

### Added

- **Database Safety & Absolute Data Persistence Policy (`documentation/database_safety.md`)**:
  - Established framework-wide Absolute Data Persistence policy forbidding destructive schema actions across development, test, demo, staging, and production environments.
  - Documented forward-only migration workflows (`python dev.py migrate`), non-destructive alter patterns, and idempotent seeding.
  - Documented mandatory soft-delete query and lifecycle patterns (`deleted_at = now()`, `is_active = False`) replacing physical `DELETE` and `TRUNCATE` operations.
  - Added safety notices and banned command lists to CLI documentation (`documentation/cli.md`) and Migration guides (`documentation/migrations.md`).
- **PostgreSQL-native data layer** — six phases turning PostgreSQL from a row
  store into the runtime the framework depends on. Every capability is gated by
  `engine/orm/dialect.py`, so a query written for PostgreSQL fails on another
  driver with a message naming the driver and the feature, never with a syntax
  error from the driver or a filter that quietly means something else.
  - **Expression seam (`engine/orm/expression.py`)**: `Expr` carries
    framework-authored SQL plus its bindings, and `QueryBuilder.where_expr()` /
    `select_expr()` / `order_by_expr()` accept it. This is how the PostgreSQL
    operators (`@>`, `@@`, `<=>`, `#>>`) became reachable **without** widening
    the identifier and operator allowlists that guard every other clause.
    `Raw` marks a DDL snippet that must be emitted unquoted
    (`DEFAULT gen_random_uuid()`).
  - **Dialect capabilities (`engine/orm/dialect.py`)**: one place answering
    "can this driver do X?". Extension-gated capabilities (`vector`, `trigram`)
    are **probed** against `pg_extension` on first use rather than assumed from
    the server version, and the refusal names the missing extension.
  - **Tenant isolation on row-level security** (`engine/orm/tenancy.py`,
    `engine/orm/tenant_scoped.py`, `ScopeTenant` middleware,
    `Blueprint.tenant_scoped()`, `Tenant` facade): the tenant is bound to the
    `app.current_tenant_id` session variable through `set_config()` — `SET
    LOCAL` cannot take a parameter — and read by generated `USING` /
    `WITH CHECK` policies that fail closed when nothing is bound.
    `Connection.release()` clears the variable at checkin.
  - **Transactional queue on `SELECT … FOR UPDATE SKIP LOCKED`**
    (`engine/queue/drivers/`): batch claims, priority, exponential backoff with
    full jitter, a `failed_jobs` dead-letter table, stale-reservation
    reclamation, and per-job tenant rebinding. `engine/queue/listener.py` adds
    `LISTEN`/`NOTIFY` dispatch and a `Broadcast` facade.
  - **PostgreSQL types and search** (`engine/orm/casts.py`,
    `engine/orm/postgres/macros.py`): attribute casting for JSONB, arrays,
    ranges and vectors, plus query macros for JSONB containment and JSON-path,
    array containment/overlap, range overlap and adjacency, full-text search
    over generated `tsvector` columns, trigram similarity, and pgvector
    distance operators.
  - **Distributed locks (`engine/orm/locks.py`, `Lock` facade)**: advisory
    locks, transaction-scoped by default so a crashed holder cannot strand
    them. `Cache.add()` was added as an atomic put-if-absent for the fallback
    path.
  - **Migration DSL**: partial, expression, GIN/GiST/HNSW and `CONCURRENTLY`
    indexes; `CHECK` and `EXCLUDE` constraints; declarative range/list/hash
    partitioning with `Schema.partition()` and `Schema.ensure_partitions()`;
    managed extensions via `Schema.extension()`.
  - **New commands**: `db:audit-rls`, `db:extensions`, `db:partitions`,
    `db:locks`, `queue failed`, `queue retry`, `queue reclaim`, and
    `queue work --listen`.
- **Server version awareness.** The dialect reads the live server version and
  gates version-specific capabilities on it, the same way extension-gated ones
  are probed. `uuidv7()` — a built-in from PostgreSQL 18 — is refused with a
  message naming the version on older servers rather than emitted and left to
  fail at insert time. `dev.py db:show` reports the version and advises when it
  is below the recommended one.

### Changed

- **`MULTI_TENANCY_ENABLED` now defaults to off.** Multi-tenancy is an
  architectural decision with a cost — a tenant bound on every request, an
  isolation policy on every table, and a database that can enforce one — and
  not something an application should acquire by accident. With the default on,
  the out-of-the-box experience depended on the driver: a single-tenant app on
  SQLite worked only until somebody signed in as the seeded `type = "tenant"`
  user, at which point the request was refused because SQLite cannot isolate
  anything. Turning it on is now the deliberate act, which is what makes the
  refusal that follows on a driver without isolation correct rather than a
  surprise. A tenanted deployment sets `MULTI_TENANCY_ENABLED=true`.
- **PostgreSQL 18.4+ is now the recommended and provisioned version**
  (`docker-compose.yml`, `docker-compose.prod.yml`), up from 15. 14 remains the
  supported minimum. Two things change together on upgrade and doing only one
  leaves the container restart-looping: the data directory format (dump and
  restore, or `pg_upgrade`), and the **mount point** — from 18 the official
  image stores data in a major-version subdirectory of `/var/lib/postgresql`
  and refuses to start if it finds a volume at the old
  `/var/lib/postgresql/data`. Both compose files move the mount up one level.
  The procedure is in `documentation/postgres.md`.

### Fixed

- **The queue destroyed failed jobs.** `QueueManager.fail()` issued a `DELETE`
  and wrote a log line, so a permanently failing job and its payload were gone —
  nothing to inspect, nothing to retry. Jobs now move to `failed_jobs` in a
  single transaction and come back with `dev.py queue retry`.
- **Failed jobs burned every attempt in milliseconds.** A retry cleared
  `reserved_at` with no delay, so a thirty-second dependency outage killed jobs
  that one retry would have saved. Retries are now backed off with full jitter.
- **Vector search read the whole table into the process.** Similarity was
  computed in a Python loop and — worse — the filter ran *after* `LIMIT`/`OFFSET`
  and after `paginate()` had counted, so page totals described a different result
  set than the page contained. It now compiles to pgvector's distance operators;
  the in-process path remains for drivers without pgvector, with the ordering
  and pagination corrected.
- **`without_overlapping()` was a check-then-set race.** `cache.has()` followed
  by `cache.put()` let two schedulers both see no lock and both run. It now takes
  an advisory lock, falling back to the new atomic `Cache.add()`.
- **Migrations were not atomic.** Each statement auto-committed, so a failure
  partway left a half-built schema and no ledger row. A migration and its ledger
  row are now one transaction where the driver has transactional DDL, with
  `transactional = False` to opt out for `CREATE INDEX CONCURRENTLY`.
- **Workers never released their pooled connection.** Only the HTTP kernel
  called `db.release()`, so a long-running worker held one connection per thread
  for its lifetime — the exhaustion the pool exists to prevent.
- **`Model.new_uuid()` returned a version 4 UUID.** Uniformly random keys
  scatter every insert across the whole index; it now returns a time-ordered
  version 7, which is identically opaque in a URL and materially cheaper to
  index.

### Security

- **Tenant isolation was enforced only in Python.** `TenantMiddleware` switched
  `search_path` based on `user.type`, so any raw `DB.statement()`, any
  schema-qualified query and any background job with no tenant bound crossed the
  boundary with nothing in the database to stop it. Isolation is now a
  row-level-security policy the application cannot forget.
- **A driver without isolation used to warn and keep serving.** Multi-tenant
  traffic on SQLite or MySQL shared one set of tables behind a single log line.
  `ScopeTenant` now refuses to run rather than degrade.
- **A pooled connection could carry one tenant's session variable to the next
  borrower.** `Connection.release()` clears `app.current_tenant_id` at checkin
  and discards any connection that cannot be cleared.
- **Policies are inert for a superuser or a `BYPASSRLS` role**, and neither
  `ENABLE` nor `FORCE ROW LEVEL SECURITY` says so — a table reports itself
  protected while returning every tenant's rows to everyone. `ScopeTenant` now
  verifies the connecting role against `pg_roles` and refuses to serve tenant
  traffic it cannot isolate; `dev.py db:audit-rls` reports it and exits non-zero.

## [3.13.0] r00003 — 2026-08-20

### Added

- **Identity Decoupling & Domain Validation Subsystem (`app.Services.Identity`, `DomainValidator`)**:
  - Decoupled core `User` model from rigid organizational constraints, enabling seamless provisioning of test, demo, and administrative accounts.
  - Contextual domain validation with configurable allowed domains and system override domain rules.
- **Authenticated Self-Service Profile & Credential Management**:
  - Implemented endpoints `POST /panel/profile` and `POST /panel/profile/password` in `PanelController`.
  - Upgraded `resources/views/panel/profile.forge.py` with interactive forms for updating personal information and secure password rotation with hash verification.
- **Administrative User Provisioning & Dynamic RBAC Management**:
  - Implemented `store_user`, `assign_role`, `revoke_role`, `assign_group`, and `revoke_group` endpoints guarded by `role:admin`.
  - Upgraded `resources/views/panel/users.forge.py` with inline account provisioning and role/group assignment controls.
- **Identity & RBAC Lifecycle Test Suite (`tests/test_identity_and_rbac_lifecycle.py`)**:
  - 11 comprehensive automated tests validating domain decoupling, self-service profile and password changes, admin user management, and 4-tier AccessResolver authorization.

- **Cloud & Local Storage Subsystem (`craft.storage`, Facade `Storage`)**:
  - **Multi-Disk Engine**: Unified abstraction supporting `local`, `public`, and `s3` disks (AWS S3, MinIO, Cloudflare R2, Google Cloud Storage S3-compatible).
  - **Operations**: `Storage.put()`, `get()`, `get_text()`, `exists()`, `delete()`, `size()`, `mime_type()`, `url()`, `temporary_url()`, and disk switching `Storage.disk('s3')`.
- **High-Throughput Redis Queue Driver (`craft.queue`, Facade `Queue`)**:
  - Full Redis queue backend supporting `push()`, `later()` delayed jobs with zset timestamps, atomic `pop()` claiming, `work()`, and `clear()`.
- **Mail & Notifications Subsystem (`craft.mail`, Facade `Mail`)**:
  - **Fluent Email Dispatch**: `Mail.to().send()`, `Mail.raw()`, and declarative `Mailable` classes with automatic Forge template rendering.
  - **Transports**: `smtp` with TLS/SSL authentication, `log` for local debugging, and `array` for in-memory testing.
  - **Documentation & Tests**: Guides in `documentation/storage.md` and `documentation/mail.md`, with unit tests in `tests/test_storage.py`, `tests/test_mail.py`, and `tests/test_queue_redis.py`.

- **Unified AI SDK & Autonomous Agent Orchestrator (`craft.ai`, Facade `AI`)**:
  - **Provider-Agnostic Engine**: Seamlessly integrates Google Gemini (`gemini-2.0-flash`), OpenAI (`gpt-4o`), Anthropic Claude, Ollama (local LLMs), and a deterministic Mock driver for unit tests.
  - **Text Generation & Chat**: Multi-turn chat completions (`AI.chat()`) and one-shot prompt generations (`AI.generate()`).
  - **Vector Embeddings**: Generates single and batch float embeddings (`AI.embed()`) for semantic search.
  - **Multi-Turn Autonomous Agents**: `AI.agent(tools=[...])` loop executes multi-step reasoning and function calling with automated feedback loop.
- **Native Vector & Semantic Search in ORM & QueryBuilder**:
  - Added `where_vector_similar(column, vector, min_similarity=0.7)` for cosine-similarity semantic filtering directly on Models and QueryBuilder instances.
  - Added `order_by_vector_similarity(column, vector)` to rank records by relevance score (`item.similarity_score`).
- **AI Agents & Model Context Protocol (MCP) Subsystem (`craft.agents`, Facades `Agent` & `MCP`)**:
  - **Declarative Agent Tools (`AgentTool`)**: Structured tool definitions with automatic JSON Schema inference and strict RBAC / Permission authorization guards.
  - **Native MCP Server (`MCPServer`)**: JSON-RPC 2.0 compliant server supporting `initialize`, `tools/list`, and `tools/call` for direct integration with AI coding assistants, autonomous agents, and IDEs.
  - **Documentation & Tests**: Guides in `documentation/ai.md`, `documentation/vector_search.md`, `documentation/agents_mcp.md`, and 13 unit tests in `tests/test_ai_sdk.py`, `tests/test_vector_search.py`, and `tests/test_mcp_agents.py`.
- **Fluent Image & Multimedia Manipulation Subsystem (`craft.media`, Facades `Image` & `Media`)**:
  - **Fluent Image Engine** (`engine/media/image.py`): Chainable image processor backed by Pillow. Supports `resize()`, `scale()`, `crop()` with positional anchors (`center`, `top-left`, `bottom-right`, etc.), `cover()`, `contain()`, `thumbnail()`, `rotate()`, `flip()`, and filters (`greyscale()`, `blur()`, `sharpen()`, `brightness()`, `contrast()`, `invert()`).
  - **Modern Image Compression & WebP/AVIF**: Native export and optimization to `WebP`, `JPEG`, `PNG`, `AVIF`, and `GIF` with configurable quality, metadata stripping (`optimize()`), binary streaming, base64 data URIs, and direct Starlette HTTP `Response` generation.
  - **Alpha Watermarking**: Overlay watermarks with precise anchor alignment, padding, and opacity blending.
  - **Video Metadata & Thumbnails** (`engine/media/video.py`): Extract video resolution, duration, FPS, codecs, and capture video frames as fluent `Image` instances.
  - **Database-Backed Media Tracking**: Added migration `2026_08_19_000001_create_media_table.py` and Model `app/Models/Media.py` supporting polymorphic associations, collections, and JSON conversions.
  - **Documentation & Tests**: Created comprehensive guide in `documentation/media.md` and added 30 unit tests in `tests/test_media_image.py`, `tests/test_media_video.py`, and `tests/test_media_facades.py`.

### Changed

- **Database-First Translation Resolution**: In `engine/support/translation.py`,
  the `translate()` and `__()` helpers now query the dynamic `translations` database
  table as the primary source of truth, falling back to configuration (`lang.{locale}.{key}`)
  only when a database record is absent or the database is uninitialized. This guarantees
  that runtime database translation changes (via admin panel, seeders, or migrations) take
  immediate effect dynamically without requiring code redeployments.
- **Architectural Policy**: Explicitly documented and enforced zero-hardcoding rules across
  `CRAFT_ENGINE.md`, documentation, and agent skills: state, internationalization,
  authorization (RBAC/ABAC), modules, and settings must be database-backed.

## [3.12.0] — 2026-08-17 (r00002)

### Fixed

- **Smart Controller Action Parameter Resolution**: In `engine/http/kernel.py`,
  controller action parameter binding now resolves both named route placeholders
  and ordered positional fallback parameters. This fixes `TypeError: missing required
  positional argument` when controller method parameters (e.g. `posts`, `post`,
  `item`) differed from route parameter names (e.g. `id`), enabling standard REST
  resource routes like `GET /posts/3` to execute seamlessly.
- **`PostController` Action Consistency**: Standardized `PostController.show()`,
  `edit()`, `update()`, and `destroy()` to use `Post.find(id)`, supporting both
  numeric IDs and UUID lookups natively.

### CLI & CRUD Builder


- **Visual & Terminal CRUD Builder Expansion**:
  - **Extended Column Types**: CRUD Builder now supports `json`, `big_integer`,
    `small_integer`, `float`, in addition to `string`, `text`, `integer`,
    `boolean`, `decimal`, `date`, `datetime`.
  - **Dual-Key / Public UUID Integration**: Generated migrations now declare
    `t.uuid_key()` automatically alongside `t.id()`, providing public UUID
    identifiers out-of-the-box for all generated entities.
  - **Dry-Run Mode (`--pretend`)**: CLI command `dev.py make:crud <Entity> --pretend`
    allows previewing all files and routes that would be created without disk writes.
  - **Interactive Terminal Wizard (`--interactive` / `-i`)**: CLI guides
    developers step-by-step to define fields, types, and constraints interactively.
  - **Visual Admin Builder Enhancements (`/admin/crud-builder`)**: Added quick field
    presets toolbar (Name, Title, Description, Price, Active, Metadata, Due Date),
    interactive row reordering (`▲ Up` and `▼ Down` buttons), client-side duplicate
    detection and validation, and migration guidance on completion.

### Security


- **Automatic UUID Resolution in `Model.find()`**: `Model.find(id_val)` now
  automatically resolves models by their public `uuid` column when passed a
  non-digit UUID string, allowing direct lookups like `User.find("uuid-value")`
  without type errors on strictly-typed databases like PostgreSQL.
- **WAF / IDS Firewall Subsystem (`engine/security/firewall.py`)**: Added Web

  Application Firewall with IP whitelist/blacklist, anomaly reputation scoring,
  automatic threat blacklisting (threshold: 100 points), and deep payload pattern
  detection for SQL Injection, Cross-Site Scripting (XSS), Path Traversal, and
  Server-Side Request Forgery (SSRF). Exposed via `Firewall` facade and
  `FirewallMiddleware` (`firewall` route alias).
- **Honeypot & Brute-force Defense Subsystem (`engine/security/honeypot.py`)**:
  Implemented Honeypot service with pre-registered attacker usernames (`admin`,
  `root`, `administrator`, `postgres`, `superuser`, etc.) that immediately trap
  and block malicious login attempts, recording incidents to `auth_audit_logs`
  and `security_events` while assigning 30-minute IP cooldowns via
  `auth_cooldowns` without exposing real user data.
- **Hashed API Token Authentication**: `AuthenticateApiToken` now verifies
  SHA-256 hashed API tokens against the database with backward compatibility for
  unhashed tokens, mitigating token exposure risks in case of database leaks.
- **PostgreSQL Connection SSL Mode Support**: `_connect_postgres()` in
  `engine/orm/connection.py` now supports the `sslmode` parameter (e.g.,
  `require`, `verify-full`, `prefer`) via database connection configuration.
- **Configurable Security Headers**: `SecurityHeaders` middleware now applies
  `X-XSS-Protection: 1; mode=block` by default and dynamically supports custom
  Content-Security-Policy (CSP) and HSTS (`Strict-Transport-Security`)
  declarations from configuration.


- **The panel showed an ordinary account how access is configured.** Its first
  revision gave every signed-in visitor a "My access" page listing permission
  slugs, the path each grant arrives by (`role`, `group-role`, `group`) and the
  raw ABAC conditions, plus role/group/permission counts on the dashboard and
  the account's `type` and `is_admin` on the profile. That is the
  installation's security configuration, not the visitor's personal data:
  knowing which roles exist and which of them you hold is a map for probing the
  system. The page is now the **access audit** at `role:admin`, the security
  rows on the profile are administrator-only, and the dashboard shows an
  ordinary account only what it wrote and when it joined. Reported from a
  running installation — the same way the `/admin` hole was.
- **`GET /admin` was readable by any authenticated user.** The dashboard lists
  every user, every administrator and every tenant in the installation, and it
  carried the `auth` alias alone — so the seeded `user@craft.local`, or any
  account that could log in, read the whole directory. Every *other* admin
  route already required `role:admin`; this one was missed. Reported from a
  running installation, not found by a test, which is the part worth keeping in
  mind. Three changes:
  - the route now declares `auth` + `role:admin`;
  - the controller repeats the check itself
    (`Gate.authorize("access-admin-dashboard")`, defined in
    `AuthServiceProvider` as `is_admin` OR the `admin` role) — two independent
    controls, because with the data this action returns, one forgotten alias
    must not be the only thing between an ordinary user and the installation;
  - `tests/test_admin_authorization.py` reproduces the report **and** adds a
    structural guard: every route under `/admin` must declare an authorizing
    alias (`role:`, `permission:`, `group:`, `can:`), not just `auth`. The page
    was not left open by a wrong decision — it was left open by a declaration
    nobody compared against its neighbours, and comparison by eye is not a
    control. A second test asserts each admin page still renders **200** for an
    administrator, since "locked down" and "broken" look identical from outside.
- **`has_role()` and `has_permission()` could not see group grants**, because
  they queried `role_user`/`permission_role` directly. With groups added, that
  would have meant membership looking correct in the admin UI while the route
  middleware refused. Both now delegate to the single resolver.
- **`AuthenticateApiToken` never rejected anything.** It resolved a user when a
  bearer token happened to match and called the next handler regardless, so
  every route carrying the `api` alias — including `routes/api.py`, whose own
  comment promised "writes require a valid API token", and every write route
  the CRUD builder generates — accepted anonymous callers. It now raises
  `AuthorizationException` for a missing *or* invalid token, with an identical
  response for both so probing cannot confirm which tokens exist. Covered by
  `tests/test_api_token_middleware.py`, which had no runtime counterpart before
  — the reason the gap survived.
- **The `api` guard had no column behind it.** `config/auth.py` declares
  `guards.api.token_name = "api_token"` and the middleware queried it, but no
  migration ever created it, so bearer-token authentication could not have
  succeeded for anyone. Added by
  `2026_08_10_000001_add_api_token_to_users.py`, nullable with a unique index.
- **`/admin/crud-builder` was protected by `auth` alone.** The builder writes
  real `.py` files into `app/` and `database/migrations/` and rewrites
  `routes/api.py` and `routes/web.py`, so any registered user — not just an
  admin — could execute code on the host. Now carries `role:admin`, matching
  the rest of the admin surface.
- **`make policy` generated a policy that authorized everyone.** Every ability
  returned `True`, including for `user=None`, so registering a generated policy
  produced a file that looked like protection while granting universal access.
  The stub now fails closed.
- **Aggregate columns bypassed the identifier allowlist.** `count`, `sum`,
  `avg`, `max` and `min` interpolated their column argument straight into SQL —
  the one hole in the defence every other clause in the query builder applies,
  and `count(request.input("col"))` is an ordinary-looking way to reach it.
- **`unique` and `exists` failed open.** Both wrapped their query in
  `except Exception: return`, so *any* database error made the rule pass: a
  typo'd table (`unique:userz,email`), an incompatible column type or a
  connection blip all validated cleanly and let the duplicate through. Only
  "no application booted" is tolerated now; a real query failure surfaces.
  Their table and column arguments also go through the identifier allowlist,
  since both are interpolated into SQL.

### Fixed

- **The Docker images still copied `services/`,** the package directory that
  the `engine/` rename replaced, so `docker compose up --build` failed outright
  on both `Dockerfile` and `Dockerfile.prod` — the dev container that was still
  running had simply never been rebuilt, and its bind mount pointed at the old
  workspace path. Both now copy `engine/`, and `docker-compose.yml` no longer
  claims the directory is called "craft framework".
- **`engine/orm/__init__.py` was empty** — the one subpackage in the engine
  that exported nothing, so `from craft.orm import Model`, exactly as
  `documentation/orm.md` teaches it, raised ImportError. It now exports `Model`,
  `QueryBuilder`, `DatabaseManager`, `Connection`, `Row`, `SoftDeletes`, the
  four relation classes and the four ORM exceptions, with a test asserting that
  every name in `__all__` resolves.
- **A route declared with `.module(...)` cost a SELECT per request.** The
  kernel queried the `modules` table inline on every hit, with no cache, and
  duplicated logic that already lived in `ModuleManager`. It now asks the
  manager, which caches state for `cache_ttl` (5s) and drops the entry
  immediately on `enable()`/`disable()`. `ModuleManager.state()` is new and
  returns `None` for a module it has never heard of — distinct from `False`,
  so the router can still fall back to `modules.<slug>.enabled` in config
  instead of 404ing an unregistered module. Query counts are asserted in
  `tests/test_module_state_cache.py`; write to the `modules` table behind the
  manager's back and you must call `forget_cached_state()`.
- **`PostController.show()`/`update()` returned a bare `PostResource`** while
  `store()` returned `.response()` — the same controller shaping its JSON two
  different ways. Both now go through `.response()`.
- **Three config keys nothing ever read.** `APP_URL` is now honoured by the new
  `Router.absolute_url_for()`; `auth.defaults.guard` and each guard's
  `provider` key now actually select the user model, via the new
  `AuthManager.provider_name()` (the model was previously read straight from
  `auth.providers.users.model`, so both keys were decorative). `APP_TIMEZONE`
  and `auth.password_timeout` were **removed** rather than left as knobs with
  no wiring: Craft writes every timestamp in UTC by design, and there is no
  confirm-password window to time out. Covered in
  `tests/test_placebo_regressions.py`.
- **`Auth.once()` authenticated nobody.** It was `validate(...) is not None`,
  so after a `True` return `Auth.check()` was still False, `Auth.user()` still
  None and `@auth` still saw a guest — `validate()` under a name that promises
  a login. It now sets the user for the current request while still writing
  nothing to the session, which is what "without persisting" means. The test
  covering it had asserted `guest() is True` afterwards, pinning the bug
  rather than the contract.
- **`@yield("title", "default")` leaked its quotes into the HTML.** The default
  was emitted raw, so the literal rendered as `"default"`, quotes included —
  `@section` already unwrapped literals correctly; `@yield` did not.
- **HTML form method spoofing never worked.** The framework emitted the hidden
  `_method` field from two places — the `@method("PUT")` view directive and
  every edit/delete form the CRUD builder generates — and read it back from
  none. Browsers only send GET and POST, so a `Route.resource()` update (PUT)
  or destroy (DELETE) received a POST and returned 405: the directive produced
  decorative HTML and generated admin forms did not work at all. The override
  is now applied at the ASGI layer, before Starlette matches on the method,
  since anything later is already too late. Only PUT/PATCH/DELETE may be
  spoofed — allowing `GET` would turn a write into a read and skip CSRF
  verification — and only for form encodings, so a JSON API cannot have its
  verb rewritten by a field that happens to carry that name.
- **`url_for()` invented URLs for routes that do not exist.** An unknown name
  returned the literal path `/{name}`, so `route("posts.index")` rendered the
  dead link `/posts.index`; the template helper then caught the failure and
  returned `"/"`, turning a typo into a link to the homepage. Both now raise.
- **`craft.support.view()` turned every template error into a fake success.**
  It caught all exceptions and returned `"View {name} rendered"` with HTTP
  200, so a missing template, a syntax error or an undefined variable produced
  a page that looked like it had worked. The same placebo had already been
  removed from `Controller.view` and the view engine; this copy was missed,
  and `DocsController` routed through it. Errors now reach the exception
  handler.
- **`Model.roles()/permissions()/has_role()/has_permission()` lived on the base
  model**, hardwired to `role_user.user_id` — so `Post.find(1).roles()`
  returned the roles of *user* 1: wrong data, no error. They moved to the
  models they describe (`User`, `Role`), which also removes the framework's
  import of `app.Models.Role`.
- **`Schema.table()` silently discarded indexes and constraints.** Only the
  `ADD COLUMN` was compiled, so `.indexed()`, `index()` and `unique_index()`
  were accepted on an existing table and never created — the migration read
  correctly and the index did not exist.
- **`enum()` enforced nothing.** It emitted a plain `VARCHAR(255)` and stored
  the allowed values in `Column.comment`, which no grammar reads. It now
  compiles a `CHECK (col IN (…))` constraint, portable across all three
  supported drivers.
- **A failed column probe was cached forever.** `table_has_column()` memoised
  an exception as "this table has no columns" for the life of the process,
  which quietly switched off every column-conditional feature — including the
  public UUID the ORM advertises, whose backfill simply stopped.
- **`SoftDeletes` listed after `Model` now raises instead of silently hard
  deleting.** The base order was a documentation footnote, but getting it
  wrong makes `delete()` destroy rows through a call the developer believes is
  reversible.
- **`SettingManager.set()` reported nothing.** It returned `None` whether the
  value was persisted or fell through to an in-memory dict that dies with the
  process; it now returns whether the write landed, and warns when it did not.
- **The admin dashboard rendered healthy with the database down.** Each query
  was wrapped in `except: []`, so an unreachable database produced a dashboard
  reporting zero of everything — indistinguishable from a correct answer.
- **`QueryBuilder` fell back to a default `DatabaseManager()`** when the
  container failed, running queries against a different connection than the
  application's rather than failing.
- **The task scheduler was a placebo.** `schedule` resolved to a nested stub
  class whose `hourly()`/`daily()` returned `self` and which never executed
  anything, while the `Schedule` facade was public and `CRAFT_DESIGN.md`
  documented a full cron-style scheduler. Replaced by a real
  `engine/schedule/` — a cron-expression matcher backing every frequency
  helper (`hourly`, `daily_at`, `every_fifteen_minutes`, `weekdays`, `cron`,
  …), `when`/`skip` constraints, and `without_overlapping()` locking so a task
  slower than its interval cannot stack copies of itself. Run it with
  `dev.py schedule run` from cron, or `dev.py schedule work` in the foreground;
  `dev.py schedule list` shows the registry.
- **Scheduled tasks were never registered.** Nothing called
  `register_console()`, so every task declared in `routes/console.py` was dead
  on arrival — the scheduler could not have run them even once it worked. The
  framework now imports it at boot, logging rather than silencing a broken
  console file.
- **Debug mode never turned on.** `ExceptionHandler` read `app.debug` and
  `dev.py about` read `app.env`/`app.debug`, but the config repository keys
  entries by the module attribute name, so those never resolved and both
  silently reported the default. They now read `app.APP_DEBUG` / `app.APP_ENV`,
  the names the kernel already used correctly.
- **The cache degraded silently.** An unrecognised `CACHE_DRIVER` (the shipped
  default, `memory`, was not one of the two names the resolver knew) and an
  unreachable Redis both fell back to an in-memory store with no signal —
  making rate limiting per-process, so a brute-force limit quietly multiplied
  by the worker count. `memory`/`array` are now recognised explicitly, and both
  fallbacks warn.
- **`dev.py schedule work` skipped the first minute**, sleeping before its
  first evaluation instead of after.

### Added

- **A control panel at `/panel`, for every signed-in account.** The skeleton
  had an icon-only rail whose labels appeared on hover — over the page content,
  which the expanded rail covered — and a menu hardcoded in the template with
  no relation to the visitor. Hardcoding it made the navigation a second,
  silent authorization system, which is how an ordinary account came to be
  shown a Dashboard button that led straight to a 403.
  - **`engine/support/navigation.py`** (new, bound as `nav`, `Nav` facade) is
    the menu as data. Each item declares the same guard as the route it points
    at — `permission`, `role`, `group`, `ability`, `module`, or a predicate —
    and `Nav.for_user(user, path)` returns only what that visitor may reach.
    Sections with no visible items disappear, so nobody stares at an empty
    "System" heading. Any error while evaluating an item hides it: a menu is
    not the place to be optimistic.
  - The shell (`layouts/panel.forge.py`) has a labelled sidebar, offsets the
    content by its width instead of covering it, and slides in as a drawer on
    small screens with no JavaScript.
  - Eight pages: dashboard, profile, posts, users, access audit, modules
    (enable/disable, POST + CSRF), plugins, and an "about this install" read
    from the running application rather than a config file.
  - The panel is **not** an admin area — an ordinary account gets a real
    workspace, an administrator sees the same shell with more sections in it.
    Building two panels is how the two drift apart.
  - Fixed while looking at the running page, not by a test: `/panel` lit up
    alongside `/panel/access`, because per-item prefix matching cannot express
    "closest wins". Exactly one item is active now, chosen across the whole menu.
- **One panel, not two.** `/admin` rendered its own dashboard inside
  `layouts.app`, whose sidebar is the hover-expanding icon rail that covers the
  page underneath — the very problem the panel was built to fix, still visible
  on the admin side. It now redirects into `/panel` (the guard still runs
  first, so this is no way around it), and the roles, permissions and groups
  screens render inside the panel shell through a shared `PanelPage` mixin.
  Two dashboards is how the two drift apart: one gains a section, the other
  keeps an old guard, and eventually one of them is wrong.
- **Total control of the running installation**, all admin-only, all read from
  the live application rather than a config file that may not be the one in
  effect:
  - **Routes** — every registered route with the middleware guarding it,
    including anything registered at runtime (the CRUD builder does). The route
    table *is* the attack surface; this is it in one screen.
  - **Database** — driver, connection pool (`open`/`idle` against `pool_size`)
    and every table with its row count. A count that could not be read shows
    "—", never 0.
  - **Cache** — what the config asks for *and* which store actually resolved,
    because "configured redis, running array" otherwise goes unnoticed until a
    second worker appears. Plus a flush, POST with CSRF.
  - **Queue** — waiting and retried jobs from the `jobs` table, and the last 20.
  - **Scheduler** — registered tasks and their cron expressions.
  - **Logs** — the last 100 `system_logs` rows, columns taken from the data.
  - **Tenants** — with a banner stating plainly when the driver cannot isolate
    schemas, so the list never implies an isolation that is not there.
- **Groups and attribute-based access control (ABAC).** Authorization could
  previously say only *who you are*: a user held roles, and roles held
  permissions. Two things real systems need were missing.
  - **Groups** (`groups`, `group_user`, `group_role`, `permission_group`) grant
    access to a team rather than one person at a time: a group carries roles
    and/or permissions and every member inherits them, so onboarding is one
    membership row. Plus `permission_user` for the case every system hits
    eventually — one person, one extra permission, where inventing a
    single-member role is worse than recording it honestly.
  - **Conditions** — every grant table carries a nullable `conditions` column
    holding a small JSON object evaluated against the record being acted upon:
    `{"user_id": "@user.id"}` for *only your own*, `{"amount": {"lte": 10000}}`
    for an approval ceiling. `@user.<attr>` resolves to the acting user.
    Operators: eq, ne, in, not_in, gt, gte, lt, lte, is_null, contains. `NULL`
    means unconditional, so every existing grant keeps working untouched.
  - **`engine/auth/access.py`** is now the single place that answers "can this
    user do this?", unioning all four grant paths (direct, role, group→role,
    group) in one query. `has_role`, `has_permission` and the new `can()` on
    `User` delegate to it; the Gate consults it after closures and policies and
    passes the resource through, so a conditional grant is evaluated rather
    than treated as unconditional.
  - Three deliberate behaviours, each failing safe: `has_permission()` (no
    resource) counts **unconditional grants only**, since answering True for a
    narrowed grant would widen it; a **malformed condition denies** and is
    logged, so a typo cannot become an open grant; and `{}` is not `NULL` —
    someone wrote it and meant something, so it denies.
  - Exposed everywhere it needs to be: the `group:<slug>` route middleware, an
    `Access` facade (`roles`, `groups`, `permissions`, `explain`), the
    `/admin/groups` screen (membership, role grants, permission grants with
    conditions shown verbatim), and CLI — `group create|list|add-user|
    remove-user|grant-role|grant`, `user grant --conditions`, and
    `user access <email>`, which prints why each permission reaches someone.
  - The seeder ships a working example rather than empty tables: a
    `content-team` group granting the `user` role, and one conditional grant
    (the team may `publish-post`, but only their own) so the feature is visible
    and not merely documented.
  - `documentation/authorization.md` rewritten around all of it.
- **Every Forge view now carries a documentation header** — what the page is,
  which controller and route render it, what guards it, and the context
  variables it expects. 16 of 16.
- **`CRAFT_ENGINE.md`** — the framework's own overview, written for whoever (or
  whatever) picks this repository up cold: what each engine subsystem provides,
  the build loop for a feature, and how the same codebase carries an
  application through four stages — a single-machine blog, a real product with
  roles and background work, a concurrent multi-worker deployment, and
  schema-per-tenant multi-tenancy. It carries an explicit **"what does not
  exist yet"** section (storage/S3, mail, API key manager, Redis queue driver,
  broadcasting, nested eager loading, remember-me, session encryption), because
  an agent that assumes those exist writes code that cannot work. Linked from
  both READMEs and the documentation index.
- **The framework serves requests in parallel.** Throughput was ~27 req/s
  whether 1 client or 50 were connected — the signature of a process handling
  one request at a time — and p95 latency at 50 clients was 1.9s. It is now
  ~115 req/s from 10 clients up, with p95 at 0.57s and no failed requests.
  Measured on the sample app with `tools/loadtest.py` (new, standard library
  only), before and after, by toggling only the offload. Three changes, in the
  order the backlog required, because doing them in any other order corrupts
  state under real load:
  1. **A bounded connection pool** (`engine/orm/connection.py`). A `Connection`
     held one raw DB-API handle plus mutable per-request state, so two threads
     would have shared a cursor. A thread now checks a connection out on first
     use and returns it at the end of the request; `pool_size` (default 10) and
     `pool_timeout` (default 30s) are per-connection config. Exhaustion raises
     an error naming the setting instead of hanging. Per-thread connections
     *without* the release boundary were tried first and are not a pool — they
     accumulate one per thread until PostgreSQL answers "too many clients
     already", which is exactly what the suite did.
  2. **Per-request state moved off the singletons.** Transaction depth and the
     tenant `search_path` now belong to the borrowed connection, and
     `AuthManager`'s current user/session are thread-local. Both were
     process-wide, which under concurrency is not a race but a correctness
     hole: one tenant's request could repoint the schema mid-query of another's,
     and one visitor's identity could be read on another visitor's request.
     `DatabaseManager.release()` also clears the tenant, so a recycled thread
     never inherits the previous request's tenant.
  3. **The kernel offloads to the thread pool** (`run_in_threadpool`), and
     releases the connection inside the worker thread that borrowed it.
  Covered by `tests/test_connection_concurrency.py` — real threads asserting
  session isolation, transaction-depth isolation, tenant-schema isolation on
  live PostgreSQL, identity isolation, pool reuse, bounded growth, exhaustion
  and rollback of an abandoned transaction on release.
- **`dev.py serve --workers N`** for multiple processes. It refuses to pretend:
  `--workers` with `--reload` is impossible in uvicorn, so it says so and
  serves with one instead of silently ignoring the flag.
- **`ruff check .` now fails the build.** CI ran it as `ruff check . || true`,
  the same placebo pattern applied to the pipeline: the lint could never
  reprove anything. The nine findings it had been hiding are fixed (six
  `raise ... from None` in the CLI, an unused loop variable, a constant
  `getattr`, and a `zip()` without `strict=`), so the guard is now on with a
  clean base. The `zip(..., strict=True)` in `engine/orm/connection.py` is
  deliberate: a row whose arity disagrees with `cursor.description` is a driver
  bug, and pairing them off silently would drop columns. Validated on SQLite
  and on real PostgreSQL.
- **`documentation/orm.md` gained the eager-loading and soft-deletes sections**
  the index had been promising, plus many-to-many. `resources.md:133` already
  linked to `orm.md#eager-loading`, which did not exist. The sections state the
  current limit explicitly (one level; no nested `with_("posts.comments")`, no
  `collection.load()`, no `with_count()`) and document the `SoftDeletes` MRO
  trap that now raises `TypeError`. `crud-builder.md` was an orphan — it is in
  the index now, and the broken `orm.md#query-builder` anchor was corrected.
- **The event bus and the plugin hook system now actually run.** Both were
  fully implemented and unit-tested, but nothing in the framework ever emitted
  an event or triggered a hook — in a running application both subsystems were
  inert. Three things closed the gap:
  - `engine/events/lifecycle.py` (new) defines the framework's own events —
    `model.created` / `model.updated` / `model.deleted`, and `auth.login` /
    `auth.failed` / `auth.logout` — plus a `fire()` helper that no-ops when no
    container is bound (models are used in unit tests with no booted app) and
    logs rather than raises when a listener misbehaves, so a third-party
    listener cannot turn a successful INSERT into a request error.
  - `engine/orm/model.py` and `engine/auth/manager.py` emit them at the write
    and authentication points. `UserLoginFailed` carries the identifier only —
    never the submitted password, which would otherwise reach every listener
    and plugin and anything they log.
  - `PluginManager.bridge_events()` registers the manager as a *wildcard*
    listener and forwards each event to hooks registered under its `name`, so
    there is one emission point per lifecycle event rather than two dispatch
    paths to keep in sync. `PluginManager.load_enabled()` imports enabled
    plugins and calls their `register(app)` — previously nothing ever imported
    a plugin's code, so no hook could ever be added.
- **Bundled `audit-log` plugin** (`plugins/audit-log/`) — the first plugin with
  real logic, writing an audit trail of model writes and authentication to
  `system_logs`. It skips its own table: auditing `system_logs` would make each
  write emit `model.created`, which writes another row, forever. Any plugin
  persisting from inside a model hook needs the same guard.

### Changed

- **The framework package was renamed `services/` → `engine/`.** The public
  import alias is unchanged: application code still writes `from craft.…`,
  which `engine/__init__.py` installs via its meta path finder. Only the
  on-disk directory moved. Every internal import, `pyproject.toml`
  (`dev = "engine.cli.app:main"`, packaging and ruff includes), the CI
  coverage target (`--cov=engine`), the entrypoints (`dev.py`,
  `bootstrap/app.py`, `public/index.py`, `config/app.py`), the test suite,
  and the documentation were updated to match. The rename had left the tree
  in a non-booting state — files were moved but no import followed them.

### Fixed

- **The 3 seeded demo accounts were all created as identical non-admin
  users.** `UserSeeder` created them through `Model.create()`, which enforces
  `fillable`; since `type` and `is_admin` are deliberately excluded from
  `User.fillable` (so request input can never escalate privileges), both
  columns were silently dropped. `admin@craft.local` had `is_admin = False`
  and `tenant@craft.local` had `type = "user"`, which meant the admin surface
  and `TenantMiddleware` never saw the accounts the docs describe as the
  framework's official demo ladder. The seeder now uses the trusted
  `force_create` path, and password hashing moved from `User.create` to
  `User.force_create` so *every* insert path hashes rather than only the
  mass-assignment-filtered one. Regression test asserts `type`, `is_admin`,
  and that the documented password authenticates
  (`tests/test_rbac.py::test_demo_users_get_their_privilege_columns`) — the
  previous test asserted roles only, which is why this went unnoticed.

- **Hero background was boxed inside a box, still not full width.**
  `layouts/app.forge.py` wraps every public page's content in `max-w-7xl
  mx-auto` (1280px); `.hero-section` then had its own nested `max-width:
  1120px` on top of that, so the hero's gradient background never reached
  the real viewport edges — visibly boxed with large empty gutters on wide
  screens, which is what the previous "two columns" fix alone didn't
  address. Split the hero into two layers, matching the pattern every
  other section on the page already uses (a full-width band +
  `.section-container` inside it): `.hero-section` now breaks out of its
  ancestor's max-width with the standard full-bleed technique
  (`margin-inline: calc(50% - 50vw)`) so its background spans the true
  viewport width; the actual two-column content grid moved to a new
  `.hero-inner` (`resources/views/home.forge.py`), capped at a readable
  1120px and centered, same as before. The full-bleed technique's known
  side effect — `vw` units include the scrollbar's width on most browsers,
  which produced a few pixels of horizontal overflow — is clamped with
  `overflow-x: hidden` on `body` (the standard fix, not a workaround).
  Verified live at 1920px (background reaches both edges, content stays
  readable), 1440px, and 390px (unchanged mobile stack).
- **Hero section on the landing page was never actually two columns.**
  `.hero-section` was `flex-direction: column` unconditionally — copy and
  the code preview always stacked, centered, at every viewport width, which
  is what made the page feel like it never used the screen's width. Now a
  real CSS grid: single column below 1024px (unchanged mobile behavior),
  two columns (copy left, code preview right) at 1024px+. Verified live
  with a headless browser at 1440px (two columns), 390px (stacked), and
  with `prefers-color-scheme: dark` (surfaced an unrelated bug, next entry).
- **Landing page was unreadable on a system with dark mode on.**
  `craft-components.css`'s `--bg-body`/`--bg-section` aliased to the
  semantic `--craft-bg`/`--craft-surface` tokens, which correctly flip dark
  under `prefers-color-scheme: dark` (that's how `craft-theme.css` is
  designed to work) — but every text color on the landing page
  (`--slate-700/800/900`) is a literal, never-swapping step chosen
  assuming a light background. Background went dark, text didn't: several
  sections rendered dark text on a near-black ground, unreadable. Pinned
  `--bg-body`/`--bg-section` to the literal light slate steps instead — the
  landing page now commits to a single light presentation on purpose,
  rather than a half-finished dark mode with broken contrast. Verified live
  with `prefers-color-scheme: dark` forced on: background now stays light
  end to end.
- **The earlier "unified CSS design tokens" fix (this file, same session,
  under "Changed") edited the wrong file.** `public/css/app.css` — which
  that fix touched — was never linked from any view; the landing page
  actually loads `assets/css/craft-components.css`, an near-identical but
  separate copy. The dead file is now deleted; today's hero fix (and any
  future landing-page CSS change) targets `craft-components.css`, the one
  actually served. A lesson for next time: a CSS/UI fix isn't verified by
  `pytest` passing — none of these tests render a page — it needs an actual
  browser check, which is what caught this.

### Added

- **Login page shows the 3 demo accounts, gated by `APP_DEBUG`.**
  `resources/views/auth/login.forge.py` now renders a small credentials
  table under the form when `config("app.APP_DEBUG")` is true — never in a
  production build. Discoverable without opening the README.
- `documentation/authorization.md` gained a **Recipes** section: protect a
  route by role/permission, check inside a controller or a Forge view,
  create a brand-new role end to end via the CLI — worked examples on top
  of the existing reference documentation.
- New `.agents/docs/resumo-executivo-2026-08-07.md` — a session-level
  executive summary (workspace reorg, English-only pass, plugin management,
  CRUD builder + its admin UI, the release cut, the benchmark, the fixes
  that followed it, and RBAC) for anyone — human or agent — resuming this
  work without re-reading every commit.
- **Functional RBAC**, not just a data model. `roles`/`permissions` tables
  existed before but had no enforcement layer — now: `Model.has_role(slug)`
  (mirroring the existing `has_permission`), a third fallback tier on
  `GateManager.allows()` (ability closure → policy → `user.has_permission()`
  → deny by default), `RequireRole`/`RequirePermission` middleware with
  parameterized route-middleware aliases (`role:admin`, `permission:manage-
  users` — `resolve_route_middleware` now splits `alias:param` and injects
  the parameter into the middleware's constructor), CLI (`role:list/create/
  grant`, `permission:list/create`, `user:assign-role`), and a minimal admin
  UI at `/admin/roles`/`/admin/permissions` (behind `role:admin` — the first
  real usage of the new middleware). Documented in new
  `documentation/authorization.md`.
- **The 3 seeded demo accounts are now the framework's official demo
  credentials**, documented in `README.md`: `user@craft.local` (role
  `user`), `tenant@craft.local` (role `tenant-manager`, new — was
  previously seeded with **zero roles**, a real gap; also drives
  `TenantMiddleware`'s per-schema isolation), `admin@craft.local` (role
  `admin`, `is_admin=True`). All three password `craft`. The 3-tier ladder
  (`user` → `tenant-manager` → `admin`) is intentional — the middle tier now
  demonstrates elevated-but-not-full-admin access via `manage-users`.

### Fixed

- `Kernel.resolve_route_middleware`: a bare parameterized alias used
  without its parameter (e.g. `"role"` instead of `"role:admin"`) raised a
  raw `TypeError` from the middleware's constructor instead of the
  intended, actionable `KeyError` — now caught and re-raised with a message
  telling the caller to use `alias:value`.
- **Cross-file test pollution**: `test_ai_native_subsystems`
  (`tests/test_framework.py`) replaced the shared `modules`/`translations`
  tables with reduced ad-hoc schemas to test DB-driven behavior, and never
  restored them — since the test database is session-scoped, every test
  file running after it (alphabetically, before `test_subsystems_
  persistence.py`'s own unrelated workaround kicked in) saw the broken
  schema. Surfaced by the new `test_rbac.py` failing only as part of the
  full suite, never in isolation — exactly the class of bug `CONTRIBUTING.md`
  asks every test file to be immune to. Fixed at the source: the test now
  restores both tables to their real migrated shape in a `finally` block.
- `app/Http/Middleware/TenantMiddleware.py`'s docstring had a broken,
  machine-specific `file:///d:/data/www/craft/...` doc link — fixed to a
  normal relative reference, matching every other file's `References:`
  style.

### Added

- **CRUD builder now generates a real admin UI by default**, not just a JSON
  API — closing the gap flagged in `.agents/docs/benchmark-2026-08-07.md` §5
  ("Django gives a free admin list+edit UI from a model; Craft only gave
  JSON"). `make crud <Entity>` now also generates: a list view
  (`resources/views/admin/<slug>/index.forge.py`, paginated, with the same
  empty-state pattern `posts/index.forge.py` uses), a create/edit form
  (`admin/<slug>/{create,edit}.forge.py`, one input per field typed to match
  the field's DDL type, CSRF, validation errors + `old()`-preserved input on
  failure — same redisplay pattern the posts fix added), and a dedicated
  HTML controller (`app/Http/Controllers/Admin/<Entity>AdminController.py`)
  registered under `/admin/<slug>` behind `auth` middleware in `routes/web.py`
  — separate from, and non-colliding with, the existing JSON API controller
  and route in `routes/api.py`. Both can coexist for the same entity.

### Security

- CRUD-builder-generated write routes (`store`/`update`/`destroy`) had no
  authentication or authorization at all — `write_middleware="api"` alone
  never rejects a missing/invalid token (`AuthenticateApiToken` only
  resolves a user if present, it doesn't gate). Generated routes now use
  `write_middleware=["api", "auth"]`, and the generated `FormRequest.
  authorize()` checks for an authenticated user instead of always returning
  `True`. Anyone who ran `make crud` before this fix has a public
  read/write/delete API for that entity — regenerate or add auth manually.
- Mass-assignment protection was inverted: an undeclared/empty `fillable`
  meant *no* filtering, not full protection. `Model.create()`/
  `update_attributes()` now fail closed — nothing is mass-assignable unless
  `fillable` lists it or the model opts out with `guarded = False`.
- Added `SecurityHeaders` middleware (`X-Content-Type-Options: nosniff`,
  `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`),
  registered first in the default `bootstrap/app.py` stack. HSTS/CSP left
  opt-in — they need per-app tuning.
- `APP_KEY` empty in `APP_ENV=production` now fails startup loudly instead
  of silently falling back to a per-process ephemeral signing key (which
  broke sessions across restarts/workers without ever surfacing as an
  error). Non-production environments keep the ephemeral fallback.
- `docker-compose.prod.yml` no longer defaults `DB_PASSWORD` to the literal
  `secretpassword` — unset now fails the compose file loudly instead of
  silently shipping a known password. `docker-compose.yml` (dev) unchanged.
- `SECURITY.md`'s "Known gaps" section falsely claimed "no rate limiting on
  authentication endpoints" — `ThrottleRequests` is implemented and wired to
  `/login`/`/register`; corrected.

### Fixed

- `/admin` rendered a hardcoded `<h1>Admin Dashboard</h1>` instead of the
  real, styled `admin.dashboard` template that already existed in the repo.
  `HomeController.admin()` now fetches tenants/users and renders it.
- The demo blog (`PostController.store`/`update`) let a validation failure
  fall through to the generic exception handler, losing all typed input and
  showing an unstyled error fragment. Now redisplays the form with errors
  and preserved input, via a newly-wired `_old_input` session flash (the
  `old()` view helper existed but nothing populated it).
- CRUD-builder form lost all entered field rows on a server-side validation
  failure (only the entity name was preserved) and its dynamically-added
  field-row inputs had no `<label>` elements. Both fixed.
- `paginate()` had no maximum `per_page` — `?per_page=999999` was honored
  as-is. Capped to 100.
- `.agents/skills/framework/craft-development/SKILL.md` still claimed the ORM
  "wraps SQLAlchemy 2.0 Core" — missed by the earlier documentation audit
  because it lives outside `data/`. It's a custom query builder over
  `sqlite3`/`psycopg2`/`PyMySQL`; no SQLAlchemy, no Pydantic.

### Changed

- CI now matches what `CONTRIBUTING.md` already asked of a human: the
  suite runs against Python 3.11/3.12/3.13 (matrix) **and** against a real
  PostgreSQL service container, not SQLite only. Added `ruff check .`
  (non-blocking for now) and coverage reporting (`pytest-cov`,
  `--cov=services --cov-report=term-missing`) to CI output.
- `Dockerfile.prod` had stale "Codepy" branding (`addgroup/adduser codepy`)
  left over from before the framework's rename — now `dev`, matching
  `documentation/deployment.md`. Its `CMD` now runs `python dev.py migrate`
  (non-destructive) before starting gunicorn, since the prior boot sequence
  would serve against an unmigrated schema on a fresh deploy.
- `public/css/app.css`'s design tokens now alias the canonical `--craft-*`
  custom properties from `craft-theme.css` instead of redeclaring a
  near-duplicate palette — was a real footgun for anyone re-theming the app.
  `posts/show.forge.py`'s orphaned unstyled classes replaced with the
  utility classes the rest of `posts/*.forge.py` already uses.
- `.agents/docs/dx_and_ai_learning_curve.md` referenced a `.ai/` directory
  that doesn't exist (it's `.agents/`) and had a malformed comparison table
  with orphaned placeholder cells — fixed the path references, replaced the
  table with an accurate prose summary.

### Added

- `ruff` and `pytest-cov` added to the `[dev]` extra in `pyproject.toml`,
  with a deliberately small starting lint ruleset scoped to `services/`
  only (`E9`, `F`, `B`) — widen incrementally rather than false-starting a
  full-codebase style pass in one go.

### Not fixed — deliberately deferred

- **The concurrency ceiling measured in `.agents/docs/benchmark-2026-08-07.md`
  §1 is still there.** A real load test showed throughput flat at ~30 req/s
  regardless of concurrency (fully serialized). Root cause: sync dispatch on
  the event loop + a single shared `psycopg2` connection + no multi-worker
  option, and the three have to be fixed together — offloading sync work to
  a thread pool without first fixing the connection would corrupt concurrent
  cursor state. An attempt this session to add connection pooling found the
  fix isn't a local swap: `Connection` conflates the raw driver connection
  with mutable per-request session state (transaction depth, active tenant
  schema), so a real fix needs request-scoped connection lifecycle — new
  work touching `DatabaseManager`, `Connection`, tenant middleware, the
  migrator, and `conftest.py`, not a contained change. Stopped rather than
  ship something that passes tests today and breaks under real concurrency
  tomorrow — exactly the "degrades silently to something plausible" failure
  mode this project has been burned by before. This needs its own dedicated
  fatia with room to get the design right.

- Every change to the framework now requires a `CHANGELOG.md` entry in the
  same commit that makes it (not batched for the release cut) — policy
  documented in `CONTRIBUTING.md` ("Every change gets a CHANGELOG entry") and
  in `.agents/skills/framework/craft-development/SKILL.md` §3, so both human
  contributors and AI agents working in this repo pick it up.
- Codified: all code, orientation comments, and docstrings under `data/` are
  100% English, no exceptions — other languages enter only through the
  translation layer (`resources/lang/catalog.json`, `TranslationSeeder`,
  `__()`). Documented in `.agents/skills/framework/craft-development/SKILL.md`
  §2, with the grep check to run before finishing any change.

### Removed

- Four orphaned Portuguese view files from the already-supposedly-removed
  SoftPax domain, found to still be sitting in the tree: `resources/views/
  access/index.forge.py`, `resources/views/dashboard/index.forge.py`,
  `resources/views/admin/translations/index.forge.py`, and `resources/views/
  layout.py`. None were referenced by any controller, route, or test —
  confirmed via `self.view(...)`/`extends(...)` grep before deleting.

---

## [3.11.0] r00001 — 2026-08-07

First cut release. Everything below this line — the full validation pass
(15 → 627 tests), the security/reliability hardening, the workspace
reorganization into `data/`, plugin management, and the CRUD builder — ships
as `v3.11.0-r00001`.

### 2026-08-07 — Workspace reorganization, plugin management, CRUD builder

The application skeleton moved to `data/` at the workspace root — that
directory is now the single deployable unit and the Docker Compose project
root (`build: .` / `volumes: .:/app` both resolve relative to `data/`), so
editing any file there is live in the running container immediately. Nothing
outside `data/` is copied into the container image.

### Added

- **CRUD builder** — `dev.py make crud <Entity> --fields "name:type[:rule1|
  rule2],..."` generates a migration, model, `FormRequest`, API `Resource`,
  and a controller wired to real ORM calls (not a placeholder scaffold).
  Registers as a JSON API resource in `routes/api.py` via `Route.api_resource`
  (matching the existing `PostController` convention), not in `routes/web.py`,
  which is behind CSRF verification a JSON client can't satisfy. An admin UI
  at `/admin/crud-builder` (behind `auth`, like `/admin`) drives the same
  `services/cli/crud_builder.py:build_crud()`. Generated write routes have no
  authorization by default — see `documentation/crud-builder.md`.
- **Plugin management**, levelled up to match `ModuleManager`: a `plugins`
  table (migration + `app/Models/Plugin.py`), disk discovery from
  `plugins/<slug>/plugin.py`, DB-backed `installed()/is_enabled()/enable()/
  disable()` with the same try-DB/fallback-to-memory behaviour as
  `ModuleManager` (never fakes success), and `sync()` upserts newly
  discovered plugins without re-enabling one an operator disabled. CLI:
  `dev.py plugin:list/enable/disable/sync`.
- Workspace-level `README.md` and skill `.agents/skills/project/
  workspace-architecture/SKILL.md` documenting the `data/`-as-deployable-unit
  contract and the clone-to-new-app procedure, for both humans and AI agents
  bootstrapping a new project from this repository.
- `Category`/`Relations`/`References` orientation header added to 41 core
  files under `services/`, so an AI agent skimming a file understands its
  role before editing it.

### Fixed

- `dev.py`'s `group:subcommand` convenience (`migrate:status` ==
  `migrate status`) used to split **any** colon-containing argument, which
  silently mangled option values like `--fields "name:string:required"`.
  Now only the leading command token is eligible for the split.
- `documentation/orm.md` claimed the ORM wraps SQLAlchemy 2.0 Core — it
  doesn't; it's a custom query builder over `sqlite3`/`psycopg2`/`PyMySQL`.
- `documentation/security.md` still framed session-cookie signing in terms
  that read as PQC-adjacent; clarified as HMAC-SHA256, with `PQC`
  (`services/security/pqc.py`) called out as the separate, opt-in utility it
  actually is.
- `CRAFT_DESIGN.md` (the original design doc) now carries a banner marking
  it as the aspirational target architecture (FastAPI/asyncpg/SQLAlchemy/
  Pydantic) rather than the current implementation, after it kept misleading
  agents that skimmed it for how the framework actually works.
- Residual Portuguese in English-facing files (`README.md`, this file,
  `SECURITY.md`, and five docstrings) translated.
- `services/validation/validator.py` carried a "Laravel semantics" comment —
  removed (naming-restriction violation: this project names no third-party
  framework anywhere).

### Changed

- Suite: 596 → **627 tests** (plugin persistence + discovery, CRUD builder
  file-shape/idempotency/rule-reflection).

---

### 2026-08-07 — Security hardening and fixes

Hardening and bug-fix pass over the validated skeleton. The suite went from
530 to **596 tests**.

### Security

- `WOTS` (`services/security/pqc.py`) rewritten as a Lamport one-time
  signature over SHA-256 — the previous `verify` did not verify anything.
- The exception page now escapes HTML in everything it prints (message,
  stack, context).
- The CSRF token is no longer accepted via query string — only the parsed
  body (`_token`) or the header, so a cross-site link cannot plant the token.
- On the `file` driver, `regenerate()`/`invalidate()` remove the old
  session file from disk.
- Mass-assignment protection: `Model.create()` respects `fillable`;
  `force_create()` is the explicit bypass for trusted internal input.
- The query builder validates identifiers (tables/columns) and uses an
  operator whitelist.
- `APP_DEBUG` now defaults to off (`config/app.py`); the development `.env`
  is what turns it on.
- `X-Forwarded-For` is only honoured when `app.trusted_proxies` is configured.

### Reliability

- The `database` queue driver reserves jobs atomically: `reserved_at` with a
  90s `retry_after`, and `attempts` counted on claim — two workers never
  grab the same job.
- Events accept listeners named by string.
- Cache: `increment` preserves the TTL and `remember()` caches `None`.
- Settings are stored with a JSON type instead of a raw string.
- Validator: an unknown rule now raises instead of silently passing;
  `min`/`max`/`between` measure the numeric value of `integer`/`numeric`
  strings; custom messages accept the `field.rule` form.

### ORM

- `where(column, op, None)` becomes `IS NULL`; `or_where` preserves the
  soft-delete scope.
- `find()` honours a custom `primary_key`.
- Reads inside a transaction use the write connection.
- SQLite opens transactions with `BEGIN IMMEDIATE`; on PostgreSQL, metadata
  queries respect the active schema.
- The migrator ignores files that are not migrations and does not choke on
  a rollback whose file has disappeared.

### Fixes

- `ModuleManager`/`Settings` access rows by column name (dict cursors on
  MySQL/PostgreSQL).
- `PostController`: `edit`/`update` return 404 for a non-existent post.
- Forge directives handle nested parentheses.
- `url_for` URL-encodes values and raises for a missing parameter.
- Async controller actions are awaited (`await`).

### DX

- SQLite is the default database (`config/database.py` + `.env.example`):
  the quickstart runs with no database server — `cp .env.example .env`,
  `key:generate`, `migrate --seed`, `serve`.

---

### Validation pass — from "does not matter" to a green suite

Validation work on the base skeleton, from "does not matter" to 530 green
tests on SQLite, real PostgreSQL, and Python 3.11.

### Added

**Database**

- Multi-driver connection layer (`services/orm/connection.py`): SQLite,
  PostgreSQL and MySQL with the same SQL. `?` and `:name` placeholders are
  translated to each driver's paramstyle.
- Read/write splitting and schema-per-tenant on PostgreSQL
  (`set_tenant_schema`, `ensure_tenant_schema`).
- Migrator with batches, `run/rollback/reset/refresh/fresh/status`, `--step`
  and `--pretend`.
- Schema builder with a fluent `Blueprint` and per-dialect DDL, foreign keys
  and composite indexes. Fluent and keyword styles are interchangeable:
  `t.string("cpf").nullable()` == `t.string("cpf", nullable=True)`.

**`dev` CLI**

- `migrate:*`, `db seed/show/tables/ping/wipe`, `route list`, `queue work`,
  `serve`, `tinker`, `key:generate`, and 12 `make:*` generators.
- Accepts both `migrate:status` and `migrate status`.

**HTTP**

- Session with `cookie` and `file` drivers, both signed with HMAC-SHA256
  using `APP_KEY`. Flash data and a CSRF token included.
- `StartSession`, `VerifyCsrfToken`, `Authenticate`, `RequireAuth`, and
  `AuthenticateApiToken` middleware.
- Per-route middleware resolved by alias (`auth`, `api`, `session`, `csrf`).
- `Request` with the body parsed before the pipeline: `input()`, `only()`,
  `boolean()`, `file()`, `session()`, `user()`, `bearer_token()`.
- Forge view engine with its own directives (`@csrf`, `@auth`, `@guest`,
  `@can`, `@if`, `@foreach`, `@extends`, `@section`, `@yield`, `@include`,
  `@method`) and global helpers (`csrf_field`, `auth`, `config`, `route`,
  `session`, `__`).

**ORM**

- Eager loading via `with_()`: one query per relation instead of N+1.
- `HasOne`, `HasMany`, `BelongsTo` and `BelongsToMany` with
  `attach/detach/sync`.
- Soft deletes with `with_trashed()` / `only_trashed()` / `restore()`.
- Query builder with `or_where`, `where_in`, `where_null`, `where_between`,
  `join`, `group_by`, `having`, `paginate`, and aggregates.

**Authentication and validation**

- `Hash` with bcrypt and a PBKDF2-SHA256 fallback.
- `AuthManager` with a persistent session; login rotates the session id.
- Validator grew from 3 to ~30 rules, including `unique` and `exists`.

**i18n**

- BCP 47 locales with a `pt-BR → pt → en` fallback chain.
- `normalize_locale` canonicalizes `PT-br` → `pt-BR` and `EN` → `en`.
- Four seeded locales: `en`, `pt` (European), `pt-BR`, `es`.
- Placeholders: `__("welcome_{name}", "pt-BR", name="Ana")`.
- `resources/lang/catalog.json` with 75 semantic keys × 4 locales, including
  consent copy aligned to LGPD/GDPR (opt-in, essential cookies exempt from
  consent, explicit revocation).

**Other**

- Cache with array/file/redis stores, TTL, `remember` and `increment`.
- Queue with JSON serialization, retry with backoff, and `available_at`.
- Seeders and factories.
- `.env` loading with `${VAR}` interpolation.
- 530-test suite (up from 15).

### Fixed

**Blockers**

- The package did not import: the core lived in `framework/` while the 83
  internal imports said `services.*`.
- `import craft` resolved to an unrelated third-party CUDA package in
  site-packages. Replaced with a `MetaPathFinder` that maps
  `craft.* → services.*`.
- `.env` was never read — `env()` only saw real OS environment variables.

**Security**

- `Gate.allows()` returned `True` for any unknown permission — fail-open.
  It now denies by default.
- Per-route middleware was ignored by the kernel: `.middleware("auth")` was
  decorative.
- The seeder wrote a password in plain text.
- `Starlette(debug=True)` was hardcoded in the kernel, which would leak
  stack traces in production.
- `Resource` leaked the entire model: the base class read
  `self.resource.to_dict()`, so a subclass defining `to_dict()` — which the
  generator emitted — was ignored and unexposed fields shipped in the
  response.

**Behaviour**

- `Model.create` used `SELECT last_insert_rowid()`, which breaks on
  PostgreSQL.
- Incorrect JOIN in `Model.permissions()` (`pr.role_id` instead of
  `pr.permission_id`).
- `FormRequest.validated()` returned the raw body without validating
  anything, ignoring `rules()` and `authorize()`.
- The view engine never rendered a layout: `@extends("layouts.app")`
  delivered raw dot notation to Jinja, and the error was swallowed by a
  `<div>Rendered view: x</div>` placeholder returning HTTP 200.
- `EventDispatcher.listen(Event, SomeListener)` required a list and raised
  `TypeError`; base-class listeners did not hear subclasses.
- `ModuleManager.enable()/disable()` returned `True` even for a
  non-existent module.
- `PluginManager.trigger_hook()` swallowed a plugin's exception without
  logging anything.
- `FacadeMeta.__getattr__` fabricated any attribute, including dunders,
  resolving the container before boot.
- `Container.__init__` unconditionally claimed the global singleton: a
  second `Application` hijacked the process.
- Middleware was instantiated on every request, recreating the session
  store and its signing key — no cookie ever survived.
- `captcha.py` used `Any` without importing it: it passed on Python 3.14
  (lazy annotations, PEP 649) and broke on 3.11, the declared minimum.
- Migration `framework_dynamic_tables`: `role_user` used `uuid` for
  `user_id`, and `permission_role` was dropped in `down()` but never
  created in `up()`.
- Migration `jobs`: `available_at`/`created_at` as INTEGER receiving an ISO
  string.
- 4xx responses were logged with a full traceback, burying real failures.
- `datetime.utcnow()` deprecated on Python 3.12+.

**Documentation**

- `security.md` claimed session cookies were signed with post-quantum
  encryption and "cannot be read." Both false: the signature is
  HMAC-SHA256 and, on the cookie driver, the payload is readable by the
  client (signed, not encrypted).
- The Captcha API was documented with the wrong signature.

### Changed

- The `pt` locale was Brazilian Portuguese mislabelled as generic
  ("Painel de Controle", "Baixar", "Registrar"). Now `pt` is European
  Portuguese and `pt-BR` is Brazilian, with distinct copy.
- `QueueManager` was fake: it built a payload with hardcoded `"TestJob"`
  and `"999"` keys just to make the test pass. Rewritten with real
  serialization.
- `Captcha.validate` had a hardcoded `and code != "WRONG"`. It now uses
  `secrets.compare_digest` and always clears the code (single-use).
- Containers renamed to `framework` and `framework-db`; the Compose
  project pinned to `name: framework`. The dev database got a named
  volume — it used to live in the container layer and vanish on every
  recreation.
- Trimmed dependencies: `sqlalchemy`, `alembic`, `pydantic`,
  `pydantic-settings` and `click` removed, none of them used. `pytest` and
  `httpx` became the `[dev]` extra.
- `bcrypt` pinned to `<4.1`: above that, passlib breaks (`__about__` was
  removed).
- `pyproject.toml`: the entrypoint is now `craft = services.cli.app:main`.
- The repository is now version-controlled (`git init`).

### Removed

- The SoftPax domain (funeral home/cemetery) from the base skeleton: 16
  migrations, 18 models, 26 controllers and 3 view folders.
- Dead files: `app/main.py` (a parallel FastAPI app), `home_controller.py`,
  `BaseModel.py` (SQLAlchemy models), `services/coreengine/`, and 4 empty
  files with no references.
- The `craft-showcase` (vite) landing page from the root.
- `.agents/.agents/` and `.ai/.agents/`, recursively nested directories.
  The `changelog.md` that lived in the nesting was lost in this cleanup;
  this file restarts from the Git history.

**Open source project**

- **MIT** license (`LICENSE`), © 2026 Antonio Santos.
- Authorship metadata, classifiers and URLs in `pyproject.toml`;
  `__author__`, `__email__`, `__license__` and `__copyright__` in the
  package.
- License header in 134 source files.
- `CONTRIBUTING.md` and `SECURITY.md`, with a production checklist and
  known gaps stated rather than hidden.
- Full documentation in `documentation/`: 17 guides with an index, covering
  installation, configuration, the container, routing, controllers, views,
  validation, migrations, the ORM, security, sessions, cache, queues,
  resources, i18n, testing, and deployment, plus the `dev` reference. The
  130 APIs cited were verified against the code.

### Compatibility notes

- **Python 3.11+**. The suite runs on 3.14 locally and 3.11 in the
  container.
- Soft-delete mixins must come **before** `Model` in the class declaration
  (`class Note(SoftDeletes, Model)`), or the MRO makes `Model` win.
- Applications that relied on `pt` carrying Brazilian text should now ask
  for `pt-BR`. The `pt-BR → pt → en` fallback covers missing keys.
