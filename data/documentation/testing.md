# Testing

```bash
python -m pytest
python -m pytest tests/test_orm_model.py
python -m pytest -k "eager_loading"
python -m pytest -q
```

The default target is SQLite in memory.

## Three targets

A change needs validation on all supported dialects and Python versions.
Database tests must not target an existing database or remove records. The
current PostgreSQL fixture and legacy tests still require a non-destructive
isolation redesign; do not run the full suite against a persistent server.

```bash
# 1. SQLite, your local Python
python -m pytest

# 2. Python 3.14, the minimum supported version
python3.14 -m pytest
```

Python 3.14 evaluates annotations lazily (PEP 649). Code with a broken
annotation — a missing import, say — runs fine there.

## The schema comes from migrations

`conftest.py` builds the test schema with the real migrator, so every run
exercises your migrations rather than a parallel fixture that can drift.

```python
@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    from bootstrap.app import app
    from craft.migrations.migrator import Migrator

    migrator = Migrator(app)
    migrator.run()
    yield app
```

Request it to get the booted application:

```python
def test_something(migrated_database):
    db = migrated_database.make("db")
```

## Building tables in a test

Use the schema builder, not raw DDL — that keeps the test dialect-agnostic so it
runs on SQLite and PostgreSQL alike:

```python
@pytest.fixture(autouse=True)
def tables(migrated_database):
    schema = migrated_database.make("schema")
    schema.create_table("gadgets", lambda t: (
        t.id(),
        t.string("name").nullable(),
        t.timestamps(),
    ))
    yield
```

## HTTP tests

```python
from starlette.testclient import TestClient
from bootstrap.app import asgi_app


def test_login_survives_a_redirect():
    client = TestClient(asgi_app)

    token = client.get("/t/token").json()["token"]
    client.post("/login", data={
        "email": "user@example.com", "password": "secret", "_token": token,
    })

    # A separate request still knows who we are.
    assert client.get("/me").json()["user"] == "user@example.com"
```

Each `TestClient` keeps its own cookie jar, so two clients are two sessions.

State-changing requests need a CSRF token, or they get 419. Fetch one from a GET
route first, or exempt the route under `api/*`.

## Every file must pass on its own

```bash
python -m pytest tests/test_orm_model.py
```

A file that only passes in the full run is relying on state another test left
behind. Two real examples from this codebase:

- A fixture built a scratch `Application`, which claimed the global container
  and pointed every later test at a temp database. Fixed with
  `bind_as_global=False`.
- A test called `Config.set("lang.pt.greeting", "Ola")` and never restored it,
  so every later test reading a `pt` translation saw that value.

Restore anything shared — configuration, the global container, class attributes:

```python
def test_with_config(migrated_database):
    config = migrated_database.make("config")
    config.set("cache.default", "file")
    try:
        ...
    finally:
        config.set("cache.default", "array")
```

## Test what would regress

Assert on the behaviour, not the implementation. The eager-loading tests count
the SQL issued, because asserting only on results would pass just as happily
with the N+1 bug they exist to prevent:

```python
class QueryCounter:
    def __init__(self, db):
        self.db, self.queries, self._original = db, [], db.statement

    def __enter__(self):
        def counting(query, bindings=None, read=False):
            if query.lstrip().upper().startswith("SELECT"):
                self.queries.append(query)
            return self._original(query, bindings, read)
        self.db.statement = counting
        return self

    def __exit__(self, *exc):
        self.db.statement = self._original


def test_eager_loading_is_two_queries(counter):
    with counter() as c:
        for author in Author.with_("posts").get():
            author.posts().get()
    assert c.count == 2
```

The same idea applies elsewhere: assert the password is not the plaintext, that
a Resource does not leak a hidden field, that a 4xx is not logged as a fault.

## Factories

```python
from database.factories.UserFactory import UserFactory

user = UserFactory.new().create()
users = UserFactory.times(3).create()
admin = UserFactory.new().state("admin").create()
draft = UserFactory.new().make()          # unsaved
```

## Fast feedback

```bash
python -m pytest -x                 # stop at the first failure
python -m pytest --lf               # only what failed last time
python -m pytest -q --tb=short
```
