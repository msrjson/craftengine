---
id: "20261003-230525"
title: Decide reproducible framework and productivity benchmark evidence
type: decision
priority: 2
autonomous: false
blocked_by: owner-decision
max_attempts: 2
attempts: 0
created_at: 2026-10-03T23:05:25Z
updated_at: 2026-10-03T23:17:08Z
source: Owner-requested market research on 2026-10-04 (Europe/Lisbon), official framework documentation and source audit
touches:
  - data/tools/
  - data/documentation/market_evaluation.md
  - data/documentation/testing.md
  - data/tests/
---

## Problem

Existing numerical comparisons lack enough provenance to support competitive claims. Build repeatable evidence before presenting Craft as faster or more productive.

## Evidence

- `data/documentation/market_evaluation.md:45` gives feature scores without a rubric; line 77 claims 5x productivity; line 130 gives cross-framework RPS; line 145 claims 90% business effort.
- `data/tools/loadtest.py:1` describes a minimal concurrency probe rather than a controlled comparative benchmark.
- `backlog/pending/p3-20261003-223126-third-party-comparison-document.md:19` already tracks whether the public comparison may remain; this proposal does not supersede that decision.
- [Stack Overflow survey](https://survey.stackoverflow.co/2025/technology) is an adoption signal, not a source for framework throughput or productivity.

## Done when

- [ ] Owner approves an internal-only protocol, or records the publication exception in the existing comparison-document decision.
- [ ] Protocol fixes framework versions, hardware, resource budgets, workers, database, payloads, authentication, warm-up, duration and repetitions.
- [ ] Report contains raw artifacts, p50/p95/p99, error rate, CPU/memory and uncertainty; unmeasured competitors remain explicitly unmeasured.
- [ ] Productivity trial uses the same feature specification, acceptance tests and participants, reporting completion time and defects instead of invented multipliers.

## Verify

```bash
python3 .claude/rules/lint_backlog.py
rg -n 'owner decision|owner ruling' backlog/pending/p2-20261003-230525-market-reproducible-claims.md
git diff --check
```

For this decision task, verify a dated owner ruling in History and satisfaction of the criteria above. Implementation tests must be specified in separate approved tasks and run in the framework container; these commands do not verify any proposed runtime feature.

## Notes

Expected benefit: credible positioning and performance decisions. Effort: medium/high. Do not edit the existing public comparison before its owner decision; no benchmarks were run in this research. Use isolated environments and preserve all data.

Suggestions are not approved implementation work: autonomous is false and blocked_by is owner-decision. Paths above bound a possible follow-up; no application files are modified by this research. Recheck source before implementation, including existing uncommitted changes. Comparative assessments remain internal to this backlog pending the existing publication decision.

## History

- 2026-10-03T23:05:25Z created by codex (source: owner-requested market research; suggestion awaiting owner decision)
- 2026-10-03T23:17:08Z owner ruling: owner rejected market-oriented study and requested comparison of GitHub source to improve Craft ergonomics for humans and coding agents
- 2026-10-03T23:17:08Z resolved as obsolete by codex; superseded by p2-20261003-231656-source-framework-ergonomics-review.md
