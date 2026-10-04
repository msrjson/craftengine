# Events & Queues

Craft features a synchronous Event Dispatcher to decouple logic within request lifecycles, and an asynchronous Queue System to execute heavy tasks in background processes.

---

## Events & Listeners

Events serve as placeholders indicating something has happened, and Listeners intercept those occurrences.

### 1. Defining the Event
Events are typically simple datastructure wrappers:

```python
class PostPublished:
    def __init__(self, post_id: str):
        self.post_id = post_id
```

### 2. Defining the Listener
Listeners define a synchronous `handle(event)` method. Declare it with plain `def` — the dispatcher calls handlers synchronously and never awaits them, so an `async def` handler would produce an un-run coroutine:

```python
from app.Models.Post import Post
from craft.facades import Log

class SendPostNotifications:
    def handle(self, event: PostPublished):
        post = Post.find(event.post_id)
        Log.info(f"Sending notifications for post: {post.title}")
```

### 3. Registering & Dispatching
Map your events to listeners inside your `EventServiceProvider` boot method:

```python
from craft.facades import Event

# Mapping (a single listener or a list both work)
Event.listen(PostPublished, [SendPostNotifications])

# Dispatching anywhere in your app code
Event.dispatch(PostPublished(post_id="post-uuid"))
```

Events can also be plain strings. A listener registered under a string name is
dispatched when that string (or an event object whose `name` attribute equals
it) is fired:

```python
Event.listen("user.created", lambda event: Log.info("user created"))
Event.dispatch("user.created")
```

### 4. The end of a request

The HTTP kernel names no subsystem. When a request finishes it emits
`RequestTerminated` on the worker thread that served it, through
`EventDispatcher.notify`: every listener runs, and one that raises is logged
without stopping the others. A listener that releases a per-request resource
registers with `listen_last`, so it runs after every other listener -
wildcards included - and survives `forget` and `flush`. The database returns
its pooled connection this way.

```python
from craft.facades import Event
from craft.events.lifecycle import RequestTerminated

Event.listen(RequestTerminated, lambda event: metrics.observe_request(event.request))
```

For calls between modules - not reactions - use the
[internal proxy](internal-proxy.md).

---

## Asynchronous Queues

Queue processing shifts time-consuming tasks (like email delivery or file parsing) to a background worker.

### Defining Jobs
Jobs inherit from the base class `craft.queue.Job`. They must define a synchronous `handle()` method — the worker calls `job.handle()` directly and never awaits it, so use plain `def`, not `async def`.

> [!CAUTION]
> **Strict JSON Serialization Requirement**:
> To prevent security vulnerabilities, Craft processes job payloads using JSON serialization rather than Python's `pickle` library.
> Do **NOT** pass complex object instances (such as database Model instances or connection objects) to Job constructor parameters.
> Instead, pass scalar attributes (such as database primary keys, strings, or numbers) and query the corresponding model instance from the database inside the job's `handle()` method.

```python
from craft.queue import Job
from app.Models.User import User
from craft.facades import Log

class SendWelcomeEmail(Job):
    def __init__(self, user_id: str):
        # Pass simple scalar types to the constructor
        self.user_id = user_id

    def handle(self):
        # Reload database models inside the handler
        user = User.find(self.user_id)
        if user:
            Log.info(f"Sending welcome email to: {user.email}")
```

### Dispatching Jobs
Push jobs to the queue using the `Queue` facade:

```python
from craft.facades import Queue

# Push the job into background processing
Queue.push(SendWelcomeEmail(user_id="user-uuid"))

# Make the job available only after a delay (database driver)
Queue.later(300, SendWelcomeEmail(user_id="user-uuid"))
```

### Drivers

- **`sync`** (default): `push()` runs the job inline, immediately. `later()`
  also runs immediately — the delay cannot be honoured without a backing store,
  so a warning is logged and the job executes inline.
- **`database`**: jobs are serialized to JSON into the `jobs` table and
  processed by a worker.

### Running the Worker
Background tasks are processed using the background queue worker command:

```bash
python dev.py queue:work
```
This starts a persistent loop polling the database queue for jobs and executing them.

With the database driver, workers claim jobs **atomically**: claiming a job
sets `reserved_at` and increments `attempts`, so two workers never run the same
job. A reservation older than 90 seconds (`retry_after`) is treated as a hung
worker and the job becomes claimable again. A job that raises is released for
retry; once it has been attempted 3 times (`max_attempts`), it is removed from
the queue and the failure is logged.

### Stopping a worker

On `SIGTERM` — what Docker, systemd and Kubernetes send before `SIGKILL` — the
worker finishes the job in hand and then exits, printing `Worker stopped
cleanly.` Killed mid-job instead, the job would stay reserved until the stale
sweep reclaimed it minutes later, and any side effect it had already performed
would happen twice on the retry.

Give the supervisor a grace period longer than your slowest job
(`terminationGracePeriodSeconds` on Kubernetes, `stop_grace_period` in
Compose). A second `SIGTERM` exits immediately: the handler stands down as it
fires, so an operator is never left with a process that ignores them.

## On PostgreSQL

The queue claims jobs with `SELECT ... FOR UPDATE SKIP LOCKED`, backs off
failures with jitter, keeps spent jobs in a `failed_jobs` dead-letter table,
and can wake instantly on `LISTEN`/`NOTIFY` instead of polling. See
[PostgreSQL](postgres.md#queues).
