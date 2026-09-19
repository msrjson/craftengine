---
name: api-and-interface-design
description: Guides the design of stable, hard-to-misuse interfaces in Craft Engine projects - HTTP endpoints, Resources, FormRequests, service contracts and module boundaries. Use when designing or changing an API, a public service or facade, a module or plugin boundary, or the contract between Forge pages, vanilla JS and the backend.
---

# API and Interface Design

## Overview

Design stable, documented interfaces that are hard to misuse. A good interface makes the right
thing easy and the wrong thing hard. This applies to JSON endpoints under `routes/api.py`,
Resources, FormRequests, service contracts resolved from the container, facades, plugin
boundaries and the data a Forge template receives: any surface where one piece of code talks to
another.

## When to Use

- Designing new endpoints in `routes/api.py` or `routes/web.py`
- Defining module or plugin boundaries, or contracts between teams
- Defining what a Forge template or a vanilla JS widget receives from the server
- Designing a schema that will shape an API response
- Changing an existing public interface, facade or container binding

## Core Principles

### Hyrum's Law

> With a sufficient number of users of an API, all observable behaviors of your system will be
> depended on by somebody, regardless of what you promise in the contract.

Every public behavior, including undocumented quirks, error codes, field ordering, timing and
pagination defaults, becomes a de facto contract once someone depends on it. Design implications:

- **Be intentional about what you expose.** A Resource is an explicit allow-list: every field
  it emits is a commitment. Never return a raw model dump.
- **Do not leak implementation details.** Column names, internal ids, stack traces and SQL
  errors are observable, and so they will be depended on.
- **Plan for deprecation at design time.** See the `deprecation-and-migration` skill
  (`.claude/skills/deprecation-and-migration/SKILL.md`) for removing things people depend on.
- **Tests are not enough.** Contract tests cannot catch a consumer relying on undocumented
  behavior. Public facades and container bindings are covered by the release non-regression
  rules for exactly this reason.

### The One-Version Rule

Avoid forcing consumers to choose between multiple versions of the same API or dependency.
Diamond dependency problems appear when different consumers need different versions of the same
thing. Design for a world where one version exists at a time: extend rather than fork. A
`/api/v1` prefix is a safety valve for a genuinely incompatible redesign, not a license to run
`v1` and `v2` side by side indefinitely.

### 1. Contract First

Define the interface before implementing it. The contract is the spec; the implementation
follows. In Python, a `Protocol` plus typed input and output models is the contract:

```python
from typing import Protocol

from app.Domain.Tasks.types import CreateTaskInput, ListTasksParams, TaskId, UpdateTaskInput
from app.Models.Task import Task
from craft.support.collection import Collection


class TaskService(Protocol):
    """Task use cases, resolved from the container by controllers and jobs."""

    def create_task(self, data: CreateTaskInput, owner_id: int) -> Task:
        """Create a task and return it with server-generated fields."""

    def list_tasks(self, params: ListTasksParams) -> Collection:
        """Return one page of tasks matching the filters, with pagination metadata."""

    def get_task(self, task_id: TaskId) -> Task:
        """Return one task or raise TaskNotFoundError."""

    def update_task(self, task_id: TaskId, data: UpdateTaskInput) -> Task:
        """Apply a partial update; only provided fields change."""

    def archive_task(self, task_id: TaskId) -> None:
        """Soft-delete the task; succeeds if it is already archived."""
```

Controllers never instantiate the service; they resolve it from the container, which is what
keeps them thin and mockable in `pytest`.

### 2. Consistent Error Semantics

Pick one error strategy and use it everywhere. In Craft projects every JSON error uses the same
envelope: a stable machine `code`, a translation `message_key`, and `params` for interpolation.
Never a rendered sentence; the client resolves the key in the user's locale.

```json
{
  "error": {
    "code": "TASK_TITLE_TAKEN",
    "message_key": "task.create.title_taken",
    "params": { "title": "Weekly report" }
  }
}
```

Raise typed exceptions that carry the contract, from the service layer:

```python
class DomainError(Exception):
    """Base class for business rule violations exposed to the transport layer."""

    code: str = "DOMAIN_ERROR"
    message_key: str = "error.generic"
    status_code: int = 422

    def __init__(self, **params: object) -> None:
        super().__init__(self.code)
        self.params = params


class TaskTitleTakenError(DomainError):
    """Raised when the owner already has an open task with the same title."""

    code = "TASK_TITLE_TAKEN"
    message_key = "task.create.title_taken"
    status_code = 409
```

The framework's `ExceptionHandler` (bound in the container as `exception_handler`) turns
exceptions into responses and reads `status_code` from the exception; its default JSON payload
is `{"message", "status", "errors"}`. A project that exposes an API subclasses it, overrides
`to_payload()` to emit the envelope above, and rebinds it in a service provider, so every
endpoint shares one shape. Validation failures map to the same envelope with the field errors in
`params`.

Status code mapping:

| Status | Meaning |
|---|---|
| 400 | The client sent malformed input |
| 401 | Not authenticated |
| 403 | Authenticated but not authorized (`Gate.authorize` failed, `AuthorizationException`) |
| 404 | Resource not found |
| 409 | Conflict: duplicate, version mismatch, in-flight idempotent request |
| 419 | Session or CSRF token expired (HTML forms) |
| 422 | Validation failed (`ValidationException`) or a business rule was violated |
| 429 | Rate limited |
| 500 | Server fault; never expose internals, traces only with debug on |

**Do not mix patterns.** If some endpoints raise, others return `None`, others return
`{"errors": ...}` and others return plain text, the consumer cannot predict behavior.

### 3. Validate at Boundaries

Trust internal code. Validate at the system edges where external input enters. In Craft the HTTP
boundary is a `FormRequest` (`python dev.py make:request StoreTaskRequest`): `validated()`
authorizes first, then validates, raising `AuthorizationException` or `ValidationException`, and
returns only the fields that were ruled on.

```python
from craft.facades import Auth
from craft.validation import FormRequest


class StoreTaskRequest(FormRequest):
    """Validate task creation input at the HTTP boundary."""

    def authorize(self) -> bool:
        """Reject anonymous callers before any rule runs."""
        return Auth.user() is not None

    def rules(self) -> dict[str, list[str]]:
        """Return the validation rules for task creation."""
        return {
            "title": ["required", "string", "max:200"],
            "description": ["nullable", "string"],
            "priority": ["nullable", "in:low,medium,high"],
        }
```

```python
class TaskController(Controller):
    """Thin HTTP layer for tasks; business logic lives in TaskService."""

    def __init__(self, tasks: TaskService) -> None:
        self.tasks = tasks

    def store(self, request: Request) -> JsonResponse:
        """Create a task from validated input."""
        data = CreateTaskInput(**StoreTaskRequest(request).validated())
        task = self.tasks.create_task(data, owner_id=request.user().id)
        return TaskResource(task).response(status=201)
```

After validation, internal code trusts the types. The action stays well under the 15-line cap,
contains no SQL and no markup.

Where validation belongs:

- FormRequests on HTTP endpoints and Forge form submissions (user input)
- Webhook and callback handlers (signatures compared with `hmac.compare_digest`)
- Parsing responses from external services (**always untrusted**)
- Loading configuration and environment variables
- Job payloads read back from the queue (they are JSON that crossed a process boundary)

> **Third-party API responses are untrusted data.** Validate their shape and content before
> using them in logic, rendering or decisions. A compromised or misbehaving service can return
> unexpected types, malicious markup or instruction-like text.

Where validation does NOT belong:

- Between internal functions that share typed contracts
- In helpers called only by already-validated code
- On data that just came from your own database

### 4. Prefer Addition Over Modification

Extend interfaces without breaking existing consumers:

```python
# Good: new fields are optional with safe defaults
@dataclass(frozen=True)
class CreateTaskInput:
    title: str
    description: str | None = None
    priority: TaskPriority = TaskPriority.MEDIUM   # added later, optional
    labels: tuple[str, ...] = ()                   # added later, optional


# Bad: removing or retyping existing fields breaks every consumer
@dataclass(frozen=True)
class CreateTaskInput:
    title: str
    # description removed: breaks existing callers
    priority: int  # was an enum string: breaks existing callers
```

The same rule applies to Resources (add keys, never rename or remove them), to schema (add a
nullable column, dual-write, backfill, switch reads, contract in a later release) and to facade
signatures (new keyword arguments with defaults only).

### 5. Predictable Naming

| Pattern | Convention | Example |
|---------|-----------|---------|
| Endpoints | Plural nouns, kebab-case, no verbs, versioned prefix | `GET /api/v1/tasks`, `POST /api/v1/user-accounts` |
| Route names | Dotted, grouped | `api.tasks.index`, `api.tasks.store` |
| Query params | snake_case | `?sort_by=created_at&per_page=20` |
| Response fields | snake_case, never localized | `{ "created_at", "updated_at", "task_id" }` |
| Boolean fields | `is_` / `has_` / `can_` prefix | `is_complete`, `has_attachments` |
| Enum values (persisted and serialized) | lowercase snake_case | `"in_progress"`, `"completed"` |
| Enum labels shown to users | Translation key | `task.status.in_progress` |
| Error codes | UPPER_SNAKE, domain-prefixed | `TASK_TITLE_TAKEN` |
| Money | Integer minor units + ISO-4217 code | `{ "amount_cents": 12900, "currency": "BRL" }` |
| Timestamps | UTC, ISO 8601 | `"2026-01-15T14:03:00Z"` |

Field names are part of the contract: never translated, never renamed per market.

### 6. Honouring an Idempotency Key

Accepting an `Idempotency-Key` header is the contract. Honouring it is the implementation, and it
is where money is lost. A key the server accepts but handles carelessly is worse than no key,
because the client now believes retrying is safe.

**Derive the key from the intent, not the attempt.** It must be stable across retries of one
intent and different across distinct intents:

```python
str(uuid.uuid4())                           # wrong: new key per attempt, every retry charges again
f"{user_id}:{amount_cents}"                 # wrong: two legitimate charges of the same amount collapse
f"{order_id}:{time.time()}"                 # wrong: a timestamp is a random key in disguise

request.headers.get("idempotency-key")      # right: the client generates it once and reuses it on retry
f"charge:v1:{order_id}"                     # right: derived from an immutable identifier
```

The key comes from the client or the initiating event, never from the layer doing the retrying.

**Claim atomically. A check followed by an act is a race.** Back the key with a unique
constraint in a forward-only migration:

```python
from craft.migrations import Schema


def up() -> None:
    """Create the idempotency key store."""
    Schema.create_table("idempotency_keys", lambda t: (
        t.id(),
        t.string("key").unique(),
        t.string("request_hash"),
        t.string("state"),
        t.jsonb("response").nullable(),
        t.timestamps(),
    ))
```

```python
# Wrong (TOCTOU): two concurrent retries both read "not seen", both charge.
if not self.keys.exists(key):
    self.gateway.charge(amount_cents, currency)
    self.keys.record(key)

# Right: let the unique constraint pick the winner.
try:
    self.keys.claim(key, request_hash)       # INSERT ... state = 'in_progress'
except DuplicateIdempotencyKeyError:
    return self._replay_or_reject(key, request_hash)
result = self.gateway.charge(amount_cents, currency)
self.keys.complete(key, result)
```

The repository owns the SQL and translates the database driver's unique-violation error into the
typed `DuplicateIdempotencyKeyError`; the service never sees SQL and never catches a broad
`Exception`. The unique constraint *is* the mechanism: a store that cannot enforce uniqueness in
one operation cannot back this.

**Guard the payload.** The same key with a different body is a client bug and must fail loudly
instead of serving the first response to a second request:

```python
if not hmac.compare_digest(existing.request_hash, request_hash):
    raise IdempotencyKeyReusedError(key=key)   # 422, code IDEMPOTENCY_KEY_REUSED
```

**Decide what an in-flight duplicate gets.** The first request is still running when the second
arrives, which is the common case during retry storms:

| Strategy | Response | Use when |
|---|---|---|
| Reject | `409 Conflict` | The client can retry later; simplest and safest |
| Wait | Block for the result, bounded | The caller needs the result synchronously |
| Return pending | `202` + status URL, work continues in a queued job | Long-running effects |

Never let the second caller through because the first "seems stuck". A stalled attempt whose fate
is unknown is exactly when duplicating costs most.

**Every call has three outcomes, not two: success, failure and unknown.** A timeout says nothing
about whether the effect applied. Record the intent *before* calling out, so a crash between the
call and the response leaves evidence for a reconciliation job to resolve, rather than a silently
retried charge.

**Set retention from the longest retry chain,** not from disk cost. Keys must outlive every path
that can redeliver the same intent, including a failed queue job retried days later and any
payment dispute window. A 24-hour key TTL behind a 7-day retry path is a duplicate waiting to
happen. Expire keys by state and timestamp, never by wiping the table.

## REST API Patterns

### Resource Design

`Route.api_resource()` registers the standard JSON routes (index, store, show, update, destroy)
without the HTML-only create and edit pages; `write_middleware` guards only the state-changing
actions:

```python
from craft.facades import Route

from app.Http.Controllers.Tasks.TaskCommentController import TaskCommentController
from app.Http.Controllers.Tasks.TaskController import TaskController

Route.group(
    lambda: (
        Route.api_resource("tasks", TaskController, write_middleware="api"),
        Route.patch("/tasks/{id}", [TaskController, "patch"]).name("tasks.patch"),
        Route.get("/tasks/{id}/comments", [TaskCommentController, "index"]).name("tasks.comments.index"),
        Route.post("/tasks/{id}/comments", [TaskCommentController, "store"]).name("tasks.comments.store"),
    ),
    prefix="/api/v1",
    name="api.",
)
```

```
GET    /api/v1/tasks                -> list tasks (query params filter)
POST   /api/v1/tasks                -> create a task
GET    /api/v1/tasks/{id}           -> get one task
PUT    /api/v1/tasks/{id}           -> replace a task
PATCH  /api/v1/tasks/{id}           -> partial update
DELETE /api/v1/tasks/{id}           -> archive a task (soft delete)

GET    /api/v1/tasks/{id}/comments  -> list comments for a task (sub-resource)
POST   /api/v1/tasks/{id}/comments  -> add a comment
```

`DELETE` on a business entity is a soft delete (`deleted_at` or `is_active = false`), never a
physical `DELETE`. Confirm the route table with `python dev.py route:list`.

### Pagination

Paginate every list endpoint. The query builder's `paginate(per_page, page)` caps `per_page` at
100 and attaches pagination metadata to the collection; `ResourceCollection.response()` emits it
under `meta`:

```python
def index(self, request: Request) -> JsonResponse:
    """List one page of tasks."""
    params = ListTasksParams.from_query(request.all())
    page = self.tasks.list_tasks(params)
    return TaskResource.collection(page).response()
```

```
GET /api/v1/tasks?page=1&per_page=20&sort_by=created_at&sort_order=desc
```

```json
{
  "data": [ { "id": 7, "title": "Weekly report", "status": "in_progress" } ],
  "meta": {
    "total": 142,
    "per_page": 20,
    "current_page": 1,
    "last_page": 8
  }
}
```

Whitelist `sort_by` against known columns; never interpolate it into SQL.

### Filtering

Use query parameters for filters:

```
GET /api/v1/tasks?status=in_progress&assignee_id=123&created_after=2026-01-01
```

Validate filter values like any other input (enum membership, integer ids, ISO dates) before they
reach the repository.

### Partial Updates (PATCH)

Accept partial objects and change only what was sent:

```
PATCH /api/v1/tasks/123
{ "title": "Updated title" }
```

Validate with rules that do not require absent fields, and pass only the provided keys
(`validated()` returns only ruled-on fields that were present) to the service.

## Python Type Patterns

### Model Variants Explicitly

Use one dataclass per variant and `match` for exhaustive handling, instead of a bag of optional
fields:

```python
@dataclass(frozen=True)
class Pending:
    pass


@dataclass(frozen=True)
class InProgress:
    assignee_id: int
    started_at: datetime


@dataclass(frozen=True)
class Completed:
    completed_by: int
    completed_at: datetime


type TaskState = Pending | InProgress | Completed


def status_key(state: TaskState) -> str:
    """Return the translation key that labels a task state."""
    match state:
        case Pending():
            return "task.status.pending"
        case InProgress():
            return "task.status.in_progress"
        case Completed():
            return "task.status.completed"
```

The server returns the machine value (`"in_progress"`); the label is a translation key resolved
in the presentation layer, never a sentence built in the domain.

### Input/Output Separation

```python
# Input: what the caller provides, validated by a FormRequest.
@dataclass(frozen=True)
class CreateTaskInput:
    title: str
    description: str | None = None


# Output: what the system returns, including server-generated fields.
class TaskResource(Resource):
    """Public representation of a task."""

    def to_array(self, request: Request | None = None) -> dict[str, object]:
        """Return the allow-listed task fields."""
        task = self.resource
        return {
            "id": task.get_attribute("id"),
            "title": task.get_attribute("title"),
            "description": task.get_attribute("description"),
            "status": task.get_attribute("status"),
            "created_by": task.get_attribute("user_id"),
            "created_at": task.get_attribute("created_at"),
            "updated_at": task.get_attribute("updated_at"),
        }
```

`python dev.py make:resource TaskResource` generates the class. A Resource is independent of the
model's hidden attributes: it is an explicit allow-list, so a new column never leaks by accident.

### Distinct Types for IDs

```python
from typing import NewType

TaskId = NewType("TaskId", int)
UserId = NewType("UserId", int)


def get_task(task_id: TaskId) -> Task:
    """Return one task by id."""
```

`mypy` then rejects passing a `UserId` where a `TaskId` is expected.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "We'll document the API later" | The types, FormRequests and Resources are the documentation. Define them first. |
| "We don't need pagination yet" | You will the moment someone has 100+ rows. `paginate()` costs one call. |
| "PATCH is complicated, let's just use PUT" | PUT requires the full object every time. PATCH is what clients want. |
| "We'll version the API when we need to" | Breaking changes without a plan break consumers. Design for extension from the start. |
| "Nobody uses that undocumented behavior" | Hyrum's Law: if it is observable, somebody depends on it. |
| "We can just maintain two versions" | Multiple versions multiply maintenance and create diamond dependencies. Prefer the One-Version Rule. |
| "Internal APIs don't need contracts" | Internal consumers are still consumers. Contracts prevent coupling and enable parallel work. |
| "A plain English message in the error is friendlier" | It is untranslatable and becomes a contract. Return `code` + `message_key` + `params`. |
| "Returning the model's `to_dict()` is faster" | It leaks every column you add later. Use a Resource. |
| "Accepting the Idempotency-Key header is enough" | The header is the contract; storing the key against the result is the implementation. |
| "Our queue guarantees exactly-once delivery" | No queue does across a worker crash. Design for at-least-once with idempotent processing. |
| "Duplicate requests are rare" | They are correlated: retries spike exactly when a dependency is degraded. |

## Red Flags

- Endpoints that return different shapes depending on conditions
- Error responses that differ between endpoints, or contain rendered sentences instead of `code` + `message_key`
- Validation scattered through services instead of FormRequests at the boundary
- Controllers instantiating services, running queries or exceeding 15 lines per action
- Breaking changes to existing fields (type changes, renames, removals)
- List endpoints without pagination, or a `per_page` the client can raise without limit
- Verbs in URLs (`/api/v1/createTask`, `/api/v1/getUsers`)
- Localized field names or enum values in the payload
- Money as floats or formatted strings
- Third-party API responses used without validation
- A `SELECT` for an idempotency key followed by an `INSERT`: that is a race, not a guard
- An idempotency key derived from a UUID, timestamp or anything regenerated per attempt
- The same key accepted with a different body, silently returning the first response
- Key retention shorter than the longest path that can redeliver the request

## Verification

After designing an API:

- [ ] Every endpoint has a FormRequest for input and a Resource for output
- [ ] Every error response uses `{ "error": { "code", "message_key", "params" } }`
- [ ] Every `message_key` has rows for `en`, `pt-BR` and `es` in the translation store
- [ ] Validation happens at boundaries only
- [ ] List endpoints paginate and return `data` + `meta`
- [ ] New fields are additive and optional (backward compatible)
- [ ] Naming is consistent: snake_case fields, kebab-case plural routes, UPPER_SNAKE error codes
- [ ] Controllers resolve services from the container and respect the layer caps
- [ ] State-changing endpoints either honour an idempotency key or are documented as unsafe to retry
- [ ] The key is claimed in one atomic operation guarded by a unique constraint
- [ ] A reused key with a different payload fails loudly
- [ ] The in-flight duplicate response is a deliberate choice (409, wait, or 202)
- [ ] Key retention outlives the longest retry path
- [ ] Feature tests in `tests/` cover success, validation failure, authorization failure and not-found
- [ ] `python -m pytest tests`, `python .claude/rules/lint_language.py` and `python .claude/rules/lint_structure.py` pass
