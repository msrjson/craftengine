# Observability Checklist

Quick reference for instrumenting production code in Craft Engine applications. Use alongside
the `observability-and-instrumentation` skill
(`.claude/skills/observability-and-instrumentation/SKILL.md`).

## Table of Contents

- [On-Call Questions (Start Here)](#on-call-questions-start-here)
- [Structured Logging](#structured-logging)
- [Background Work](#background-work)
- [Metrics](#metrics)
- [Health Probes](#health-probes)
- [Distributed Tracing](#distributed-tracing)
- [Alerting](#alerting)
- [Dashboards](#dashboards)
- [Verify the Telemetry](#verify-the-telemetry)
- [Pre-Launch Gate](#pre-launch-gate)

## On-Call Questions (Start Here)

Telemetry without a question is noise. Before instrumenting anything:

- [ ] Two to four questions an on-call engineer will ask about this feature are written down (in the spec)
- [ ] Every signal below maps to one of those questions
- [ ] Each question is matched to the right signal type: metrics say **that** something is wrong, traces say **where**, logs say **why**

## Structured Logging

- [ ] Production uses `LOG_FORMAT=json` — one JSON object per line with stable event names, not free-form strings
- [ ] Production channel chosen deliberately (`LOG_CHANNEL=stderr` in containers) and its level set to `info`, not the shipped `debug`
- [ ] `RequestContext` is the first entry of the global middleware stack in `bootstrap/app.py`
- [ ] Every log line carries `request_id` — accepted from a validated `X-Request-ID` or generated at the boundary, and echoed on the response
- [ ] Log calls use an event name plus `extra=` fields (`Log.warning("bank_slip_confirmation_failed", extra={...})`), never f-strings or `%` formatting
- [ ] Request-wide fields (`user_id`, `tenant_id`) added once with `context.put()`, not repeated on every call
- [ ] `request_id` propagated on every outbound call (`X-Request-ID` header) and every async boundary (job payloads)
- [ ] Any log stream written by more than one entry point (scheduler, webhook, replay endpoint, manual `python dev.py` run) carries an `entry_point` field, set where the run starts and propagated alongside the correlation id
- [ ] Log levels are consistent: `error` = invariant broken, someone may act; `warning` = degraded but handled; `info` = significant business event; `debug` = off in production
- [ ] Exceptions logged with `exc_info=True` so the formatter records type, message and stack as fields
- [ ] Log messages are English and engineer-facing; they never pass through the translation store and never reach users
- [ ] No `print()` in application code
- [ ] No secrets, tokens, passwords or unredacted personal data in any log line (hard rule from the `security-and-hardening` skill)
- [ ] Fields are allowlisted — no `request.all()`, no whole request or response bodies, no `Authorization` or `Cookie` headers, no model `to_dict()` dumps
- [ ] Personal data referenced by id, never by name, e-mail or `CPF`; log retention set and compatible with LGPD / GDPR erasure obligations
- [ ] External service calls logged with metadata only: endpoint, status, latency, attempt count, sanitized identifiers
- [ ] Actual log output spot-checked: real JSON fields, not a repr string inside `message`

## Background Work

- [ ] Queued jobs carry the originating `request_id` (and trace context) in their JSON payload
- [ ] Job `handle()` binds that id with `context.bind(...)` so the worker's lines join the originating request
- [ ] Scheduled tasks and CLI runs bind a fresh run id and an `entry_point` at the start of the run
- [ ] Failed jobs are visible: `python dev.py queue` failed-job listing checked, and failures logged with job name, attempt and entity id
- [ ] Queue depth and age of the oldest pending job are measured for every queue
- [ ] Job processing duration recorded as a histogram, by job name (a bounded set)

## Metrics

- [ ] `METRICS_ENABLED=true` in production, with `METRICS_TOKEN` set and the endpoint reachable only from the private network
- [ ] The scraper collects each worker process separately (the registry is per process) and sums
- [ ] **RED** instrumented for every endpoint (covered by `craft_requests_total` and `craft_request_duration_seconds`) and every external dependency (added by the application): Rate, Errors, Duration
- [ ] **USE** instrumented for every resource (queues, connection pools, hosts): Utilization, Saturation, Errors — `craft_db_pool_connections` watched for `open` reaching `limit`
- [ ] `craft_exceptions_total` watched per exception class
- [ ] Latency is a histogram (`registry.histogram` with explicit buckets); p50, p95 and p99 are queryable — never an average
- [ ] Custom metrics declared once at boot with a description, recorded with `registry.increment` / `registry.observe`
- [ ] All labels come from small, fixed sets (route pattern, status, provider, operation, outcome)
- [ ] No unbounded label values: no user ids, tenant ids, e-mails, raw URLs, request ids or error message text
- [ ] Status codes grouped by class (`5xx`) in dashboards and alert queries
- [ ] Shared instrumentation wrappers (timing an external call) live in `app/plugins/` and are resolved from the container

## Health Probes

- [ ] `/health` (liveness) touches nothing external, so a database incident does not restart healthy instances
- [ ] `/ready` (readiness) checks the database and cache, and the load balancer gates traffic on it
- [ ] Probe paths match the orchestrator configuration (`HEALTH_LIVENESS_PATH`, `HEALTH_READINESS_PATH`)
- [ ] Any extra readiness check for a critical dependency is registered as a health check, not bolted onto liveness

## Distributed Tracing

- [ ] OpenTelemetry (or an equivalent) tracer provider configured at startup, before the application is built
- [ ] The ASGI application wrapped by the tracing middleware; outbound HTTP and PostgreSQL clients instrumented
- [ ] Tracing packages pinned in `pyproject.toml` and the pinned dependency set, recorded in `CHANGELOG.md`
- [ ] Trace context propagated on every outbound call (W3C `traceparent` / `tracestate`) and extracted from every inbound request
- [ ] Context survives async boundaries — queued job payloads carry trace metadata next to `request_id`
- [ ] The trace id is added to the log context, so a log line leads to its trace
- [ ] Manual spans only around meaningful internal units of work, with the attributes on-call will filter by
- [ ] No secrets or personal data as span attributes
- [ ] Head-based sampling at a low default rate; 100% of errors kept if tail sampling is available

## Alerting

- [ ] Every alert is symptom-based (5xx rate, p99 latency, oldest queued job, readiness failing everywhere) — causes (CPU, disk, restarts, pool usage) go to dashboards, not pagers
- [ ] Every alert is actionable; "ignore it, it self-heals" alerts are deleted
- [ ] Every alert links to a runbook in `docs/runbooks/`, in English — minimum three lines: what it means, first query to run, escalation path
- [ ] Runbooks contain no destructive commands (`migrate:fresh`, `migrate:reset`, `migrate:refresh`, `db:wipe`, `db:drop`); recovery is forward-only
- [ ] Thresholds and durations justified by an SLO or historical data, not guesses
- [ ] Two severities only: **page** (user-facing, act now) and **ticket** (degradation, act this week)
- [ ] Each new alert test-fired once: it reached the right channel and the runbook link works
- [ ] No alerts that fire daily and get acknowledged without action
- [ ] Security signals routed too: spikes in `security_events` (firewall threats, spam traps) and repeated authentication failures raise a ticket

## Dashboards

- [ ] Service health dashboard exists: 5xx rate, p99 latency, traffic, saturation (pool, queue)
- [ ] Dependency health panel shows per-provider error rates and latency
- [ ] Queue panel shows depth, oldest job age and failure rate per queue
- [ ] Dashboard answers the on-call questions from the top of this checklist — not "everything except the answer"
- [ ] Default time range is sensible (1h to 6h, not 30 days)

## Verify the Telemetry

Instrumentation is code; it can be wrong:

- [ ] Forced an error in staging → found it in the logs by the `request_id` from the `X-Request-ID` response header
- [ ] Sent test traffic → metric series appear on `/metrics` with expected labels and sane values
- [ ] Enqueued a job from a request → the worker's lines carry the same `request_id` and the right `entry_point`
- [ ] Followed one request end to end in the tracing UI → no broken spans
- [ ] An induced failure was diagnosed from telemetry alone, without reading the source
- [ ] `pytest` cases assert the critical event names and fields (`caplog`), the metric increments (`registry.get`, `registry.reset()` between tests), and the absence of secrets and personal data in records

## Pre-Launch Gate

Before a feature ships to production, all of the following are true:

- [ ] Structured JSON logs flowing to the log aggregator, with `request_id` on every line
- [ ] RED metrics visible in dashboards for every new endpoint and dependency
- [ ] At least one symptom-based alert configured, with runbook, test-fired
- [ ] A request can be traced across every hop it touches, including queued work
- [ ] `/metrics` protected; `/health` and `/ready` wired to the orchestrator and load balancer
- [ ] On-call knows where the runbooks are
- [ ] Gates pass: `python -m pytest tests`, `ruff check engine`, `python .claude/rules/lint_language.py`, `python .claude/rules/lint_structure.py`
- [ ] `CHANGELOG.md` records the instrumentation under `## [Unreleased]`

For the launch-day monitoring sequence and rollback triggers, see the `shipping-and-launch`
skill (`.claude/skills/shipping-and-launch/SKILL.md`).
