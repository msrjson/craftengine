---
task: p1-20261012-113637-release-4-8-0-and-wordpress-demo
outcome: resolved
agent: claude@claude-code
started_at: 2026-10-12T11:37:36Z
finished_at: 2026-10-12T11:57:27Z
commits: [63e2450, 8a8bf33, 01482f5]
---

## What changed

Craft Engine 4.8.0 r00028 was cut from the 36 unreleased changelog entries:
`CHANGELOG.md` promoted, `pyproject.toml`, `engine/__init__.py`, `VERSION` and
`CRAFT_ENGINE.md` in sync. The guides were audited against every entry and 12
of them updated. Workspace documents and the rehearsal script name the demo a
WordPress-style admin and point at `.agents/scripts/`.

The demo (`data-demo/`, repository `msrjson/craftengine-demo`, commits
2c96905 and 1f60655) has a README written around what it validates, its 18
extensions listed, `/tickets` and `/invoices` behind sign-in with a
guest-redirect test, no visible CRM naming in the three locales, and the engine
pin moved to `v4.8.0-r00028` with `engine upgrade --to 4.8.0`. It was pushed
to its public repository for the first time.

## Verification

- `docker exec framework sh -lc 'cd /app && python -m pytest tests -q'` with the
  local `.env` moved aside -> SQLite 2169 passed, 68 skipped; PostgreSQL
  (`CRAFT_TEST_DB=pgsql`) 2232 passed, 5 skipped. The first run failed 4 tests in
  `tests/test_release_sync.py` because `VERSION` had not been bumped; fixed and
  rerun in full.
- `ruff check engine` -> All checks passed. `python tools/check_engine_boundary.py`
  (host, needs Git) -> 0 new findings. `python tools/check_data_safety.py` -> clean.
  Both language passes -> clean. `python dev.py docs:check` -> 43 pages, no broken links.
- `sh .agents/scripts/rehearse-demo.sh` (engine 4.8.0 r00028) -> 109 passed on
  SQLite and 109 on a disposable PostgreSQL.
- CI run 38245180214 on `master` -> success in every job; run 38245180324 on
  `main` -> both test jobs, the image build and the release job succeeded, the
  Pages job was cancelled by the concurrency group as expected. Release
  `v4.8.0-r00028` exists and its tag points at 01482f5.
- Demo container rebuilt on the new pin: `engine status` reports pinned and
  running v4.8.0-r00028, `migrate` had nothing to run, the suite passed 109 on
  SQLite. A guest request to `http://localhost:9002/tickets` answers 302.
- UNVERIFIED: `https://craftengine.org/docs/` could not be reached from this
  machine (no HTTP answer), so the published documentation was not seen live.

## Follow-ups

- `backlog/pending/` generated-module-screen-has-no-auth: owner decision on the scaffolder default.
- The running demo database still shows the old application name: translation
  rows already seeded are not refreshed, and no command re-seeds an installed
  extension's catalog (finding on the board, 2026-10-07).
- Running the demo suite with `CRM_TEST_DB=pgsql` inside `craftengine-demo`
  points it at the live demo database; it stops at `EXTENSION_ALREADY_INSTALLED`
  and changes nothing, but the PostgreSQL evidence for the demo is the rehearsal.
