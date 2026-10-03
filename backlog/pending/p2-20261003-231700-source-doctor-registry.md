---
id: "20261003-231700"
title: Decide extensible doctor checks with categories and offline preflight
type: decision
priority: 2
autonomous: false
blocked_by: owner-decision
max_attempts: 2
attempts: 0
created_at: 2026-10-03T23:17:00Z
updated_at: 2026-10-03T23:17:00Z
source: Owner-corrected GitHub source comparison for human and coding-agent ergonomics
touches:
  - data/engine/support/doctor.py
  - data/engine/cli/app.py
  - data/documentation/cli.md
  - data/tests/
---

## Problem

Applications cannot add first-class project checks to the current fixed doctor list. Syntax/routes/templates and database checks are bundled, increasing prerequisites for simple preflight feedback.

## Evidence

- `data/engine/support/doctor.py:124` hardcodes seven check callables, including table and translation checks.
- `data/engine/support/doctor.py:88` already provides code/location/params/message/fix and JSON; preserve this useful foundation.
- [django/django: def run_checks(](https://github.com/django/django/blob/a461af8ce48762d7ec602260aaff81014ddccbcb/django/core/checks/registry.py#L74) supports check registration, tags and separate deployment checks. [django/django: def execute(](https://github.com/django/django/blob/a461af8ce48762d7ec602260aaff81014ddccbcb/django/core/management/base.py#L446) runs selected system checks before commands. [spring-projects/spring-boot: public class FailureAnalysis](https://github.com/spring-projects/spring-boot/blob/f6142c9f47591b70949391d1848c1f81503006db/core/spring-boot/src/main/java/org/springframework/boot/diagnostics/FailureAnalysis.java#L27) and [spring-projects/spring-boot: interface FailureAnalyzer](https://github.com/spring-projects/spring-boot/blob/f6142c9f47591b70949391d1848c1f81503006db/core/spring-boot/src/main/java/org/springframework/boot/diagnostics/FailureAnalyzer.java#L29) distinguish diagnosis, action and cause rather than merely dumping exceptions.

## Done when

- [ ] Owner chooses a small check-registration API available to providers, with namespaced identifiers and declared requirements.
- [ ] Add category selection and an offline mode that reports skipped database-dependent checks explicitly instead of declaring them successful.
- [ ] Preserve full doctor as the default and existing JSON findings; order results deterministically and reject duplicate registrations.
- [ ] Verification plan adds an application-provided check, selects only route/view checks without a live database, and preserves full-check nonzero exits.

## Verify

```bash
python3 .claude/rules/lint_backlog.py
rg -n 'owner ruling:' backlog/pending/p2-20261003-231700-source-doctor-registry.md
git diff --check
```

These verify queue structure and a future owner ruling, not an implemented feature. Verify the Done when decisions against that ruling. Before approved implementation, create a separately scoped task with exact container test commands for the scenarios listed above. No foreign framework or Craft application behavior tests were run during this source review.

## Notes

For humans: diagnostics at the right stage. For agents: early deterministic feedback without bringing up every service. Effort: medium. Do not turn offline mode into a gate bypass or hide skipped security checks.

Review: `backlog/pending/p2-20261003-231656-source-framework-ergonomics-review.md`.

Craft source baseline: `58f510c344f5362de1a4b35f98190ef2147228c7`. Local references were read from the working tree; unrelated existing worktree changes were preserved. Foreign source links use immutable commit SHAs, not moving branches. Findings are static source analysis unless explicitly stated otherwise.

Research does not authorize implementation. Keep autonomous false until the owner decides. No application code was changed. Source-level lessons require adaptation to Python, Craft's runtime and existing safety contracts; no performance or usability multiplier has been measured.

## History

- 2026-10-03T23:17:00Z created by codex (source: owner-corrected GitHub code comparison; suggestion awaiting owner decision)
