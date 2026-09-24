# Craft Engine

**What it is, and how an AI builds real applications with it — from a blog to
something running for the whole planet.**

Craft Engine is a batteries-included Python web framework. Its core is the **engine**:
the directory `engine/`, published to your application as the package `craft.*`.
Everything around it — `app/`, `config/`, `routes/`, `database/`, `resources/` —
is the skeleton you copy to start a new application.

```python
from craft.facades import Route, DB, Auth, Cache, Queue, Event, Gate
from craft.orm import Model
```

Version 3.18.0 · **1200+ tests**, green on SQLite and on real PostgreSQL, Python
3.14+ · MIT.

---

## What the engine actually contains

Built **directly on Starlette**. There is no third-party ORM, no third-party
template engine, no migration tool borrowed from elsewhere — the pieces below
are the framework's own code, which is why they behave consistently with each
other.

| Subsystem | What you get |
|---|---|
| `container/` | Service container with autowiring, singletons, providers |
| `http/` | Router, kernel, middleware pipeline, Request/Response, sessions, CSRF |
| `orm/` | Active Record models, query builder, relations, eager loading, soft deletes, **connection pool** |
| `migrations/` | Schema builder + migrator with batches, rollback, `fresh`, `status`, `--pretend` |
| `auth/` | Login, bcrypt hashing, session fixation defence, Gate + Policies (deny by default), and full authorization: roles, groups, permissions and attribute conditions (ABAC) on any grant |
| `validation/` | ~30 rules, `FormRequest` with authorization attached |
| `view/` | Forge template engine — layouts, sections, directives |
| `cache/` | array · file · redis, with `remember()` and TTL |
| `queue/` | sync · database · redis drivers, JSON payloads, delayed tasks, retry with backoff |
| `storage/` | Local & S3-compatible cloud object storage, signed URLs, public disks |
| `mail/` | Fluent email delivery, SMTP with TLS/SSL, Log & Array mailers, Mailable classes |
| `events/` | Dispatcher with framework lifecycle events (model created/updated/deleted, auth login/failed/logout) |
| `schedule/` | Cron-style scheduled tasks with overlap locking |
| `modules/`, `plugins/` | DB-backed feature modules and discoverable plugins with hooks |
| `security/` | WAF / IDS firewall, Honeypot traps, Login audit logs, Brute-force cooldowns, Captcha, PQC, Throttling, Security headers |
| `media/` | Fluent Image manipulation, WebP/AVIF compression, Watermarking, Video metadata & thumbnails, DB media tracking |
| `ai/` | Unified AI SDK (Gemini, OpenAI, Claude, Ollama, Mock), Embeddings, Multi-turn Autonomous Agents |
| `agents/` | Model Context Protocol (MCP) Server, Declarative Agent Tools with RBAC security guards |
| `resources/` | JSON transformers for API output |
| `cli/` | The `dev` console, including 14 generators, full CRUD builder, firewall/security tools |


Three database drivers with one SQL dialect: **SQLite**, **PostgreSQL**,
**MySQL**. `?` and `:name` placeholders are translated per driver, and the
schema builder emits DDL per dialect.

---

## Why this framework suits an AI builder

1. **One obvious place for everything.** A controller goes in
   `app/Http/Controllers/`, a rule set in `app/Http/Requests/`, a policy in
   `app/Policies/`. There is no architectural decision to re-litigate on every
   feature, so the model spends its budget on the problem, not the layout.
2. **Generators emit working code, not stubs.** `dev.py make crud` writes a
   migration, model, form request, resource, JSON API controller, an admin UI
   controller with list/create/edit, and registers the routes.
3. **`tests/` is the executable specification.** 880+ tests describe what the
   framework promises. When documentation and code disagree, the tests settle
   it — and an agent can run them in under a minute.
4. **Failures are loud.** An unknown middleware alias raises at boot. An unknown
   route name raises. A model that mixes in soft deletes in the wrong base order
   raises at import. `Gate` denies unknown abilities. The framework is built so
   that a mistake stops you rather than producing something that looks like it
   worked.
5. **No silent degradation.** This codebase went through sweeps that
   removed placebos — methods that returned a fixed value, config that
   nothing read, exceptions swallowed to fake success. What
   the framework advertises, it does.

---

## 🏛️ Fundamental Architectural Rule: Database-First & Zero Hardcoding

**Craft Engine is built for real production applications, not toy demos. Everything that represents state, authorization, internationalization, or togglable features MUST be stored and resolved from the database.**

Developers and AI agents creating applications with Craft Engine must follow these non-negotiable rules:

1. **Internationalization & Copy (`translations` table)**:
   - All human-facing text must use `__('key')` or `translate('key', locale)`.
   - Never hardcode user strings in templates or controllers.
   - The database (`translations` table) is the **primary dynamic source of truth**. Dynamic translations can be updated in real time via seeders, migrations, or admin panels without code deploys.
2. **Authorization & RBAC/ABAC (`roles`, `permissions`, `groups`, pivots)**:
   - Never hardcode role checks (`if user.id == 1` or `if user.role == 'admin'`).
   - Use `Gate.allows()`, `@can()`, middleware `role:`, `permission:`, `group:`.
   - All grants, relations, and ABAC conditions live in the database.
3. **Feature Toggles & Modules (`modules` table)**:
   - Dynamic features are controlled by the `modules` table (`enabled=True/False`), never static booleans or commented code.
4. **Application Settings (`settings` table)**:
   - Dynamic configurations that administrators can tune live in the `settings` table, with `.env` reserved strictly for environment-level infrastructure credentials.
5. **Dynamic Navigation (`Nav` facade)**:
   - Menus and dashboards are data-driven, filtering items based on dynamic database permissions rather than hardcoded template HTML.

---

## The build loop

```bash
# 0. Once
cp .env.example .env && python dev.py key:generate

# 1. Data first — the entity, its table, and everything around it
python dev.py make crud Article --fields "title:string:required|max:255,body:text:required,published:boolean"
python dev.py migrate

# 2. See it running
python dev.py serve            # http://127.0.0.1:8000
#   JSON API   /api/v1/articles
#   Admin UI   /admin/articles   (behind `auth`)

# 3. Rules and permissions
python dev.py make policy ArticlePolicy
python dev.py role create editor && python dev.py permission create publish-articles

# 4. Anything slow goes off the request
python dev.py make job PublishArticle
python dev.py queue work

# 5. Prove it
python -m pytest
```

Then iterate: views in `resources/views/`, routes in `routes/web.py` and
`routes/api.py`, business logic in `app/Services/`.

**`python dev.py route list`** prints every registered route — the fastest way
for an agent to check what it just built actually exists.

---

## From a blog to global scale

The same codebase carries all four stages. What changes is configuration and
which subsystems you switch on — not the architecture.

### 1. A blog · one machine, no services

SQLite (zero setup), `cookie` sessions, `array` cache, `sync` queue.

```bash
craft make:auth
craft make:crud Post --fields "title:string:required,body:text:required"
craft migrate && craft serve
```

Register an account at `/register`; the generated screens sit behind `auth`.

### 2. A real product · users, roles, background work

Switch `DB_CONNECTION=pgsql` in `.env` — nothing in your code changes. Turn on
what the traffic now justifies:

- **Authorization** — roles, **groups** (access granted to a team, not one
  person at a time), permissions, and **attribute conditions on any grant**:
  `{"user_id": "@user.id"}` for *only your own*, `{"amount": {"lte": 10000}}`
  for an approval ceiling. Enforced by the `role:` / `permission:` / `group:`
  route middleware, and by `Gate.authorize(ability, user, record)` in the
  controller when the decision depends on the record. `dev.py user access
  <email>` prints why each permission reaches someone. See
  [authorization](documentation/authorization.md).
- **`SESSION_DRIVER=file`** when sessions must be invalidatable server-side.
- **`CACHE_DRIVER=file`**, **`QUEUE_CONNECTION=database`** plus a worker
  process (`dev.py queue work`), and `dev.py schedule work` for cron-style jobs.

### 3. Traffic · concurrency and horizontal scale

The engine serves requests **in parallel out of the box**: the synchronous
middleware and controller chain runs on a thread pool, and each thread borrows
a pooled database connection for the request and returns it afterwards.
Measured on the sample app: ~27 req/s regardless of client count before,
~115 req/s from 10 clients up after, with p95 falling from 1.9s to 0.57s.

Scale from there with processes and services:

```bash
python dev.py serve --host 0.0.0.0 --port 8000 --no-reload --workers 4
# or, in production:
gunicorn -w 4 -k uvicorn.workers.UvicornWorker public.index:application
```

```python
# config/database.py
"pgsql": {
    "pool_size": 20,        # per worker process
    "pool_timeout": 30,
    "write": {"host": "primary.db.internal"},
    "read":  {"host": "replica.db.internal"},   # read/write splitting
}
```

Budget `pool_size × workers` against the database's `max_connections`. Move the
cache to `redis` and give every worker the same `APP_KEY`, or sessions break as
requests move between them (`documentation/deployment.md` has the checklist).

Use `tools/loadtest.py` to measure rather than guess:

```bash
python tools/loadtest.py http://127.0.0.1:8000/ --clients 1 --clients 50
```

### 4. Global · many tenants, many teams

- **Schema-per-tenant isolation** on PostgreSQL. `TenantMiddleware` routes each
  authenticated tenant to its own schema, creating and migrating it on first
  sight. The active tenant is scoped to the thread serving the request, so one
  tenant's request cannot repoint another's `search_path` mid-query.
- **Modules** — feature areas that can be switched off in the database, with
  routes declaring `.module("billing")`. Disabled means 404, no deploy needed.
- **Plugins** — discovered from `plugins/<slug>/plugin.py`, enabled per
  installation, with hooks. This is the extension point to build on when the
  application outgrows one team.
- **Read replicas** and **UUID public identity** are already in the ORM.

---

## What does not exist yet

Being explicit here is the point — an agent that assumes these exist will write
code that cannot work:

- **No storage/filesystem abstraction.** No S3 driver. File handling is yours.
- **No mail subsystem.** No SMTP anywhere in the codebase, which also means
  there is no password-reset or email-verification flow.
- **No API key manager** — bearer-token authentication works
  (`AuthenticateApiToken` + the `api_token` column), but issuing, rotating and
  rate-limiting keys per client is not built.
- **No Redis queue driver.** `QUEUE_CONNECTION=redis` warns and falls back to
  `database`; the Redis **cache** store, however, is real.
- **No broadcasting or notification subsystem.**
- **Eager loading covers one level.** No `with_("posts.comments")`, no
  `collection.load()`, no `with_count()`.
- **`remember me` is absent** from `Auth.attempt()` — it was removed rather
  than faked.
- The **cookie session driver signs but does not encrypt**; use
  `SESSION_DRIVER=file` for sensitive session data.

`CRAFT_DESIGN.md` describes an aspirational design, not the implemented one.
Treat it as a target, never as an API reference.

---

## Rules for an AI working in this codebase

1. **Verify in the code, never from memory.** `engine/` is the framework and
   `tests/` is the specification. Code wins over documentation; documentation
   wins over recollection.
2. **Never name a third-party framework** in code, docstrings or docs. Craft's
   concepts have Craft's names.
3. **No placebos.** If you cannot implement it, do not ship a method that
   returns a plausible value, a config key nothing reads, or an
   `except: pass` that fakes success. Say it is missing — that is what the
   section above is for.
4. **Every change to `engine/`, `app/`, `bootstrap/`, `config/`, `database/`,
   `routes/` or `dev.py` gets a `CHANGELOG.md` entry in the same change**, not
   batched later.
5. **Run the suite on both drivers** before claiming something works —
   `python -m pytest`, then again with `CRAFT_TEST_DB=pgsql`. Several real bugs
   in this repository's history appeared on exactly one of them.
6. **UI changes are not covered by pytest** — no test renders a page. Check a
   real browser.

---

## Where things are

```
app/                     Your application code
  Http/Controllers/      Controllers
  Http/Middleware/       Middleware
  Http/Requests/         FormRequests (authorization + validation)
  Http/Resources/        JSON transformers
  Models/                Craft ORM models
  Policies/ Events/ Listeners/ Jobs/ Providers/ Services/
bootstrap/app.py         Container, providers, global middleware pipeline
config/                  app, auth, cache, database, logging, queue, session
database/                migrations/ seeders/ factories/
engine/                  THE FRAMEWORK (published as craft.*)
plugins/                 Discoverable plugins
public/index.py          ASGI entry point (`application = asgi_app`)
resources/views/         Forge templates
routes/                  web.py, api.py, console.py
tests/                   The executable specification
tools/loadtest.py        Throughput probe
dev.py                   The console
```

## Next

- [`README.md`](README.md) — quick start, demo accounts, CLI reference.
- [`documentation/`](documentation/README.md) — the full guide: container,
  routing, ORM, migrations, validation, security, sessions, cache, queues,
  resources, localization, testing, deployment, CRUD builder.
- [`CHANGELOG.md`](CHANGELOG.md) — what changed and, more usefully, *why*.
- [`SECURITY.md`](SECURITY.md) — security policy and production checklist.
