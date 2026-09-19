# Testing Patterns Reference (Python, pytest, Craft)

Quick reference of pytest patterns for Craft Engine applications, illustrating the
principles of the `test-driven-development` skill
(`.claude/skills/test-driven-development/SKILL.md`): Arrange-Act-Assert, descriptive
names, mock discipline and the anti-patterns to avoid.

Every Craft-specific helper below exists in the framework source (`engine/`) and its
suite (`tests/`). A generated application can differ — read the project's own
`tests/conftest.py` before relying on a fixture name.

## Table of Contents

- [Running the Suite](#running-the-suite)
- [Test Structure (Arrange-Act-Assert)](#test-structure-arrange-act-assert)
- [Test Naming Conventions](#test-naming-conventions)
- [Common Assertions](#common-assertions)
- [Fixtures](#fixtures)
- [Test Doubles](#test-doubles)
- [Validation and FormRequest Testing](#validation-and-formrequest-testing)
- [HTTP / Integration Testing](#http--integration-testing)
- [ORM and Factory Testing](#orm-and-factory-testing)
- [SQLite and PostgreSQL Runs](#sqlite-and-postgresql-runs)
- [Translation Testing](#translation-testing)
- [Browser-Level Testing](#browser-level-testing)
- [Test Anti-Patterns](#test-anti-patterns)

## Running the Suite

```bash
python -m pytest tests                                  # full suite (the gate)
python -m pytest tests/test_form_request.py             # one module
python -m pytest tests/test_tasks.py -k "overdue"       # tests matching an expression
python -m pytest tests/test_tasks.py::TestCompleteTask  # one class
python -m pytest tests -x                               # stop at the first failure
python -m pytest tests --lf                             # re-run only the last failures
python -m pytest tests -vv                              # verbose names and diffs
python -m pytest tests --cov=engine --cov-report=term-missing   # coverage (pytest-cov)
```

`testpaths = ["tests"]` is declared in `pyproject.toml`, so a bare `python -m pytest`
also finds the suite.

## Test Structure (Arrange-Act-Assert)

```python
def test_creates_a_task_with_pending_status(self) -> None:
    # Arrange: inputs and preconditions
    service = TaskService(repository=FakeTaskRepository())

    # Act: the one operation under test
    task = service.create_task(title="Quarterly report")

    # Assert: the observable outcome
    assert task["title"] == "Quarterly report"
    assert task["status"] == "pending"
```

## Test Naming Conventions

```python
# Pattern: test_<expected behavior>_<condition>, grouped by unit in a class.
class TestCreateTask:
    def test_creates_a_task_with_pending_status(self) -> None: ...
    def test_raises_validation_exception_when_the_title_is_empty(self) -> None: ...
    def test_strips_whitespace_from_the_title(self) -> None: ...
    def test_assigns_a_unique_id_to_each_task(self) -> None: ...
```

The Craft suite also groups by outcome, which reads well for security rules:

```python
class TestItRejects:
    def test_a_request_with_no_token_is_refused(self, client) -> None: ...

class TestItAdmits:
    def test_a_valid_token_is_authenticated_and_resolves_the_user(self, client) -> None: ...
```

A docstring on a test explains *why* the behavior matters when the name alone cannot.

## Common Assertions

```python
import math

import pytest

# Equality and identity
assert result == expected
assert result is None
assert result is not expected_instance

# Truthiness — prefer explicit comparisons when the type matters
assert form.passes() is True

# Numbers
assert total_cents > 0
assert math.isclose(ratio, 0.3, rel_tol=1e-9)   # never == on floats
assert value == pytest.approx(0.3)

# Strings
assert "title" in form.errors
assert slug.startswith("quarterly-")

# Collections
assert len(tasks) == 3
assert {"id": 1} in rows
assert set(payload) == {"code", "message_key", "params"}

# Exceptions
with pytest.raises(ValidationException):
    StoreTaskRequest({"title": ""}).validated()

with pytest.raises(ModelNotFoundError):     # craft.orm.exceptions
    Task.find_or_fail(999_999)

# Exception details
with pytest.raises(TaskAlreadyCompletedError) as caught:
    service.complete_task(task_id=completed_id)
assert caught.value.code == "TASK_ALREADY_COMPLETED"
assert caught.value.message_key == "task.complete.already_completed"
```

Assert on `code` and `message_key`, never on a rendered sentence — the copy lives in the
translation store and changes per locale. `ValidationException`,
`AuthorizationException` and `NotFoundHttpException` come from
`craft.exceptions.handler`; a domain error carrying `code` and `message_key` is defined
by the application.

## Fixtures

```python
import pytest


@pytest.fixture
def service() -> TaskService:
    """A service wired to an in-memory repository."""
    return TaskService(repository=FakeTaskRepository())


@pytest.fixture
def persisted_user(migrated_database):
    """A user row this test owns, removed afterwards."""
    from app.Models.User import User

    user = User.force_create({"name": "Test", "email": "fixture@craft.local", "password": "s3cret"})
    yield user
    DB.statement("DELETE FROM users WHERE email = 'fixture@craft.local'")
```

What the Craft framework suite's `tests/conftest.py` provides:

| Fixture | Scope | What it does |
|---|---|---|
| `migrated_database` | session, autouse | Builds the schema with the real `Migrator` once and yields the application (`bootstrap.app.app`) |
| `is_postgres` | function | `True` when the suite runs against PostgreSQL |

It also sets `APP_ENV=testing`, `QUEUE_CONNECTION=sync` and `CACHE_DRIVER=array`
before the application boots, so jobs run inline and the cache is in-memory.

Scope guidance:

- `function` (default) for anything a test mutates
- `module` for route registration or other setup that is read-only afterwards
- `session` only for immutable, expensive setup such as the migrated schema
- Teardown goes after `yield`, so it runs even when the test fails

Cleanup of fixture rows is test hygiene, not business deletion; production code still
uses soft deletes for business entities (`class Note(SoftDeletes, Model)`).

## Test Doubles

### Facade Doubles

```python
from craft.facades import Cache


class FakeCache:
    """Records the keys it was asked for."""

    def __init__(self) -> None:
        self.keys: list[str] = []

    def get(self, key: str, default: object = None) -> object:
        self.keys.append(key)
        return "cached-value"


@pytest.fixture
def fake_cache():
    double = FakeCache()
    Cache._swap(double)
    yield double
    Cache._clear_resolved()      # mandatory: a leaked double rewires later tests


def test_reads_the_dashboard_from_cache(fake_cache) -> None:
    assert load_dashboard() == "cached-value"
    assert fake_cache.keys == ["dashboard:summary"]
```

`Facade._swap(instance)` points one facade at the double; `_clear_resolved()` restores
container resolution. A swap on one facade never leaks to another.

### Container Doubles

```python
def test_resolves_the_gateway_from_the_container(migrated_database) -> None:
    migrated_database.instance("payments.gateway", FakeGateway(approve=False))
    ...
```

The application exposes `bind`, `singleton`, `instance` and `make`. Prefer constructor
injection for services — then a unit test passes the double directly and needs no
container at all.

### Patching with pytest

```python
def test_uses_the_configured_region(monkeypatch) -> None:
    monkeypatch.setenv("STORAGE_REGION", "sa-east-1")
    assert storage_region() == "sa-east-1"
```

`monkeypatch` undoes itself after the test. Reach for `unittest.mock` only for
interaction checks at a true boundary.

### Double at Boundaries Only

```
Double these:                  Do not double these:
├── External HTTP APIs         ├── Your own services' internals
├── Payment and mail delivery  ├── Business rules
├── The clock (inject `now`)   ├── Data transformations
├── Randomness (inject seed)   ├── Validation rules
└── Slow infrastructure        └── Pure functions and plugin engines
```

The ORM on in-memory SQLite is fast enough to use for real in most tests.

## Validation and FormRequest Testing

```python
from craft.exceptions.handler import AuthorizationException, ValidationException
from craft.validation.form_request import FormRequest


class StoreTaskRequest(FormRequest):
    def rules(self) -> dict[str, list[str]]:
        return {"title": ["required", "string", "max:120"], "estimate": ["nullable", "integer"]}


class TestStoreTaskRequest:
    def test_valid_input_passes(self) -> None:
        assert StoreTaskRequest({"title": "Plan sprint"}).passes() is True

    def test_validated_returns_only_ruled_fields(self) -> None:
        form = StoreTaskRequest({"title": "Plan sprint", "is_admin": True})
        assert form.validated() == {"title": "Plan sprint"}

    def test_missing_title_is_reported_on_the_field(self) -> None:
        form = StoreTaskRequest({})
        assert form.fails() is True
        assert "title" in form.errors

    def test_validated_raises_on_invalid_input(self) -> None:
        with pytest.raises(ValidationException):
            StoreTaskRequest({"title": "x" * 500}).validated()
```

The mass-assignment case (`is_admin` dropped by `validated()`) is a security test —
keep one for every request that feeds a model.

## HTTP / Integration Testing

```python
import pytest

from bootstrap.app import asgi_app
from craft.facades import Route
# TestClient: import it exactly as the neighboring HTTP tests in tests/ do.


@pytest.fixture(scope="module", autouse=True)
def task_routes(migrated_database):
    Route.post("/test-api/tasks", store_task).middleware("api").name("test.api.tasks.store")
    yield


@pytest.fixture
def client():
    return TestClient(asgi_app)


class TestStoreTaskEndpoint:
    def test_creates_a_task_and_returns_201(self, client, api_user) -> None:
        response = client.post(
            "/test-api/tasks",
            json={"title": "Plan sprint"},
            headers={"Authorization": "Bearer valid-token-123", "Accept": "application/json"},
        )

        assert response.status_code == 201
        assert response.json()["data"]["title"] == "Plan sprint"

    def test_returns_422_with_field_errors_for_invalid_input(self, client, api_user) -> None:
        response = client.post(
            "/test-api/tasks",
            json={"title": ""},
            headers={"Authorization": "Bearer valid-token-123", "Accept": "application/json"},
        )

        assert response.status_code == 422

    def test_refuses_an_anonymous_caller(self, client) -> None:
        response = client.post("/test-api/tasks", json={"title": "x"}, headers={"Accept": "application/json"})

        assert response.status_code in (401, 403)
```

Patterns worth copying from the framework suite:

- Register throwaway routes under a `/test-...` prefix with a unique `.name(...)`
- Send `Accept: application/json` to get JSON errors instead of HTML pages
- Pass `follow_redirects=False` to assert on a redirect itself (guest to login)
- For session forms, fetch a CSRF token first and post it as `_token`; a
  state-changing form without it must be rejected — test that too
- Assert that "no token" and "wrong token" produce the same response, so the endpoint
  does not confirm which credentials exist

## ORM and Factory Testing

```python
from craft.factories import Factory
from craft.orm.model import Model
from craft.orm.soft_deletes import SoftDeletes


class Task(SoftDeletes, Model):
    __table__ = "tasks"
    fillable = ["title", "status", "user_id"]


class TaskFactory(Factory):
    model = Task

    def definition(self) -> dict[str, object]:
        return {"title": "Generated task", "status": "pending"}

    def completed(self) -> dict[str, object]:
        return {"status": "completed"}


class TestTaskPersistence:
    def test_create_persists_and_find_reads_it_back(self) -> None:
        task = TaskFactory.new().create({"title": "Persisted"})

        assert Task.find(task.id) is not None

    def test_state_and_count_build_several_rows(self) -> None:
        tasks = TaskFactory.times(3).state("completed").create()

        assert len(tasks) == 3

    def test_make_builds_without_writing(self) -> None:
        task = TaskFactory.new().make()

        assert "id" not in task.to_dict()

    def test_delete_is_soft(self) -> None:
        task = TaskFactory.new().create()
        task.delete()

        assert task.trashed() is True
        assert Task.find(task.id) is None
        assert Task.with_trashed().find(task.id) is not None
```

`Factory` (`craft.factories`) offers `new()`, `times(n)`, `count(n)`, `state(dict |
"method_name")`, `raw()`, `make()` and `create()`; one instance returns a model, several
return a list. Factories live in `database/factories/` and are generated with
`python dev.py make:factory`.

`SoftDeletes` must be listed before `Model` in the bases; the reverse order is refused
at class creation, because it would turn `delete()` into a real `DELETE`.

## SQLite and PostgreSQL Runs

The default run uses in-memory SQLite with the schema built by the real migrator, so
migrations are exercised on every run. Validate the PostgreSQL dialect against a real
server:

```powershell
$env:CRAFT_TEST_DB = "pgsql"
$env:DB_HOST = "127.0.0.1"; $env:DB_PORT = "5432"
$env:DB_DATABASE = "craft_test"
$env:DB_USERNAME = "craft"; $env:DB_PASSWORD = "<secret>"
python -m pytest tests
```

```python
def test_row_level_security_isolates_tenants(is_postgres, migrated_database) -> None:
    if not is_postgres:
        pytest.skip("row-level security needs PostgreSQL")
    ...
```

- Point `CRAFT_TEST_DB=pgsql` only at a **disposable** database: the PostgreSQL path of
  the session fixture starts from a clean schema, which would destroy real data
- Anything dialect-sensitive — JSONB, row-level security, extensions, locking, UUID
  defaults — needs a PostgreSQL run in CI, not just SQLite
- A skip must name its reason; verify a custom marker actually skips what it claims

## Translation Testing

```python
from craft.facades import DB
from craft.support.translation import locale_chain


def test_a_regional_locale_falls_back_to_its_base() -> None:
    assert locale_chain("pt-BR", "en") == ["pt-BR", "pt", "en"]


def test_every_new_key_has_three_locale_rows(migrated_database) -> None:
    rows = DB.select("SELECT locale FROM translations WHERE key = ?", ["task.complete.already_completed"])
    assert {row["locale"] for row in rows} == {"en", "pt-BR", "es"}
```

The framework's `translations` table stores `key`, `locale` and `value`; `DB.select`
returns rows addressable by column name. Templates resolve keys with
`{{ __('task.index.title') }}`; assert on the presence of the key's resolved value for a
chosen locale only in tests dedicated to translation, not in feature tests.

## Browser-Level Testing

Craft ships no browser automation dependency, and the frontend is vanilla JS and CSS
with no build step. Verify rendered pages with Chrome DevTools through the
`browser-testing-with-devtools` skill
(`.claude/skills/browser-testing-with-devtools/SKILL.md`):

```
1. python dev.py serve
2. Open the page, reproduce the flow, capture a screenshot
3. Console: zero errors; Network: expected status codes and payloads
4. DOM: the @csrf hidden input exists on state-changing forms,
   @honeypot / @antispam fields exist on public forms
5. Encode what you verified as an HTTP test in pytest where possible
```

If a project adds a browser automation tool, keep those tests few and limited to
critical flows.

## Test Anti-Patterns

| Anti-Pattern | Problem | Better Approach |
|---|---|---|
| Testing implementation details | Breaks on refactor | Test inputs, outputs and persisted state |
| Asserting on rendered copy | Breaks when a translation changes | Assert on `code`, `message_key`, status and data |
| Shared mutable state | Tests pollute each other | Function-scoped fixtures; teardown after `yield` |
| Leaked facade double | Later tests hit the double | `_clear_resolved()` in every teardown |
| Testing third-party code | Not your bug, wasted time | Double the boundary, test your code |
| Skipping tests to pass CI | Hides real bugs | Fix or delete the test |
| Permanent `pytest.mark.skip` | Dead code pretending to be coverage | Remove it or fix it |
| Overly broad assertions (`status_code != 500`) | Misses regressions | Assert the exact expected outcome |
| Un-awaited coroutine in a test | Passes without running the code | Drive async code to completion and assert on its result |
| Destructive schema resets against shared databases | Data loss, violates forward-only migrations | Disposable test database; clean only the rows a test created |
