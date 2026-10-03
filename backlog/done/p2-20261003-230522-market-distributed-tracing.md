---
id: "20261003-230522"
title: Decide optional HTTP-to-job distributed tracing
type: decision
priority: 2
autonomous: false
blocked_by: owner-decision
max_attempts: 2
attempts: 0
created_at: 2026-10-03T23:05:22Z
updated_at: 2026-10-03T23:17:08Z
source: Owner-requested market research on 2026-10-04 (Europe/Lisbon), official framework documentation and source audit
touches:
  - data/engine/support/
  - data/engine/http/
  - data/engine/queue/
  - data/config/
  - data/documentation/observability.md
  - data/tests/
---

## Problem

Request correlation and local metrics do not alone show a request flowing into a background worker. Teams need optional interoperable traces with bounded overhead.

## Evidence

- `data/engine/support/metrics.py:66` already defines metrics primitives; this is an extension proposal, not a missing-metrics claim.
- `data/engine/cli/agent_catalog/skills/observability-and-instrumentation/SKILL.md:304` contains OpenTelemetry examples; reference code is not a framework runtime integration.
- [Spring Boot production features](https://docs.spring.io/spring-boot/reference/actuator/index.html) provides an operational reference.

## Done when

- [ ] Owner decides optional OpenTelemetry integration and dependency boundary.
- [ ] Design defines W3C trace propagation into JSON job metadata, sampling, sensitive-data redaction and export failure behavior.
- [ ] Plan verifies HTTP-to-worker parentage, request/tenant isolation, disabled behavior and no new default public endpoints.

## Verify

```bash
python3 .claude/rules/lint_backlog.py
rg -n 'owner decision|owner ruling' backlog/pending/p2-20261003-230522-market-distributed-tracing.md
git diff --check
```

For this decision task, verify a dated owner ruling in History and satisfaction of the criteria above. Implementation tests must be specified in separate approved tasks and run in the framework container; these commands do not verify any proposed runtime feature.

## Notes

Expected benefit: diagnose latency and failures. Effort: medium. Do not log credentials, job payloads or unbounded high-cardinality attributes; preserve existing tracing if found during implementation audit.

Suggestions are not approved implementation work: autonomous is false and blocked_by is owner-decision. Paths above bound a possible follow-up; no application files are modified by this research. Recheck source before implementation, including existing uncommitted changes. Comparative assessments remain internal to this backlog pending the existing publication decision.

## History

- 2026-10-03T23:05:22Z created by codex (source: owner-requested market research; suggestion awaiting owner decision)
- 2026-10-03T23:17:08Z owner ruling: owner rejected market-oriented study and requested comparison of GitHub source to improve Craft ergonomics for humans and coding agents
- 2026-10-03T23:17:08Z resolved as obsolete by codex; superseded by p2-20261003-231656-source-framework-ergonomics-review.md
