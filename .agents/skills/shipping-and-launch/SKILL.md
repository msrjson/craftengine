---
name: shipping-and-launch
description: Prepares Craft applications for safe production launches with a pre-launch checklist, staged rollout, monitoring and a forward-only rollback plan. Use when preparing to deploy to production, asking what must be in place before shipping, planning a staged rollout or feature flag release, setting up launch monitoring, or writing a rollback strategy.
---

# Shipping and Launch

## Overview

Ship with confidence. The goal is not merely to deploy; it is to deploy safely, with
monitoring in place, a rollback plan written before it is needed, and a clear definition of
success. Every launch should be **reversible, observable and incremental**.

Craft adds two constraints that shape every launch plan. First, the database is
**forward-only**: a rollback redeploys the previous application against the current schema, it
never rewinds migrations. Second, a release is only a release when the non-regression laws
hold: version synced, counter incremented, changelog folded, gates green, tag cut.

## When to Use

- Deploying a feature to production for the first time
- Releasing a significant change to users or tenants
- Migrating data or infrastructure
- Opening a beta or early-access program
- Cutting a tagged release
- Any deployment that carries risk (all of them)

## The Pre-Launch Checklist

Every change must already clear the project Definition of Done
(`.claude/references/definition-of-done.md`). This checklist is what production adds on top.

### Code Quality

- [ ] `python -m pytest tests` passes on SQLite **and** against PostgreSQL
- [ ] `tests/test_release_non_regression.py` passes
- [ ] `ruff check` is clean and type checking passes where the project enforces it
- [ ] `python .claude/rules/lint_language.py` and `python .claude/rules/lint_structure.py` exit 0
- [ ] The production image builds (`Dockerfile.prod` or the project's equivalent)
- [ ] Code reviewed and approved
- [ ] No `TODO`/`FIXME` that must be resolved before launch, no commented-out code
- [ ] No `print()` debugging or ad-hoc logging of request payloads left in the code
- [ ] No bare `except:` or `except Exception:`; failures raise typed errors with `code` and `message_key`
- [ ] Error handling covers the expected failure modes (database unavailable, queue down, third-party timeout)

### Security

- [ ] No secrets in code, configuration files or git history
- [ ] `pip-audit` (or the project's dependency audit) reports no critical or high vulnerabilities
- [ ] Every input validated through a `FormRequest` or an equivalent explicit validator
- [ ] Authentication on protected routes and authorization through Gate/Policy checks
- [ ] Every state-changing Forge form carries `@csrf`; public forms carry `@honeypot` or `@antispam`
- [ ] Tokens, signatures and secrets compared with `hmac.compare_digest`
- [ ] Security headers enabled (the `SecurityHeaders` middleware or equivalent: CSP, HSTS, frame and content-type options)
- [ ] Rate limiting on authentication and other abuse-prone endpoints (`ThrottleRequests` or equivalent)
- [ ] CORS restricted to specific origins, never a wildcard with credentials
- [ ] Debug mode off in production; error pages expose no stack traces
- [ ] Personal data handling reviewed for LGPD/GDPR: purpose, minimization, retention, access logging

Full detail: `.claude/references/security-checklist.md` and the `security-and-hardening`
skill (`.claude/skills/security-and-hardening/SKILL.md`).

### Performance

- [ ] Core Web Vitals within "Good" thresholds on the key pages
- [ ] No N+1 queries on critical paths (eager loading where relationships are iterated)
- [ ] Indexes exist for the columns filtered, joined and ordered on in hot queries
- [ ] Images compressed, sized responsively and lazy-loaded below the fold
- [ ] Static `.js`/`.css` payload within budget, served with long-lived cache headers
- [ ] Caching configured for repeated reads (the `Cache` facade) with explicit invalidation
- [ ] Slow work moved to queued jobs rather than the request path

Full detail: `.claude/references/performance-checklist.md` and the `performance-optimization`
skill (`.claude/skills/performance-optimization/SKILL.md`).

### Accessibility

- [ ] Keyboard navigation works for every interactive element
- [ ] Screen readers convey page structure (landmarks, headings, labels)
- [ ] Color contrast meets WCAG 2.2 AA (4.5:1 for body text)
- [ ] Focus is managed correctly for dialogs and dynamically inserted content
- [ ] Validation errors rendered with `@error('field')` are associated with their fields
- [ ] No accessibility violations reported by Lighthouse or an axe audit

Full detail: `.claude/references/accessibility-checklist.md`.

### Internationalization

- [ ] No hardcoded user-facing text in Python, Forge templates, e-mails or JavaScript
- [ ] Every new translation key has rows for `en` (source), `pt-BR` (default) and `es`
- [ ] Translation seeders or migrations for the new keys run in the target environment
- [ ] Money rendered from integer minor units; dates stored in UTC and localized at render time

### Infrastructure

- [ ] Environment variables and secrets set in the production secret store
- [ ] Forward migrations reviewed and ready: `python dev.py migrate --pretend` shows exactly what will run
- [ ] Every migration in this release is additive or part of an expand/contract sequence — no drop or rename of anything the previous version still reads
- [ ] A verified, restorable backup taken before migrations run
- [ ] No banned command (`migrate:fresh`, `migrate:reset`, `migrate:refresh`, `db:wipe`, `db:drop`) in any deploy script or runbook
- [ ] DNS and TLS configured; HTTPS enforced
- [ ] Static assets served with caching (CDN or reverse proxy)
- [ ] Structured logging and error reporting configured and reaching their destination
- [ ] Liveness (`/health`) and readiness (`/ready`) endpoints respond, or their configured paths do
- [ ] Queue workers (`python dev.py queue:work`) and the scheduler (`python dev.py schedule:work`) deployed alongside the web process when the release uses them

### Documentation and Release Invariants

- [ ] README updated with any new setup requirement
- [ ] API documentation current for changed endpoints
- [ ] ADRs written for architectural decisions (the `documentation-and-adrs` skill, `.claude/skills/documentation-and-adrs/SKILL.md`)
- [ ] `CHANGELOG.md`: `## [Unreleased]` folded into `## [X.Y.Z] rNNNNN — YYYY-MM-DD`, with a fresh empty `## [Unreleased]` above it
- [ ] `pyproject.toml` version equals `engine/__init__.py` `__version__`; `__release__` is the previous counter plus one
- [ ] Tag `vX.Y.Z-rNNNNN` created from one source of truth (the release job or a single manual step, never both)
- [ ] User-facing documentation updated where behavior changed

## Feature Flag Strategy

Ship behind a flag to separate deploying code from releasing behavior. Resolve the flag
service from the container and decide in the controller or service layer — the template
receives a boolean, it never evaluates the flag itself:

```python
"""Task detail controller action that gates task sharing behind a flag."""

from typing import Any

from craft.http.controller import Controller


class TaskController(Controller):
    """Thin HTTP layer for task pages."""

    def __init__(self, tasks: "TaskService", flags: "FeatureFlags") -> None:
        """Receive collaborators from the container.

        Args:
            tasks: Domain service for tasks.
            flags: Feature flag lookup.
        """
        self._tasks = tasks
        self._flags = flags

    def show(self, request: Any, task_id: int) -> Any:
        """Render one task, including the sharing panel only when enabled."""
        task = self._tasks.find_for_user(task_id, request.user)
        sharing_enabled = self._flags.is_enabled(
            "tasks.sharing", tenant_id=request.user.tenant_id
        )
        return self.view("tasks.show", {"task": task, "sharing_enabled": sharing_enabled})
```

```html
@if(sharing_enabled)
  <section aria-labelledby="task-sharing-title">
    <h2 id="task-sharing-title">{{ __('task.sharing.title') }}</h2>
    @include('tasks.partials.sharing_panel')
  </section>
@endif
```

How the controller receives its collaborators depends on how the project's routes resolve
controllers from the container; the shape — flag decided in Python, a boolean passed to the
view, copy through translation keys — is what matters.

**Feature flag lifecycle:**

```
1. DEPLOY with flag OFF     -> code in production, inactive
2. ENABLE for team/beta     -> internal users or a pilot tenant exercise it in production
3. GRADUAL ROLLOUT          -> 5% -> 25% -> 50% -> 100% of users or tenants
4. MONITOR at each stage    -> error rate, latency, queue depth, user feedback
5. CLEAN UP                 -> remove the flag and the dead path after full rollout
```

**Rules:**

- Every flag has an owner and a removal date
- Remove flags within two weeks of full rollout, with a `Removed` or `Changed` changelog entry
- Do not nest flags; combinations grow exponentially
- Test both flag states in CI
- A flag never gates a schema change: migrations must be safe whether the flag is on or off

## Staged Rollout

### The Rollout Sequence

```
1. DEPLOY to staging
   └── Forward migrations applied; `migrate:status` shows nothing pending
   └── Full suite green against a PostgreSQL copy of the production schema
   └── Manual smoke test of the critical flows

2. DEPLOY to production (flag OFF)
   └── Backup verified, forward migrations applied
   └── /ready returns 200 on every instance
   └── Error monitoring shows no new error types

3. ENABLE for the team (flag ON for internal users or a pilot tenant)
   └── Team uses the feature in production
   └── 24-hour monitoring window

4. CANARY (flag ON for 5% of users or tenants)
   └── Monitor error rate, latency, queue depth, user behavior
   └── Compare canary against baseline
   └── 24-48 hour monitoring window
   └── Advance only if every threshold below is green

5. GRADUAL increase (25% -> 50% -> 100%)
   └── Same monitoring at every step
   └── Able to return to the previous percentage at any point

6. FULL rollout (flag ON for everyone)
   └── Monitor for one week
   └── Remove the flag
```

### Rollout Decision Thresholds

| Metric | Advance (green) | Hold and investigate (yellow) | Roll back (red) |
|---|---|---|---|
| Error rate (5xx) | Within 10% of baseline | 10-100% above baseline | More than 2x baseline |
| P95 latency | Within 20% of baseline | 20-50% above baseline | More than 50% above baseline |
| Browser JS errors | No new error types | New errors in under 0.1% of sessions | New errors in over 0.1% of sessions |
| Queue depth / failed jobs | Stable | Growing but draining | Growing without draining, or failed jobs spiking |
| Missing translation keys | None reported | Isolated fallbacks | Raw keys or fallback copy visible on critical flows |
| Business metrics | Neutral or positive | Decline under 5% (may be noise) | Decline over 5% |

### When to Roll Back

Roll back immediately if:

- Error rate exceeds 2x baseline
- P95 latency rises more than 50%
- User-reported issues spike
- Data integrity problems are detected (wrong tenant data, lost writes, corrupted records)
- A security vulnerability is discovered in the release
- Security events (firewall blocks, honeypot or antispam triggers) spike in a way that points at the new code

## Monitoring and Observability

### What to Monitor

```
Application metrics:
├── Error rate (total and per route)
├── Response time (p50, p95, p99)
├── Request volume
├── Active users and tenants
├── Queue depth, job runtime, failed jobs
├── Missing translation key fallbacks
└── Key business metrics (conversion, completed flows)

Infrastructure metrics:
├── CPU and memory
├── PostgreSQL connection pool usage and lock waits
├── Disk space (database and uploads)
├── Network latency
└── Readiness probe failures per instance

Client metrics:
├── Core Web Vitals (LCP, INP, CLS)
├── JavaScript errors
├── Failed requests seen by the browser
└── Page load time
```

Craft registers liveness (`/health`), readiness (`/ready`) and metrics (`/metrics`) routes by
default, with paths configurable in the framework configuration; confirm they are enabled and
reachable only where they should be. Instrumentation detail lives in the
`observability-and-instrumentation` skill
(`.claude/skills/observability-and-instrumentation/SKILL.md`) and
`.claude/references/observability-checklist.md`.

### Error Reporting

Errors are reported with enough context to locate the failure, and users receive a stable
code and a translation key — never internals, never a hardcoded sentence:

```python
"""Reporting helper for unhandled failures at the HTTP boundary."""

import logging
from dataclasses import dataclass

logger = logging.getLogger("app.errors")


@dataclass(frozen=True)
class ErrorPayload:
    """Transport-safe error body.

    Attributes:
        code: Stable machine code, UPPER_SNAKE.
        message_key: Translation key the client renders.
    """

    code: str
    message_key: str


def report_unhandled(
    error: Exception, *, method: str, path: str, user_id: int | None, tenant_id: int | None
) -> ErrorPayload:
    """Log an unhandled failure with context and return the public payload.

    Args:
        error: The exception that escaped the handler.
        method: HTTP method of the request.
        path: Request path, without the query string.
        user_id: Authenticated user id, when there is one.
        tenant_id: Tenant being served, when there is one.

    Returns:
        The payload to send to the client with status 500.
    """
    logger.error(
        "http_unhandled_exception",
        exc_info=error,
        extra={"method": method, "path": path, "user_id": user_id, "tenant_id": tenant_id},
    )
    return ErrorPayload(code="INTERNAL_ERROR", message_key="error.internal")
```

Do not log request bodies, passwords, tokens or personal data in the `extra` context. On the
browser side, a small vanilla `window.addEventListener("error", ...)` handler that posts the
error type, page and release tag to a reporting endpoint is enough; never send form contents.

### Post-Launch Verification

In the first hour after launch:

```
1. /ready returns 200 on every instance
2. Error monitoring shows no new error types
3. Latency shows no regression against baseline
4. The critical user flow works end to end, in each locale that matters
5. Logs are flowing, structured and readable
6. Queue workers are consuming and failed jobs are not climbing
7. `python dev.py migrate:status` shows every migration ran, none pending
8. The rollback path is confirmed ready (previous image tag available, flag toggle works)
```

## Error Budget Release Gate

The service's error budget — the share of requests or time the SLO allows to fail — decides
whether it is safe to ship. Treat it as an objective gate, not a negotiation:

```
Budget remaining > 20%  ->  ship normally; monitor closely
Budget remaining 0-20%  ->  slow rollouts only; no high-risk changes
Budget exhausted        ->  freeze feature work; reliability work only
Budget resets           ->  resume the normal pace; keep the fix that recovered it
```

A high burn rate during a canary (spending budget faster than the baseline pace) is a **hold**
signal in the thresholds table, the same as an elevated error rate.

## Rollback Strategy

Every deployment has a rollback plan **before** it happens. Because Craft migrations are
forward-only, the plan never includes rewinding the schema in production:

```markdown
## Rollback Plan for [feature / vX.Y.Z-rNNNNN]

### Trigger Conditions
- Error rate > 2x baseline
- P95 latency > [X] ms
- User reports of [specific issue]
- Any data integrity or cross-tenant exposure signal

### Rollback Steps
1. Turn the feature flag off (if the change is flagged)
   OR
1. Redeploy the previous image tag (vX.Y.Z-rNNNNN of the last good release) without running migrations
2. Verify: /ready on every instance, error rate back to baseline, critical flow works
3. Communicate: notify the team and record the incident

### Database Considerations
- Migrations in this release: [list]. All additive, so the previous version runs against the new schema.
- Destructive steps: none in this release (contract steps ship in a later, separate release).
- Data written by the new feature: preserved; if it must be corrected, ship a forward migration or a
  data-fix job — never `migrate:reset`, `migrate:fresh` or manual deletes; business records are soft-deleted.
- Backup taken at: [timestamp], restore tested on: [date]. Restore is the last resort for corruption, not a rollback tool.

### Time to Roll Back
- Feature flag: < 1 minute
- Redeploy previous image: < 5 minutes
- Forward fix migration: planned and reviewed like any other change
```

After a rollback, the fix goes out as a new release with the next counter; the bad release's
tag and changelog entry stay in history, with a `Fixed` entry in the next release explaining
what went wrong.

## See Also

- Project Definition of Done every change clears first: `.claude/references/definition-of-done.md`
- Security pre-launch checks: `.claude/references/security-checklist.md`
- Performance pre-launch checks: `.claude/references/performance-checklist.md`
- Accessibility verification: `.claude/references/accessibility-checklist.md`
- Alerting rules and SLO thresholds: the `observability-and-instrumentation` skill (`.claude/skills/observability-and-instrumentation/SKILL.md`)
- Versioning, changelog and tags: the `git-workflow-and-versioning` skill (`.claude/skills/git-workflow-and-versioning/SKILL.md`)
- Pipelines and rollback workflow: the `ci-cd-and-automation` skill (`.claude/skills/ci-cd-and-automation/SKILL.md`)
- Schema changes across releases: the `deprecation-and-migration` skill (`.claude/skills/deprecation-and-migration/SKILL.md`)
- Parallel go/no-go review: the `/ship` command (`.claude/commands/ship.md`)

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "It works in staging, it'll work in production" | Production has different data, traffic and tenants. Monitor after deploy. |
| "We don't need a feature flag for this" | Every feature benefits from a kill switch. "Simple" changes break things too. |
| "Monitoring is overhead" | Without it, users report the outage before you see it. |
| "We'll add monitoring later" | Add it before launch. You cannot debug what you cannot see. |
| "Rolling back is admitting failure" | Rolling back is responsible engineering. Leaving a broken release live is the failure. |
| "The error rate looks fine, keep going" | Check the burn rate, not just the current rate. Fast budget burn is a hold signal. |
| "If it breaks we'll just roll back the migration" | The schema is forward-only. Make the migration additive so the previous release still runs. |
| "We'll drop the old column in this release, nothing uses it" | The previous release uses it — and that is what you redeploy on rollback. Drop it in a later release. |
| "The changelog can be fixed after the tag" | The tag, the version files and the changelog heading must agree at the moment of release. |

## Red Flags

- Deploying without a written rollback plan
- A rollback plan that depends on `migrate:rollback`, `migrate:reset` or restoring a backup
- A release that drops or renames a column the previous version still reads
- No monitoring or error reporting in production
- Big-bang releases: everything at once, no staging, no flag
- Feature flags with no owner or expiry
- Nobody watching the deploy during the first hour
- Production configuration applied by hand from memory rather than from code
- Version files out of sync, counter not incremented, or no `vX.Y.Z-rNNNNN` tag
- Error pages or API responses exposing stack traces or hardcoded copy
- "It's Friday afternoon, let's ship it"
- Error budget exhausted while feature work continues unchanged

## Verification

Before deploying:

- [ ] Pre-launch checklist complete, every section green
- [ ] Release invariants hold: version synced, `__release__` +1, changelog folded, tag ready
- [ ] Every migration is additive or an expand/migrate step; no contract step ships with the code that stops using the old shape
- [ ] Backup verified; no banned destructive command anywhere in the deploy path
- [ ] Feature flag configured (if applicable) and both states tested
- [ ] Rollback plan written, naming the previous image tag
- [ ] Monitoring dashboards and alerts in place
- [ ] Team notified of the deployment window

After deploying:

- [ ] `/ready` returns 200 on every instance
- [ ] Error rate and latency at baseline
- [ ] Critical user flows work in the default locale (`pt-BR`) and the others that matter
- [ ] Logs flowing; queue workers consuming; no pending migrations
- [ ] Rollback path verified ready

For every shipped service:

- [ ] Error budget policy in place: the action when budget drops below 20% and when it is exhausted is agreed in advance
