---
id: "20261003-230518"
title: Choose Craft Engine market positioning and first investment slice
type: decision
priority: 2
autonomous: false
blocked_by: owner-decision
max_attempts: 2
attempts: 0
created_at: 2026-10-03T23:05:18Z
updated_at: 2026-10-03T23:17:08Z
source: Owner-requested market research on 2026-10-04 (Europe/Lisbon), official framework documentation and source audit
touches: []
---

## Problem

Craft needs a defensible target audience and an investment order based on delivery, operating reliability and adoption barriers, rather than an unsupported universal framework ranking. This is an internal research record requested by the owner on 2026-10-04 (Europe/Lisbon). Recommendations are engineering judgments, not market-share or performance measurements.

## Evidence

- `data/README.md:3` identifies a Python framework on Starlette; a new project is intentionally bare.
- `data/documentation/market_evaluation.md:45` assigns feature scores without a reproducible scoring method.
- [Stack Overflow 2025 survey](https://survey.stackoverflow.co/2025/technology) reports a five percentage point increase for FastAPI; this is respondent usage, not revenue, hiring demand or market share. The survey mixes frameworks and other web technologies. No 2026 survey was verified in this review.

### Comparative assessment

There is no single best framework across languages and workloads. The following shortlist uses official documentation, inspected during this review; documentation establishes capabilities, not production performance or user adoption.

| Reference | Fit and lesson for Craft | Source |
|---|---|---|
| Laravel / PHP | Primary benchmark for integrated developer experience, queues and conventions | https://laravel.com/framework/docs/13.x/queues |
| Symfony / PHP | Modular architecture and message middleware/transports | https://symfony.com/doc/current/messenger.html |
| Ruby on Rails / Ruby | Convention-driven full-stack delivery and a common job abstraction | https://guides.rubyonrails.org/active_job_basics.html |
| Django / Python | Closest established full-stack Python reference; Tasks exists in 6.0 but production execution needs external infrastructure | https://docs.djangoproject.com/en/6.0/topics/tasks/ |
| AdonisJS / TypeScript | Integrated full-stack reference for developers seeking familiar MVC conventions | https://docs.adonisjs.com/ |
| Masonite / Python | Relevant integrated Python alternative; include in developer-experience trials without assuming equivalent adoption | https://docs.masoniteproject.com/ |
| FastAPI / Python | API contracts and generated documentation; API specialist rather than an equivalent full-stack scope | https://fastapi.tiangolo.com/features/ |
| NestJS / TypeScript | Structured service development and optional Swagger/OpenAPI integration | https://docs.nestjs.com/openapi/introduction |
| Phoenix / Elixir | Real-time and concurrent application architecture; evaluate only if a concrete product need emerges | https://phoenix.hexdocs.pm/overview.html |
| Spring Boot / Java | Operational readiness and production diagnostics | https://docs.spring.io/spring-boot/reference/actuator/index.html |
| ASP.NET Core / C# | First-party API contract generation reference for enterprise services | https://learn.microsoft.com/en-us/aspnet/core/fundamentals/openapi/overview?view=aspnetcore-10.0 |

### Recommended direction (inference)

Target Python teams building transactional web applications and APIs who value consistent conventions and generated project-owned code. Validate this with interviews and equivalent example applications before claiming demand. Craft already has queues, Redis integration, authorization, diagnostics and metrics; improve specific gaps rather than adding duplicate subsystems.

Recommended sequence: trustworthy claims and comparable measurements; opt-in API contracts; transaction-aware job dispatch; owned cache leases and idempotency; optional distributed tracing; scoped test doubles. Keep real-time UI systems and broader enterprise integrations behind demonstrated customer needs. Cross-language benchmarks require equivalent workloads and deployment resources; raw RPS from different setups cannot rank frameworks.

## Done when

- [ ] Owner records target audience, success metrics and the first approved slice with rationale.
- [ ] Owner reviews the six companion suggestions created by this research, and records accept/defer/reject for each.
- [ ] Any implementation is tracked separately with bounded paths and measurable acceptance criteria.

## Verify

```bash
python3 .claude/rules/lint_backlog.py
rg -n 'owner decision|owner ruling' backlog/pending/p2-20261003-230518-market-strategy-framework-benchmarks.md
git diff --check
```

For this decision task, verify a dated owner ruling in History and satisfaction of the criteria above. Implementation tests must be specified in separate approved tasks and run in the framework container; these commands do not verify any proposed runtime feature.

## Notes

Research only. No feature implementation authorized by this task. Existing comparison-document decision remains open.

Suggestions are not approved implementation work: autonomous is false and blocked_by is owner-decision. Paths above bound a possible follow-up; no application files are modified by this research. Recheck source before implementation, including existing uncommitted changes. Comparative assessments remain internal to this backlog pending the existing publication decision.

## History

- 2026-10-03T23:05:18Z created by codex (source: owner-requested market research; suggestion awaiting owner decision)
- 2026-10-03T23:17:08Z owner ruling: owner rejected market-oriented study and requested comparison of GitHub source to improve Craft ergonomics for humans and coding agents
- 2026-10-03T23:17:08Z resolved as obsolete by codex; superseded by p2-20261003-231656-source-framework-ergonomics-review.md
