---
id: "20261003-230519"
title: Decide an opt-in OpenAPI contract and documentation slice
type: decision
priority: 2
autonomous: false
blocked_by: owner-decision
max_attempts: 2
attempts: 0
created_at: 2026-10-03T23:05:19Z
updated_at: 2026-10-03T23:05:19Z
source: Owner-requested market research on 2026-10-04 (Europe/Lisbon), official framework documentation and source audit
touches:
  - data/engine/http/router.py
  - data/engine/validation/
  - data/engine/resources/
  - data/engine/cli/
  - data/documentation/
  - data/tests/
---

## Problem

Consumers need machine-readable request, response and authorization contracts without maintaining a second route registry.

## Evidence

- `data/engine/http/router.py:64` exposes route inventory metadata but not a request/response contract.
- Repository search found no runtime OpenAPI or Swagger generator; agent reference text does not establish runtime support.
- [FastAPI features](https://fastapi.tiangolo.com/features/) and [NestJS OpenAPI](https://docs.nestjs.com/openapi/introduction) demonstrate generated contracts and interactive documentation.

## Done when

- [ ] Owner decides explicit metadata versus typed schemas and dependency budget.
- [ ] Approved design covers parameters, validation, resources, security requirements, stable operation IDs and unsupported-schema diagnostics.
- [ ] Implementation plan requires schema validation and contract tests, documentation routes off by default and all enabled routes visible in route:list.

## Verify

```bash
python3 .claude/rules/lint_backlog.py
rg -n 'owner decision|owner ruling' backlog/pending/p2-20261003-230519-market-api-contracts.md
git diff --check
```

For this decision task, verify a dated owner ruling in History and satisfaction of the criteria above. Implementation tests must be specified in separate approved tasks and run in the framework container; these commands do not verify any proposed runtime feature.

## Notes

Expected benefit: integration and client generation. Effort: medium/high; risk: schema fidelity. Avoid inventing types from dynamic controller behavior.

Suggestions are not approved implementation work: autonomous is false and blocked_by is owner-decision. Paths above bound a possible follow-up; no application files are modified by this research. Recheck source before implementation, including existing uncommitted changes. Comparative assessments remain internal to this backlog pending the existing publication decision.

## History

- 2026-10-03T23:05:19Z created by codex (source: owner-requested market research; suggestion awaiting owner decision)
