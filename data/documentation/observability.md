# Observability

Three questions an incident asks, and what answers each:

| Question | Answer |
|---|---|
| Which request caused this? | A request id on every log line and every response |
| Is it slow, or is it failing? | The request duration histogram and the status counter |
| Who noticed, and where do I look? | An error reporter and the pool gauges |

None of it matters with one instance and a terminal open. All of it matters the
moment four workers interleave their output and the one line that explains the
outage looks exactly like the thousand around it.

## Request correlation

Every request gets an identifier, set by the `RequestContext` middleware before
anything else runs. It comes back on the response as `X-Request-ID`, appears on
every log line the request produces, and is handed to error reporters.

```text
GET /orders/42
< X-Request-ID: 9f2c1ab84e7d4c0b8a1e5f3d2c7b6a90
```

An inbound `X-Request-ID` is echoed rather than replaced, so a trace survives a
hop between services — but only after validation. The header is
attacker-controlled: an unbounded value bloats every log line it touches, and a
newline in one forges log entries outright. Anything that is not up to 128
characters of `[A-Za-z0-9._:-]` is discarded and a fresh identifier issued.

Read it anywhere in the request, without threading it through call signatures:

```python
from craft.support import context

context.request_id()          # the identifier, or None outside a request
context.current()             # {"request_id": ..., "method": ..., "path": ...}
context.put(user_id=user.id)  # add to it; every later log line carries it
```

It is a `ContextVar`, not a thread-local. That is the whole reason it works
here: the request chain runs on a pooled worker thread, and a thread-local
value left behind by one request would be attributed to the next request that
thread serves.

### The probes are outside this

`/health`, `/ready` and `/metrics` are dispatched outside the middleware
stack, so they carry no request id and are not counted. A scrape every ten
seconds would otherwise dominate the request metrics it exists to report. All
three are opt-in (`HEALTH_ROUTES_ENABLED`, `METRICS_ENABLED`) and, once on,
appear in `python dev.py route list` alongside the application's own routes.
Both carry a bearer token: `METRICS_TOKEN` hides `/metrics` entirely, while
`HEALTH_READINESS_TOKEN` unlocks the detail of `/ready` without hiding the
probe itself.

## Structured logging

```dotenv
LOG_FORMAT=json      # or `text`, the default outside containers
LOG_CHANNEL=stderr   # `stderr` defaults to json: containers log to stdout
```

`json` emits one object per line with the context as real fields, which is what
a log platform can filter and aggregate on:

```json
{"timestamp": "2026-08-27T14:02:11.4812+00:00", "level": "ERROR",
 "logger": "craft", "message": "payment_declined",
 "request_id": "9f2c1ab8", "method": "POST", "path": "/orders/{id}/pay",
 "order_id": 42,
 "exception": {"type": "PaymentDeclinedError", "message": "...", "stack": "..."}}
```

Anything passed through `extra=` becomes a field, so structure the data rather
than the sentence:

```python
log.warning("payment_declined", extra={"order_id": order.id, "issuer": code})
```

`text` keeps the readable format and appends `[request_id=…]`, so a terminal
stays legible while still being traceable.

## Metrics

A Prometheus scrape endpoint, **off by default**: the payload names every route
the application serves and how often each is hit, which is reconnaissance if it
is reachable from outside.

```dotenv
METRICS_ENABLED=true
METRICS_PATH=/metrics
METRICS_TOKEN=a-long-random-string   # optional bearer token
```

Keep it on an internal network, or set `METRICS_TOKEN` and have the scraper
send it as `Authorization: Bearer …`. A request without the token gets a `404`,
not a `401` — an endpoint that admits it exists is an endpoint worth guessing
at.

| Metric | Type | Labels |
|---|---|---|
| `craft_requests_total` | counter | `method`, `route`, `status` |
| `craft_request_duration_seconds` | histogram | `method`, `route` |
| `craft_exceptions_total` | counter | `exception` |
| `craft_db_pool_connections` | gauge | `connection`, `state` |

`route` is the matched pattern, never the raw path. `/posts/{id}` is one
series; `/posts/1`, `/posts/2` and the rest are as many series as there are
posts, which is how a metrics store is killed by the thing meant to observe it.

Record your own:

```python
from craft.support.metrics import registry

registry.increment("orders_placed_total", channel="web")
registry.observe("checkout_duration_seconds", elapsed, gateway="stripe")
registry.gauge("queue_depth", "Jobs waiting.", lambda: queue.size("default"))
```

The scope is one process. Each worker is scraped separately and the numbers are
summed by whatever collects them — which is how the format is meant to be used,
and the only honest answer: a counter shared between processes would need
shared memory this framework does not otherwise require.

### What to alert on

| Signal | Means |
|---|---|
| `craft_db_pool_connections{state="open"}` at `state="limit"`, sustained | A connection leak, or the pool is too small. Visible here before it shows in the error rate |
| `craft_exceptions_total` rising | Server faults, by exception class |
| `craft_request_duration_seconds` p99 climbing while the count is flat | Contention, not load |

## Error reporting

The log is where an exception is written down; a reporter is where it is
noticed. Register one at boot — the framework carries no vendor:

```python
# bootstrap/app.py, after the container is built
import sentry_sdk

handler = app.make("exception_handler")
handler.reporter(lambda exc, ctx: sentry_sdk.capture_exception(exc))
```

The callback receives the exception and the request context, so a report names
the request instead of arriving as an anonymous stack trace:

```python
def report_to_tracker(exception, request_context):
    tracker.capture(
        exception,
        tags={"request_id": request_context.get("request_id")},
        extra=request_context,
    )

handler.reporter(report_to_tracker)
```

Only server faults reach a reporter. A 404, a failed CSRF check or a validation
error is the client getting it wrong, and paging on those trains people to
ignore the pager. A reporter that raises is logged and skipped: an error
tracker being down is not a reason to lose the exception it was meant to
receive.

## Related

- [Deployment](deployment.md) — health probes, rolling deploys, the connection
  budget
- [Queues and events](queues_events.md) — worker shutdown and job failure
- [Configuration](configuration.md) — where these settings live
