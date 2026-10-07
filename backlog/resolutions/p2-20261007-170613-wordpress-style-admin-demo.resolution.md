---
task: p2-20261007-170613-wordpress-style-admin-demo
outcome: resolved
agent: qwen@qwen-code (local Ollama)
started_at: 2026-10-07T18:51:10Z
finished_at: 2026-10-07T19:19:42Z
commits: [a372c26, 3e2277c, 1e1d839, 2119597, f144bfe, 7ff1f4d, 97a8034, e758348]
---

## What changed

The demo became a WordPress-style admin, delivered in the seven planned slices;
every file is under `data-demo/`.

- **Slice 1** (`a372c26`) - the `harbor` theme gained the admin chrome (top bar
  and a left menu built from the active modules) and a dedicated auth shell for
  login/register; a progressive-enhancement menu toggle.
- **Slice 2** (`3e2277c`) - the overview became a widget grid: At a Glance,
  Activity and Quick Draft; the activities module gained a proxy surface.
- **Slice 3** (`1e1d839`, `2119597`) - a new `posts` module (list, editor,
  publish/draft) exposed as `posts`; Quick Draft corrected to draft a post.
- **Slice 4** (`f144bfe`) - a new `pages` module mirroring posts.
- **Slice 5** (`7ff1f4d`) - an admin-only `users` module (list, add, roles) on
  the RBAC models.
- **Slice 6** (`97a8034`) - a `media` module: upload to the storage layer, a
  serve route, soft-deleted rows, thumbnails.
- **Slice 7** (`e758348`) - a `settings` module (general settings on the engine
  settings store + menu visibility), wired into `AppServiceProvider` and the
  theme.

## Verification

Run in the `framework`-style container for the demo (`craftengine-demo`), after
each slice and once more at the end:

- `docker exec craftengine-demo sh -lc 'cd /app && python -m pytest tests -q'`
  -> **105 passed** (was 55 before the work).
- `sh .agents/scripts/rehearse-demo.sh` (engine 4.7.0 r00027, fresh database)
  -> SQLite **105 passed**, disposable PostgreSQL 18 **105 passed**.
- Per slice: 66 / 70 / 77 / 84 / 92 / 98 / 105 passed (see the task History).
- Each new module was installed and activated in the running demo
  (`dev.py extension install|activate <slug>`) and its copy re-synced, so the
  live container matches the code.

## Follow-ups

- New task files: none. The `dev.py` friction found (no way to re-seed the
  catalog of an already-installed extension) is recorded on the team board as a
  FINDING with the command and the fix.
- Demo-side brittleness noted but not changed: `data-demo/tests/conftest.py`
  lists the extensions by hand and `test_crm.py` pins the count, so every new
  module needs both updated.
