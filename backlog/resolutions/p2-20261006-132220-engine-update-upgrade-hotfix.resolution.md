---
task: p2-20261006-132220-engine-update-upgrade-hotfix
outcome: resolved
agent: claude@claude-code
started_at: 2026-10-06T13:23:30Z
finished_at: 2026-10-06T13:37:02Z
---

## Summary

New package `engine/lifecycle/` (lock, release identity, manifest and drift,
tag-archive source, changelog notes, patch planner, transactional applier,
service) and the `engine` command group (`adopt`, `status`, `patch`,
`hotfix`, `update`, `upgrade`). `craft new` writes a `package` lock.
Decision recorded in `docs/adr/0005-engine-lifecycle.md`; guide in
`data/documentation/engine-lifecycle.md`; CHANGELOG under Unreleased.

## Verification

- `docker exec framework sh -lc 'cd /app && python -m pytest tests/test_engine_lifecycle.py tests/test_project_scaffolder.py -q'` -> 43 passed
- `docker exec framework sh -lc 'cd /app && python -m pytest tests -q -x'` -> 1903 passed, 66 skipped (SQLite)
- `docker exec framework sh -lc 'cd /app && ruff check engine'` -> All checks passed!
- `docker exec framework sh -lc 'cd /app && python dev.py docs check'` -> 40 page(s), no broken links
- `cd data && python3 tools/lint_language.py --config language-standard.toml` -> clean
- `cd data && python3 tools/check_engine_boundary.py` -> ENGINE_BOUNDARY_NEW_FINDINGS 0
- End to end against the canonical GitHub repository, in a scratch project
  inside the container: `engine adopt v4.4.1-r00023 --mode vendored` (296
  files), `engine hotfix v4.4.2-r00024 http/response.py`, `engine update
  --dry-run` (patch retired as absorbed), `engine update --verify ...`
  (verify ran against the new engine, moved to v4.4.2-r00024, no scratch
  directories left), `engine status` clean.
- PostgreSQL suite not run: the change touches no database code. UNVERIFIED on PostgreSQL.
