# Craft Engine

A batteries-included Python web framework, built on **Starlette**. This repository is the **base skeleton** for
building new applications — the skeleton you copy to start an app.

The core lives in `engine/` and is exposed publicly as `craft.*`.

For the starter application's actual login URLs and middleware flow, see
[Authentication](documentation/authentication.md). `GET /signin` redirects to
the canonical `/login` page; credentials are submitted to `POST /login`.

```python
from craft.facades import Route, DB, Auth
from craft.orm.model import Model
```

**1200+ tests**, validated on SQLite, PostgreSQL, and Python 3.14.


> New here — or an AI agent picking this up? Read
> [**`CRAFT_ENGINE.md`**](CRAFT_ENGINE.md): what the engine contains, the build
> loop, how the same codebase carries an app from a blog to multi-tenant scale,
> and an explicit list of what does *not* exist yet.
>
> Looking for an objective market comparison (Django vs FastAPI vs Laravel vs Rails)?
> Check out the [**Market Evaluation & Framework Benchmark**](documentation/market_evaluation.md).

---

## Getting started

```bash
cp .env.example .env
python dev.py key:generate        # signs session cookies
python dev.py migrate --seed
python dev.py serve
```

The default database is **SQLite** — zero configuration, no server needed.
For PostgreSQL or MySQL, uncomment the matching block in `.env`.
`APP_DEBUG` defaults to off in the framework; `.env.example` turns it on
for local development.

Or with Docker (app at `http://localhost:9000`):

```bash
docker compose up -d --build
```

---

## Demo accounts

`migrate --seed` seeds **3 standard demo accounts** — the framework's
official demo credentials. Any skeleton spun up from this repository gets the
same 3 accounts, so docs, screenshots, and admin-UI work can reference them
by name without re-explaining who they are.

| Email | Password | Role | Demonstrates |
|---|---|---|---|
| `user@craft.local` | `craft` | `user` | A plain authenticated account — the `user` role, basic permissions. |
| `tenant@craft.local` | `craft` | `tenant-manager` | `type = "tenant"`, so `TenantMiddleware` routes it to an isolated per-schema PostgreSQL tenant; the `tenant-manager` role adds `manage-users` on top of the basic set — elevated, short of full admin. |
| `admin@craft.local` | `craft` | `admin` | `is_admin = True` and the `admin` role — full access, every seeded permission. |

All 3 passwords are `craft`. See [`documentation/authorization.md`](documentation/authorization.md)
for the RBAC system these roles are built on.

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

# Real PostgreSQL
$env:CRAFT_TEST_DB="pgsql"
$env:DB_HOST="127.0.0.1"; $env:DB_PORT="5499"
$env:DB_DATABASE="craft_validation"
$env:DB_USERNAME="craft"; $env:DB_PASSWORD="secretpassword"
python -m pytest

docker exec framework python -m pytest  # Python 3.14, the minimum version
```

`conftest.py` builds the schema with the **real migrator**, so migrations
are exercised on every run instead of relying on parallel fixtures.

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
