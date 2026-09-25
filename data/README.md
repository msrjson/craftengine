# CraftEngine

A Python web framework built on **Starlette**, delivered as an engine and
nothing else: no admin panel, no login screen, no theme, no demo data. A new
project answers one route and contains nothing to reuse, so the people and
agents building on it start from their own code rather than from someone
else's layout.

The core lives in `engine/` and is exposed publicly as `craft.*`.

```python
from craft.facades import Route, DB, Auth
from craft.orm.model import Model
```

**1,500+ tests**, validated on SQLite, PostgreSQL, and Python 3.14.

> New here - or an AI agent picking this up? Read [`AGENTS.md`](AGENTS.md)
> first, then [`CRAFT_ENGINE.md`](CRAFT_ENGINE.md) for what the engine
> contains and what does *not* exist yet.

---

## Getting started

```bash
craft new myapp
cd myapp
cp .env.example .env
craft key:generate        # signs session cookies
craft migrate
craft serve               # http://127.0.0.1:9000
```

The default database is **SQLite**: zero configuration, no server. For
PostgreSQL or MySQL, uncomment the matching block in `.env`. `python dev.py`
works everywhere `craft` does, without installing the package.

`/` shows a starter page. Delete `resources/views/welcome.forge.py` and its
route in `routes/web.py` when you have a page of your own; nothing else refers
to either.

### Add what you need

Nothing below is present until you ask for it, and everything it writes is
yours to change:

| Command | Writes |
|---|---|
| `craft make:auth` | `User` model and migration, sign-in, registration, sign-out |
| `craft make:admin` | Role, permission and group management under `/admin` |
| `craft make:crud Product --fields "name:string:required"` | Model, migration, screens and a JSON API |
| `craft make:model`, `make:controller`, `make:request`, ... | One class at a time |

Every route that answers is listed by `craft route:list`, the engine's own
included. Health probes, metrics and the MSR manifest are off until a flag in
`config/` turns them on.

### Upgrading from 3.x

4.0 removed the demo application. A project that used its admin panel, login
screens or seeded accounts runs `craft make:auth` and `craft make:admin`, then
points `config/auth.py` at its models. The last release carrying the demo is
`v3.23.0-r00016`.

---

## The `dev` CLI

```bash
python dev.py migrate                 # apply pending migrations
python dev.py migrate:status          # what ran, and in which batch
python dev.py db seed                 # run the DatabaseSeeder
python dev.py db show|tables|ping     # inspect the connection
python dev.py route list              # every registered route
python dev.py make model Product -m   # model + migration
python dev.py make controller Product -r
python dev.py queue work              # process the queue
python dev.py tinker                  # shell with the app loaded
```

Both forms work: `migrate:status` and `migrate status`.

---

## Structure

```
app/                     Application code
  Http/Controllers/      Controllers
  Http/Middleware/       Middleware
  Http/Requests/         FormRequests (authorization + validation)
  Http/Resources/        JSON transformers
  Models/                Craft ORM models (Active Record)
  Policies/ Events/ Listeners/ Jobs/ Providers/ Services/
bootstrap/app.py         Builds the container, registers providers, mounts the kernel
config/                  app, auth, cache, database, logging, queue, session
database/                migrations/ seeders/ factories/
public/index.py          Front controller (`application = asgi_app`)
resources/views/         Forge templates
routes/                  web.py, api.py, console.py
engine/                  The framework (exposed as craft.*)
storage/                 logs, cache, sessions
tests/                   pytest suite
dev.py                   CLI
```

### This repository is not a generated project

`data/` is the engine's development tree, and it still carries the migrations
of the demo application that shipped before 4.0.0. They have already run on
existing databases, and applied migrations are never edited or removed, so
they stay. Compared with the output of `craft new`, this tree creates these
extra tables:

| Tables | Where a generated project gets them |
|---|---|
| `users`, `roles`, `permissions`, `role_user`, `permission_role`, `groups`, `group_user`, `group_role`, `permission_group`, `permission_user` | `craft make:auth` and `craft make:admin` |
| `tenants` | the project's own migration, when it is multi-tenant |
| `plugins`, `modules`, `media`, `system_logs` | not generated |

Both trees share `jobs`, `failed_jobs`, `sessions`, `translations`,
`settings`, the security tables (`auth_audit_logs`, `auth_cooldowns`,
`firewall_rules`, `security_events`) and `scheduler_runs`. `craft doctor`
reports any table the engine needs that a project lacks. When comparing behaviour, compare against a project from
`craft new`, not against this tree: code that works here because a demo
table exists can fail in a fresh project.

---

## Database

Three drivers, with the same SQL: **SQLite**, **PostgreSQL**, and **MySQL**.
`?` and `:name` placeholders are translated to each driver's paramstyle, and
the schema builder generates DDL per dialect.

```python
# database/migrations/2026_01_01_000001_create_products_table.py
from craft.migrations import Schema

def up():
    Schema.create_table("products", lambda t: (
        t.id(),
        t.string("name"),
        t.decimal("price", 10, 2),
        t.foreign_id("user_id").constrained().cascade_on_delete(),
        t.boolean("active", default=True),
        t.timestamps(),
    ))

def down():
    Schema.drop_table("products")
```

The fluent and keyword styles are interchangeable:
`t.string("cpf").nullable()` == `t.string("cpf", nullable=True)`.

Read/write splitting and schema-per-tenant (PostgreSQL) are supported:

```python
DB.set_tenant_schema("tenant_42")
```

---

## ORM (Craft ORM)

```python
class Post(Model):
    __table__ = "posts"
    fillable = ["title", "body", "user_id"]

    def author(self):
        return self.belongs_to(User, foreign_key="user_id")

    def comments(self):
        return self.has_many(Comment, foreign_key="post_id")
```

**Eager loading** — `with_()` turns N+1 into one query per relation:

```python
posts = Post.with_("author", "comments").get()   # 3 queries, not 1 + 2N
for post in posts:
    post.author().first()    # already loaded
```

Relations: `has_one`, `has_many`, `belongs_to`, `belongs_to_many`
(with `attach`/`detach`/`sync`). Soft deletes via a mixin — **list the mixin
first**, or the MRO makes `Model` win:

```python
class Note(SoftDeletes, Model):
    __table__ = "notes"

Note.query()          # hides deleted rows
Note.with_trashed()   # includes them
Note.only_trashed()   # only the deleted ones
```

Query builder: `where`, `or_where`, `where_in`, `where_null`, `where_between`,
`join`, `group_by`, `having`, `order_by`, `paginate`, and aggregates
(`count`, `sum`, `avg`, `min`, `max`).

---

## HTTP

```python
Route.get("/posts", [PostController, "index"]).name("posts.index")
Route.post("/posts", [PostController, "store"]).middleware("auth")
Route.resource("posts", PostController)
```

Per-route middleware resolves by alias: `auth`, `api`, `session`, `csrf`.
An unknown alias **raises at boot** instead of becoming decorative
protection.

The global pipeline lives in `bootstrap/app.py`, and order matters — the
session must exist before CSRF, and before the user is resolved:

```python
kernel.with_middleware(StartSession, VerifyCsrfToken, Authenticate, ...)
```

### Request

The body is parsed before the pipeline, so synchronous controllers read
input directly:

```python
request.input("email")      # query string + body (form or JSON)
request.only("name", "email")
request.boolean("remember")
request.file("avatar")
request.session().get("cart")
request.user()
request.bearer_token()
```

---

## Session and CSRF

Two drivers: `cookie` (payload in the signed cookie) and `file` (only the
id in the cookie, payload on disk — allows server-side invalidation). Both
are signed with `APP_KEY`; a tampered cookie is rejected, not trusted.

```python
request.session().put("cart", [1, 2])
request.session().flash("status", "Saved!")   # lives for exactly one request
request.session().token()                      # CSRF token
```

CSRF is verified on POST/PUT/PATCH/DELETE, via the `_token` field or the
`X-CSRF-TOKEN` header. `api/*` routes are exempt by default. Failure
returns **419**.

---

## Authentication

```python
if Auth.attempt({"email": email, "password": password}):
    return redirect(route="home")
```

Passwords use bcrypt (with a PBKDF2-SHA256 fallback if the backend is
unavailable). Login is stored in the session and the session id is
rotated, which closes session fixation. A non-existent user costs the same
time as a wrong password, so timing does not reveal which emails exist.

Authorization via Gate and Policies — **deny by default**:

```python
Gate.define("update-post", lambda user, post: post.user_id == user.id)
Gate.authorize("update-post", user, post)   # raises if denied
```

---

## Validation

```python
Validator(data, {
    "name":     ["required", "string", "max:255"],
    "email":    "required|email|unique:users,email",
    "age":      ["nullable", "integer", "between:18,120"],
    "password": ["required", "min:8", "confirmed"],
})
```

Rules: presence (`required`, `required_if`, `required_with`, `nullable`),
types (`string`, `integer`, `numeric`, `boolean`, `array`, `date`), formats
(`email`, `url`, `uuid`, `alpha*`, `regex`), size (`min`, `max`, `between`,
`size`), sets (`in`, `not_in`, `same`, `different`, `confirmed`,
`accepted`), and database (`unique`, `exists`).

Or declarative, with authorization alongside it:

```python
class StorePostRequest(FormRequest):
    def authorize(self):
        return self.user() is not None

    def rules(self):
        return {"title": ["required", "string", "max:255"]}

data = StorePostRequest(request).validated()   # raises on failure
```

---

## Concurrency

One worker process serves requests **in parallel**: the synchronous middleware
and controller chain runs on a thread pool, and each thread borrows a pooled
database connection for the request, returning it afterwards. Measured on the
sample app with `tools/loadtest.py`: ~27 req/s regardless of client count
before, ~115 req/s from 10 clients up after, p95 falling from 1.9s to 0.57s.

```python
# config/database.py — per connection
"pool_size": 10,      # physical connections per worker process (default)
"pool_timeout": 30,   # seconds to wait for a free one before failing
```

Scale further with processes, since the GIL caps one:

```bash
python dev.py serve --host 0.0.0.0 --port 9000 --no-reload --workers 4
```

Transaction depth, the tenant `search_path` and the authenticated user are all
scoped to the request being served, never process-wide — under concurrency that
distinction is correctness, not tidiness.

---

## Cache, queues, and events

```python
Cache.remember("stats", 300, lambda: expensive())   # array | file | redis
Queue.push(SendEmail(user_id=1))                    # sync | database
Event.dispatch(UserRegistered(user))
```

Jobs are serialized as **JSON**, never pickle, so a worker in another
process can rebuild them. Retry with backoff and `available_at` included.

---

## Tests

```bash
python -m pytest                       # in-memory SQLite (default)

# Real PostgreSQL: a fresh database per session, created through DB_DATABASE
docker exec -e CRAFT_TEST_DB=pgsql -e DB_HOST=db -e DB_PORT=5499 \
    -e DB_DATABASE=craft_db -e DB_USERNAME=craft -e DB_PASSWORD=secretpassword \
    -e DB_SSLMODE=disable framework python -m pytest

docker exec framework python -m pytest  # Python 3.14, the minimum version
```

`conftest.py` builds the schema with the **real migrator**, so migrations
are exercised on every run instead of relying on parallel fixtures. On
PostgreSQL the tests never run in the database `DB_DATABASE` names: the session
creates `craft_test_<utc>_<id>_<worker>` through it and never drops it. Tests
never delete, truncate or drop (`tests/test_fixture_safety.py` enforces it and
the PostgreSQL run refuses to start otherwise); they isolate data by making it
unique. Test databases accumulate on a development server - they hold only test
data and can be listed with `\l craft_test_*`.

---

## Documentation

Full documentation lives in [`documentation/`](documentation/README.md):
installation, configuration, the container, routing, controllers, views,
validation, migrations, the ORM, security, sessions, cache, queues,
resources, i18n, testing, deployment, and the `dev` reference.

- [`CRAFT_ENGINE.md`](CRAFT_ENGINE.md) — what the engine is, the build loop,
  scaling from a blog to multi-tenant, and what is not built yet.
- [`CHANGELOG.md`](CHANGELOG.md) — what changed, in Keep a Changelog format.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — how to contribute.
- [`SECURITY.md`](SECURITY.md) — security policy and production checklist.
- `.agents/docs/backlog.md` — upcoming slices and open decisions. Lives at
  the workspace root (outside this repository), not versioned here.

The official repository is
<https://github.com/msrjson/craftengine>; the published site,
<https://craftengine.org>, is built from `documentation/` by
`python dev.py docs build`.

## License

[MIT](LICENSE) — © 2026 Antonio Santos &lt;snarthost@gmail.com&gt;
