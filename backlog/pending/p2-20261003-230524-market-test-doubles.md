---
id: "20261003-230524"
title: Decide scoped queue and event test doubles
type: decision
priority: 2
autonomous: false
blocked_by: owner-decision
max_attempts: 2
attempts: 0
created_at: 2026-10-03T23:05:24Z
updated_at: 2026-10-03T23:05:24Z
source: Owner-requested market research on 2026-10-04 (Europe/Lisbon), official framework documentation and source audit
touches:
  - data/engine/queue/
  - data/engine/events/
  - data/engine/container/
  - data/documentation/testing.md
  - data/tests/
---

## Problem

Application authors need to assert dispatched jobs and events without running real external side effects. A documented scoped API may reduce test setup and integration effort.

## Evidence

- `data/engine/queue/manager.py:210` dispatches real jobs; `data/engine/queue/job.py:26` defines the handler boundary.
- `data/documentation/README.md:58` points application authors to testing documentation.
- [Laravel queues](https://laravel.com/framework/docs/13.x/queues) documents dispatch fakes; [Django Tasks](https://docs.djangoproject.com/en/6.0/topics/tasks/) provides development/testing backends.

## Done when

- [ ] Owner approves a scoped testing-helper design after auditing existing fixture capabilities.
- [ ] Plan covers queue assertions, selected-job passthrough, event assertions and cleanup on exceptions.
- [ ] Verification must prove isolation between concurrent requests/tests and that real production drivers are unaffected outside the test scope.

## Verify

```bash
python3 .claude/rules/lint_backlog.py
rg -n 'owner decision|owner ruling' backlog/pending/p2-20261003-230524-market-test-doubles.md
git diff --check
```

For this decision task, verify a dated owner ruling in History and satisfaction of the criteria above. Implementation tests must be specified in separate approved tasks and run in the framework container; these commands do not verify any proposed runtime feature.

## Notes

Expected benefit: developer experience. Effort: medium. Keep this separate from transaction dispatch; container work currently has uncommitted changes.

Suggestions are not approved implementation work: autonomous is false and blocked_by is owner-decision. Paths above bound a possible follow-up; no application files are modified by this research. Recheck source before implementation, including existing uncommitted changes. Comparative assessments remain internal to this backlog pending the existing publication decision.

## History

- 2026-10-03T23:05:24Z created by codex (source: owner-requested market research; suggestion awaiting owner decision)
