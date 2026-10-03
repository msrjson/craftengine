---
id: "20261003-230520"
title: Decide transaction-aware job dispatch semantics
type: decision
priority: 2
autonomous: false
blocked_by: owner-decision
max_attempts: 2
attempts: 0
created_at: 2026-10-03T23:05:20Z
updated_at: 2026-10-03T23:05:20Z
source: Owner-requested market research on 2026-10-04 (Europe/Lisbon), official framework documentation and source audit
touches:
  - data/engine/queue/
  - data/engine/orm/connection.py
  - data/engine/orm/db.py
  - data/documentation/queues_events.md
  - data/tests/
---

## Problem

Jobs sent to another backend can observe data before its transaction commits. Establish explicit commit-aware behavior rather than assuming every queue driver has the same visibility.

## Evidence

- `data/engine/queue/manager.py:210` provides push/later dispatch and multiple drivers.
- `data/engine/orm/connection.py:900` provides transaction begin/commit/rollback; repository search did not find a public after_commit API.
- `data/tests/test_postgres_integration.py:531` already tests commit-aware PostgreSQL notification behavior; this is not a cross-driver job dispatch guarantee.
- [Laravel queues](https://laravel.com/framework/docs/13.x/queues) covers transaction-aware dispatch; [Rails Active Job](https://guides.rubyonrails.org/active_job_basics.html) discusses transactional integrity.

## Done when

- [ ] Owner chooses opt-in after_commit behavior and whether durable delivery requires a separate outbox slice.
- [ ] Design defines outermost commit, nested savepoints, rollback, callback failure and tenant/request isolation.
- [ ] Plan tests sync/database/Redis dispatch boundaries and explicitly documents the crash window; it never claims exactly-once delivery.

## Verify

```bash
python3 .claude/rules/lint_backlog.py
rg -n 'owner decision|owner ruling' backlog/pending/p2-20261003-230520-market-transaction-aware-jobs.md
git diff --check
```

For this decision task, verify a dated owner ruling in History and satisfaction of the criteria above. Implementation tests must be specified in separate approved tasks and run in the framework container; these commands do not verify any proposed runtime feature.

## Notes

Expected benefit: transactional correctness. Effort: medium/high. Current worktree changes include ORM code; implementation must preserve and rebase around that work. Any future database work must follow database safety rules.

Suggestions are not approved implementation work: autonomous is false and blocked_by is owner-decision. Paths above bound a possible follow-up; no application files are modified by this research. Recheck source before implementation, including existing uncommitted changes. Comparative assessments remain internal to this backlog pending the existing publication decision.

## History

- 2026-10-03T23:05:20Z created by codex (source: owner-requested market research; suggestion awaiting owner decision)
