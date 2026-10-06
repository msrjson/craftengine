---
task: p2-20261006-205116-extension-lifecycle-and-architecture
outcome: resolved
agent: gpt@codex
started_at: 2026-10-06T20:51:16Z
finished_at: 2026-10-06T21:03:16Z
commits: []
---

## What changed

- Added owned, reversible service registrations and scoped cache generations; existing service/alias collisions are refused.
- Added inactive extension updates with forward-only schema changes, translation preservation, downgrade/kind checks and installed dependent compatibility.
- Preserved installed versions on lifecycle transitions; validated compatibility on activation, boot and reconciliation; dependency-first reconciliation.
- Required worker restart on all load paths after updating and refused cached Python versions across managers; rolled back partial route registration.
- Added architecture/CMS composition guidance, updated extension/CLI documentation, ADR and changelog. Modern and legacy lifecycles are explicitly distinguished.
- Corrected the existing boot isolation fixture to persist each installed manifest's actual version, preserving its original isolation assertions.

## Verification

- `docker exec framework sh -lc 'cd /app && python -m pytest tests -q'`: 1956 passed, 66 skipped; full SQLite suite before the final restart-check centralization.
- `docker exec -e CRAFT_TEST_DB=pgsql -e DB_SSLMODE=disable framework sh -lc 'cd /app && python -m pytest tests -q'`: 2018 passed, 4 skipped; full PostgreSQL suite before the final restart-check centralization.
- Final targeted verification after centralizing restart validation on all load paths: `tests/test_extension_updates.py tests/test_extensions.py tests/test_project_scaffolder.py tests/test_package_data.py`: 92 passed on SQLite and PostgreSQL, in the framework container.
- Independent `tests/test_extension_updates.py`: 22 passed before adding the final two boot/reconcile restart regressions; those regressions passed in the final targeted suites.
- `ruff check engine tests/test_extension_updates.py`: clean in the framework container.
- `(cd data && python tools/check_engine_boundary.py)`: 0 new findings.
- Both data language configurations and explicit architecture/ADR documentation checks: clean.
- Backlog and board gates, including staged checks, and `git diff --check`: clean.
- Structure gate exits 0 and reports disabled by the existing project configuration; it was not changed. New extension functions/tests respect the 25-line cap.

## Follow-ups

None for this framework correction. The pre-existing application-owned CRM/extension-panel task remains with its claimant; no demo or website work was performed.
