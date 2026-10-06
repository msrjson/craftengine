---
task: p2-20261006-205421-extension-update-message-migration
outcome: resolved
agent: gpt@codex
started_at: 2026-10-06T20:54:21Z
finished_at: 2026-10-06T21:03:16Z
commits: []
---

## What changed

- Added a new forward-only message-seeding migration to the framework tree and project skeleton.
- New ownership/update refusal keys exist in en, pt-BR and es; seeding inserts missing rows and preserves operator edits.
- Documented how an existing project upgrading only the engine package adds this application migration; no previously applied migration was edited.

## Verification

- Final `tests/test_extension_updates.py tests/test_extensions.py tests/test_project_scaffolder.py tests/test_package_data.py`: 92 passed on SQLite and PostgreSQL in the framework container.
- New tests verify all refusal keys exist in the three database locales and updates preserve edited translations and business records.
- Full framework suites: 1956 passed / 66 skipped on SQLite; 2018 passed / 4 skipped on PostgreSQL (before final restart validation centralization, reverified in targeted suites).
- Backlog and board gates and `git diff --check`: clean.
- No shared database migration was executed; PostgreSQL tests used newly created session databases and retained them.

## Follow-ups

None for this framework correction. The pre-existing application-owned CRM/extension-panel task remains with its claimant; no demo or website work was performed.
