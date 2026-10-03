---
id: "20261003-230521"
title: Decide owned cache leases and job idempotency contracts
type: decision
priority: 2
autonomous: false
blocked_by: owner-decision
max_attempts: 2
attempts: 0
created_at: 2026-10-03T23:05:21Z
updated_at: 2026-10-03T23:05:21Z
source: Owner-requested market research on 2026-10-04 (Europe/Lisbon), official framework documentation and source audit
touches:
  - data/engine/cache/
  - data/engine/queue/
  - data/documentation/cache.md
  - data/documentation/queues_events.md
  - data/tests/
---

## Problem

Atomic add is useful but does not itself provide a reusable lease with owner-checked release or a documented job uniqueness window.

## Evidence

- `data/engine/cache/manager.py:320` exposes atomic add; `remember` at line 341 is a separate convenience operation.
- `data/engine/queue/job.py:22` exposes a minimal job base class without uniqueness metadata.
- [Laravel queues](https://laravel.com/framework/docs/13.x/queues) documents unique jobs and overlap prevention.

## Done when

- [ ] Owner selects a bounded cache-lease slice before deciding on unique-job integration.
- [ ] Design specifies owner token, TTL, acquisition timeout, release by the same owner, backend capabilities and tenant-scoped keys.
- [ ] Plan includes multi-process contention and expired-lease tests, and states that execution locks do not guarantee exactly-once business effects.

## Verify

```bash
python3 .claude/rules/lint_backlog.py
rg -n 'owner decision|owner ruling' backlog/pending/p2-20261003-230521-market-cache-leases-job-idempotency.md
git diff --check
```

For this decision task, verify a dated owner ruling in History and satisfaction of the criteria above. Implementation tests must be specified in separate approved tasks and run in the framework container; these commands do not verify any proposed runtime feature.

## Notes

Expected benefit: control duplicate work. Effort: medium. File/array/Redis stores have different process boundaries. Never substitute an unsafe get-then-set for atomic acquisition.

Suggestions are not approved implementation work: autonomous is false and blocked_by is owner-decision. Paths above bound a possible follow-up; no application files are modified by this research. Recheck source before implementation, including existing uncommitted changes. Comparative assessments remain internal to this backlog pending the existing publication decision.

## History

- 2026-10-03T23:05:21Z created by codex (source: owner-requested market research; suggestion awaiting owner decision)
