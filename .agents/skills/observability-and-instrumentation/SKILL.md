---
name: observability-and-instrumentation
description: Instruments Craft Engine code so production behavior is visible and diagnosable through structured logs, metrics, traces and alerts. Use when adding logging, metrics, tracing or alerting, when shipping any feature that runs in production and needs evidence it works, or when production issues are reported but the available data cannot say what happened.
---

# Observability and Instrumentation

## Overview

Code you cannot observe is code you cannot operate. Observability is the ability to answer
"what is the system doing, and why?" from the outside, using the telemetry the code emits.
Instrumentation is not a post-launch add-on — it is written alongside the feature, the same
way tests are. If a feature ships without telemetry, the first user-reported bug becomes
archaeology instead of a query.

Craft gives you the foundation: `RequestContext` assigns every request an id and records
request metrics, `JsonFormatter` emits one JSON object per log line with that id as a field,
the `Log` facade is the configured `craft` logger, `engine.support.metrics.registry` exposes
counters, histograms and gauges in the Prometheus text format, and `/health` / `/ready`
probes are mounted outside the middleware stack. This skill covers using that foundation and
filling the gaps it leaves: background jobs, external calls, tracing and alerting.

## When to Use

- Building any feature that will run in production
- Adding a new endpoint, service, queued job, scheduled task, event listener or external integration
- A production incident took too long to diagnose ("we could not tell what happened")
- Setting up or reviewing alerting rules
- Reviewing a change that adds I/O, retries, queues or cross-service calls

**NOT for:**

- Diagnosing a failure happening right now — use the `debugging-and-error-recovery` skill
  (`.claude/skills/debugging-and-error-recovery/SKILL.md`); observability is what makes that
  skill fast next time
- Profiling and optimizing measured slowness — use the `performance-optimization` skill
  (`.claude/skills/performance-optimization/SKILL.md`)
- Launch-day monitoring checklists and rollback triggers — see the `shipping-and-launch` skill
  (`.claude/skills/shipping-and-launch/SKILL.md`); this skill covers the instrumentation that feeds them

## Process

### 1. Define "working" before instrumenting

Telemetry without a question is noise. Before adding any instrumentation, write down two to
four questions an on-call engineer will ask about this feature:

```text
FEATURE: bank slip payment confirmation (webhook + reconciliation job)
QUESTIONS ON-CALL WILL ASK:
1. What fraction of bank slips are confirmed by webhook vs by the nightly reconciliation?
2. When a confirmation fails permanently, why? (bad signature? unknown slip? provider timeout?)
3. Is the payment provider slower than usual?
4. Is the reconciliation queue falling behind?
→ Every signal below must help answer one of these.
```

If you cannot name the questions, you are not ready to instrument — you will log everything
and learn nothing. Put the questions in the spec (`.claude/skills/spec-driven-development/SKILL.md`).

### 2. Pick the right signal for each question

| Signal | Answers | Cost profile | Example |
|---|---|---|---|
| **Structured log** | "What happened in this specific case?" | Per event; grows with traffic | `bank_slip_confirmation_failed` with the provider error code |
| **Metric** | "How often, how fast, in aggregate?" | Fixed per series; cheap to query | p99 duration of provider calls |
| **Trace** | "Where did the time go across hops?" | Per request; usually sampled | One slow checkout, broken down by database, provider and queue |

Rule of thumb: metrics tell you **that** something is wrong, traces tell you **where**, logs
tell you **why**.

### 3. Structured logging

Log events, not prose. Every line is a JSON object with a stable event name and
machine-readable fields. Enable the JSON formatter in production:

```ini
# .env (production)
LOG_CHANNEL=stderr     # containers log to stdout/stderr and a platform collects it
LOG_FORMAT=json        # one JSON object per line; `text` is for a terminal
```

Log messages are English, structured and for engineers — they are not user-facing copy and
never go through the translation store.

```python
# BAD: interpolated prose — unqueryable, inconsistent, and it formats even when filtered out
Log.warning(f"Bank slip {slip.id} failed for user {user.id} after {attempt} retries")

# GOOD: stable event name + structured fields through `extra=`
Log.warning(
    "bank_slip_confirmation_failed",
    extra={
        "bank_slip_id": slip.get_attribute("id"),
        "provider": "acquirer_a",
        "error_code": error.code,
        "attempt": attempt,
    },
)
```

`JsonFormatter` promotes `request_id`, `method`, `path`, `status`, `duration_ms` and
`user_id` to top-level fields when they are in the request context, copies every `extra=`
field into the payload, and serializes exceptions (type, message, stack) when you log with
`exc_info=True`. Timestamps are UTC.

**Log levels — use them consistently:**

| Level | Meaning | On-call action |
|---|---|---|
| `error` | Invariant broken; someone may need to act | Investigate |
| `warning` | Degraded but handled (retry succeeded, fallback used) | Watch for trends |
| `info` | Significant business event (order placed, job finished) | None |
| `debug` | Diagnostic detail | Off in production by default |

The shipped channels default to `level: "debug"`; set the production channel's level to
`info` in `config/logging.py`.

**Correlation ids are mandatory.** `RequestContext` is the first global middleware: it accepts
an inbound `X-Request-ID` only after validating its length and characters (the header is
attacker-controlled — a newline in it would forge log entries), generates one otherwise,
binds it to the request context and echoes it on the response. Every log line written during
the request carries it automatically through `RequestContextFilter`.

Add your own fields to the context once, instead of repeating them on every call:

```python
from craft.support import context

context.put(user_id=request.user().get_attribute("id"), tenant_id=tenant.get_attribute("id"))
```

Propagate the id on every outbound call so the next service can continue the story:

```python
headers = {"X-Request-ID": context.request_id() or context.new_request_id()}
```

**Background work has no request.** Queued jobs serialize to JSON and run in a worker, where
the request context no longer exists — so the id has to travel in the payload and be bound
again in the worker:

```python
class ReconcileBankSlipJob(Job):
    """Reconciles one bank slip against the provider."""

    def __init__(self, bank_slip_id: int, request_id: str | None, entry_point: str) -> None:
        self.bank_slip_id = bank_slip_id
        self.request_id = request_id
        self.entry_point = entry_point

    def handle(self) -> None:
        """Run the reconciliation under the originating correlation id."""
        with context.bind(
            request_id=self.request_id or context.new_request_id(),
            entry_point=self.entry_point,
            bank_slip_id=self.bank_slip_id,
        ):
            # The service is resolved from the container, never instantiated here.
            self.reconciliation_service().run(self.bank_slip_id)
```

`context.bind()` restores the previous context when the block ends, which is what keeps a
pooled worker from stamping the next job with this job's id.

**When several entry points write to one log, name the entry point.** A correlation id
identifies a run; it does not say which code path started it. The same job reached by the
scheduler, by a replay endpoint and by a manual `python dev.py` run produces interchangeable
lines in one sink, so attributing a line falls back to elimination — cross-reading the
scheduler's history, the process table, a deploy log — and that argument holds only as long
as those external records still exist. Stamp the entry point where the run starts, next to
the correlation id, and propagate both the same way:

```python
EntryPoint = Literal["scheduler", "replay_endpoint", "cli", "webhook"]


@contextlib.contextmanager
def run_context(entry_point: EntryPoint, run_id: str | None = None) -> Iterator[dict[str, Any]]:
    """Bind the entry point and a run id for everything logged inside the block.

    Args:
        entry_point: The code path that started this run.
        run_id: An existing correlation id to continue, if there is one.

    Yields:
        The bound context.
    """
    with context.bind(entry_point=entry_point, request_id=run_id or context.new_request_id()) as bound:
        yield bound

# scheduled task          -> with run_context("scheduler"): ...
# POST /jobs/{id}/replay  -> with run_context("replay_endpoint", context.request_id()): ...
# CLI invocation          -> with run_context("cli", os.environ.get("RUN_ID")): ...
```

Name the field `entry_point`, not `source`: common log schemas reserve `source.*` for network
fields. Both fields must cross the same boundaries as the correlation id — job payloads, HTTP
headers — or a worker re-derives the entry point and guesses. A field that merely correlates
with an entry point is a hint, not an attribution: anything that can invoke the job can
reproduce it.

**Never log secrets, tokens, passwords or unredacted personal data.** This is a hard rule from
the `security-and-hardening` skill (`.claude/skills/security-and-hardening/SKILL.md`) —
telemetry pipelines are a classic data-leak path, and a log line full of personal data is a
retention and erasure problem under LGPD and GDPR. Allowlist fields; never log whole request
bodies, `request.all()`, headers such as `Authorization` or `Cookie`, or a model's `to_dict()`.
Log ids, not names, e-mails or `CPF` numbers.

### 4. Metrics

For request-driven work, instrument **RED** on every endpoint and every external dependency:
**R**ate (requests per second), **E**rrors (failure rate), **D**uration (a latency histogram,
not an average). For resources — queues, connection pools, hosts — use **USE**:
**U**tilization, **S**aturation, **E**rrors.

Craft already records RED for HTTP: `RequestContext` observes
`craft_request_duration_seconds{method, route}` and increments
`craft_requests_total{method, route, status}` for every request, and the exception handler
counts `craft_exceptions_total`. The `craft_db_pool_connections{connection, state}` gauge
reports pool occupancy — `open` equal to `limit` sustained is the shape of a connection leak.

Expose them, protected:

```ini
METRICS_ENABLED=true
METRICS_PATH=/metrics
METRICS_TOKEN=<long random value>   # the scraper sends it as a bearer token
```

The payload names every route, so keep the endpoint on a private network as well as behind
the token. The registry is per process: scrape each worker and let the collector sum.

Instrument what the framework cannot see — external dependencies, queues and business
outcomes — with the same registry:

```python
import time

from craft.support.metrics import registry

PROVIDER_BUCKETS: tuple[float, ...] = (0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
registry.histogram("payment_provider_request_duration_seconds", "Provider call duration.", PROVIDER_BUCKETS)
registry.counter("payment_provider_requests_total", "Provider calls, by operation and outcome.")


def timed_provider_call(operation: str, call: Callable[[], ProviderResponse]) -> ProviderResponse:
    """Run a provider call and record its duration and outcome.

    Args:
        operation: A fixed operation name such as `confirm_bank_slip`.
        call: The call to execute.

    Returns:
        The provider response.
    """
    started = time.monotonic()
    outcome = "error"
    try:
        response = call()
        outcome = "ok" if response.ok else "rejected"
        return response
    finally:
        registry.observe(
            "payment_provider_request_duration_seconds",
            time.monotonic() - started,
            provider="acquirer_a",
            operation=operation,
        )
        registry.increment(
            "payment_provider_requests_total", provider="acquirer_a", operation=operation, outcome=outcome
        )
```

A shared wrapper like this belongs in `app/plugins/`, resolved from the container, so every
module times its dependencies the same way.

**Cardinality is the failure mode.** Every unique label combination is a separate time series.
Labels must come from small, fixed sets — route pattern, status, provider, operation, outcome.
Never use user ids, tenant ids, e-mails, raw URLs, request ids or error message text as labels;
those belong in logs and traces. Craft's own `route` label is the matched pattern
(`/posts/{id}`), never the raw path, and unmatched requests collapse into `unmatched` for the
same reason.

```text
OK as label:    route="/api/tasks/{id}"   status="503"   provider="acquirer_a"   outcome="rejected"
NEVER a label:  user_id, tenant_id, email, request_id, full URL, error message text
```

Status codes are a bounded set, but dashboards and alerts should group them by class (`5xx`)
in the query rather than alerting per code.

Track averages never, percentiles always: an average hides the 1% of users having a terrible
time. Record histograms and read p50, p95 and p99.

### 5. Distributed tracing

Craft does not ship a tracer; use OpenTelemetry — the vendor-neutral standard — through its
Python SDK. The ASGI instrumentation wraps the application object built in `bootstrap/app.py`,
and client instrumentations cover outbound HTTP and the PostgreSQL driver:

```python
# bootstrap/tracing.py — imported by the ASGI entry point before the app is built
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatio


def configure_tracing(service_name: str, sample_ratio: float) -> None:
    """Install the global tracer provider and database instrumentation.

    Args:
        service_name: The name the tracing backend groups spans under.
        sample_ratio: Fraction of new traces to record, between 0 and 1.
    """
    provider = TracerProvider(
        resource=Resource.create({"service.name": service_name}),
        sampler=ParentBasedTraceIdRatio(sample_ratio),
    )
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)
    Psycopg2Instrumentor().instrument()
```

```python
# bootstrap/app.py — after the kernel has built `asgi_app`
from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware

asgi_app = OpenTelemetryMiddleware(asgi_app)
```

Verify the exact package names and versions against the OpenTelemetry Python documentation
before pinning them; add them to `pyproject.toml` and the pinned dependency set, and record
the change in `CHANGELOG.md`.

Add manual spans only around meaningful internal units of work (`apply_discounts`,
`charge_provider`) and attach the attributes on-call will filter by — ids and outcomes, never
personal data. Put the trace id into the log context as well, so a log line leads to its trace.
Propagate context across every async boundary — W3C `traceparent` on outbound HTTP, and the
trace context inside queued job payloads next to `request_id` — or the trace dies at the gap.
Sample head-based at a low rate by default; keep 100% of errors if the backend supports tail
sampling.

### 6. Alerting

Alert on **symptoms users feel**, not on causes:

```text
SYMPTOM (page-worthy):              CAUSE (dashboard, not a page):
5xx rate > 1% for 5 min             CPU at 85%
p99 latency > 2s for 10 min         one worker restarted
oldest queued job > 10 min          disk at 70%
/ready failing on all instances     pool at 80% of limit
```

Cause-based alerts fire when nothing is wrong and miss failures you did not predict.
Symptom-based alerts fire exactly when users are hurt, whatever the cause.

Rules for every alert you create:

1. **It must be actionable.** If the response is "ignore it, it self-heals", delete the alert.
2. **It links to a runbook** — even three lines: what it means, the first query to run, the escalation path.
3. **It has a threshold and duration** justified by the SLO or by historical data, not by a guess.
4. Use two severities only: **page** (user-facing, act now) and **ticket** (degradation, act this week). A third tier becomes noise that trains people to ignore everything.

Use the probes the framework mounts: `/health` is liveness and touches nothing external, so a
database incident does not get every healthy instance restarted; `/ready` checks the database
and cache and is what a load balancer should gate traffic on.

#### Writing Runbooks

Rule 2 requires every alert to link to a runbook. A runbook answers three questions without
requiring the reader to think: what is happening, what to check first, and who to call if that
does not resolve it. Store runbooks in `docs/runbooks/`, named after the alert, in English like
every committed document.

**Minimum viable runbook (three lines):**

```markdown
# Runbook: High 5xx Rate on /api/tasks
**Means:** database connection pool likely exhausted, or a bad deploy.
**First check:** `craft_db_pool_connections{state="open"}` vs `{state="limit"}` on /metrics, then
  `SELECT count(*) FROM pg_stat_activity WHERE backend_type = 'client backend';`
**Escalate to:** the database on-call, then the engineering on-call rotation.
```

**When to expand beyond three lines:** add steps only when the first check alone is not enough
to decide. A five-step runbook covering the three most common causes beats a twenty-step
document that covers every edge case and gets skimmed. A runbook never contains a destructive
command (`migrate:fresh`, `migrate:reset`, `db:wipe`, `db:drop`); recovery is forward-only.

**Keep runbooks current.** Update the runbook as part of closing every incident it was used in
— a stale runbook builds false confidence. If a step was wrong or missing, fix it before the
incident is marked resolved.

### 7. Verify the telemetry itself

Instrumentation is code; it can be wrong. Before calling the work done, trigger the paths and
look at the actual output:

- Force an error in staging → find it in the logs by `request_id` (taken from the response's
  `X-Request-ID` header); confirm fields are real JSON fields, not a repr string inside `message`
- Send test traffic → confirm the metric series appear on `/metrics` with the expected labels
  and sane values, and no label carries an unbounded value
- Enqueue a job from a request → confirm the worker's log lines carry the same `request_id`
  and the right `entry_point`
- Follow one request across hops in the tracing UI → no broken spans
- Fire each new alert once (lower the threshold temporarily) → confirm it reaches the right
  channel and the runbook link works

Lock the important parts in with `pytest`: assert that a handler emits the event name and
fields you depend on (`caplog`), that a metric is incremented (`registry.get(name)`, with
`registry.reset()` between tests), and that no secret or personal field appears in the record.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "I'll add logging after it works" | "After" becomes "after the first incident", the most expensive moment to discover you are blind. Instrument as you build. |
| "More logs = more observability" | Unstructured noise makes incidents slower, not faster. Three queryable events beat three hundred prose lines. |
| "`print()` is fine for now" | Unstructured output cannot be filtered, correlated or alerted on, and it bypasses the request id. `Log` with `extra=` costs the same keystrokes. |
| "The request id is automatic, so jobs are covered" | The context ends with the request. A job without the id in its payload writes orphan lines. |
| "We can just look at the dashboards when something breaks" | Dashboards built without defined questions show everything except the answer. Start from on-call questions. |
| "Alert on everything important, we'll tune later" | A noisy pager trains people to ignore it. The tuning never happens; the missed real page does. |
| "User id as a metric label makes debugging easier" | It also makes the metrics backend fall over. High-cardinality lookups belong in logs and traces. |
| "Tracing is overkill for one app and a database" | One app, a database, a queue and a payment provider already raise latency questions logs cannot answer. |
| "Logging the whole payload helps debugging" | It also copies personal data and secrets into a system with different access and retention. Allowlist fields. |

## Red Flags

- A change with retries, queues or external calls and zero new telemetry
- Log lines built with f-strings or `%` formatting instead of an event name and `extra=` fields
- `print()` in application code
- No correlation id — each log line is an orphan; jobs enqueued without the originating `request_id`
- One log stream fed by the scheduler, a webhook and manual runs, with no field naming which one produced the line
- Metrics labeled with user ids, tenant ids, raw URLs or error message text (cardinality bomb)
- Latency tracked as an average with no percentiles
- `/metrics` enabled without `METRICS_TOKEN` or on a public network
- Liveness probe that checks the database, so a database blip restarts every instance
- Alerts that fire daily and get acknowledged without action
- Alerts on causes (CPU, memory) paging humans while the user-facing error rate is unmonitored
- Secrets, tokens, `Authorization` or `Cookie` headers, full request bodies or personal data in logs or span attributes
- "It works on my machine" as the only evidence a production feature is healthy

## Verification

After instrumenting a feature, confirm:

- [ ] The on-call questions for this feature are written down, and each signal maps to one
- [ ] Production logs are JSON (`LOG_FORMAT=json`), with stable event names and a `request_id` on every line
- [ ] Queued jobs and scheduled tasks bind the originating `request_id` (or a fresh run id) with `context.bind()`
- [ ] Every log sink written by more than one entry point carries an `entry_point` field, set where the run starts and propagated with the correlation id rather than inferred downstream
- [ ] No secrets, tokens or unredacted personal data in any log line or span attribute (spot-check actual output)
- [ ] RED metrics exist for every new endpoint and every external dependency, with bounded label sets
- [ ] Latency is a histogram; p95 and p99 are queryable
- [ ] `/metrics` is protected by `METRICS_TOKEN` and network policy
- [ ] A single request can be followed end to end in the tracing UI without broken spans
- [ ] Every new alert is symptom-based, has a runbook link, and was test-fired once
- [ ] An induced failure in staging was located through telemetry alone, without reading the source
- [ ] Gates pass: `python -m pytest tests`, `ruff check engine`, `python .claude/rules/lint_language.py`, `python .claude/rules/lint_structure.py`
- [ ] `CHANGELOG.md` records the instrumentation under `## [Unreleased]`

For the at-a-glance version of this list, including the pre-launch instrumentation gate, see
`.claude/references/observability-checklist.md`.
