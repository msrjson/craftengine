---
id: "20261003-231702"
title: Decide bounded live project inspection for humans and coding agents
type: decision
priority: 2
autonomous: false
blocked_by: owner-decision
max_attempts: 2
attempts: 0
created_at: 2026-10-03T23:17:02Z
updated_at: 2026-10-03T23:17:02Z
source: Owner-corrected GitHub source comparison for human and coding-agent ergonomics
touches:
  - data/engine/cli/app.py
  - data/engine/cli/agent_scaffolder.py
  - data/engine/support/
  - data/documentation/ai_agents.md
  - data/tests/
---

## Problem

Static generated agent instructions repeat generic examples and cannot reliably describe the actual installed project/version, registered methods or chosen optional features. Humans also need an easy way to discover these facts.

## Evidence

- `data/engine/cli/agent_scaffolder.py:131` returns hardcoded framework guidance rather than a live project inventory.
- `data/engine/cli/app.py:816` and doctor already have JSON output; reuse their facts rather than inventing a parallel runtime model.
- `data/engine/facades/base.py:40` already discovers signatures when a facade method is wrong; expose the same useful facts before an error.
- [laravel/boost: class ApplicationInfo](https://github.com/laravel/boost/blob/97b8da0cb8c2c1da75531a36e34adaa313a64afc/src/Mcp/Tools/ApplicationInfo.php#L17) returns runtime/package versions and database engine through a read-only tool. [symfony/symfony: public function complete(](https://github.com/symfony/symfony/blob/9493f3e814d1cf270f8dcb95c58e44c56de14a89/src/Symfony/Component/Console/Application.php#L404) derives completion suggestions from command definitions.

## Done when

- [ ] Owner approves an inspect CLI with scoped selectors, such as project/commands/service, and stable versioned --json output.
- [ ] Project inspection returns framework/Python versions, enabled capabilities and location references; service inspection returns public signatures without dumping instances or executing service methods.
- [ ] Command inspection derives argument/flag/default information from registered CLI definitions; no hand-maintained method list.
- [ ] Bound output by selector/limit; redact secrets, avoid external network and database records, expose unknown/unsupported introspection clearly.
- [ ] Verification plan compares CLI metadata to registrations, checks no side-effectful method execution, and ensures reduced agent context is factual for the installed version.

## Verify

```bash
python3 .claude/rules/lint_backlog.py
rg -n 'owner ruling:' backlog/pending/p2-20261003-231702-source-agent-inspection.md
git diff --check
```

These verify queue structure and a future owner ruling, not an implemented feature. Verify the Done when decisions against that ruling. Before approved implementation, create a separately scoped task with exact container test commands for the scenarios listed above. No foreign framework or Craft application behavior tests were run during this source review.

## Notes

For humans: searchable commands and service signatures. For agents: version-correct bounded context. Effort: medium. Start with CLI; MCP can wrap approved read-only endpoints later. Inspect initialization risks before asserting no side effects; arbitrary service constructors must not be invoked blindly.

Review: `backlog/pending/p2-20261003-231656-source-framework-ergonomics-review.md`.

Craft source baseline: `58f510c344f5362de1a4b35f98190ef2147228c7`. Local references were read from the working tree; unrelated existing worktree changes were preserved. Foreign source links use immutable commit SHAs, not moving branches. Findings are static source analysis unless explicitly stated otherwise.

Research does not authorize implementation. Keep autonomous false until the owner decides. No application code was changed. Source-level lessons require adaptation to Python, Craft's runtime and existing safety contracts; no performance or usability multiplier has been measured.

## History

- 2026-10-03T23:17:02Z created by codex (source: owner-corrected GitHub code comparison; suggestion awaiting owner decision)
