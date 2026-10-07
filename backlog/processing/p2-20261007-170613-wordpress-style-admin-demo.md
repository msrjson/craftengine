---
id: "20261007-170613"
title: WordPress-style admin backend for data-demo, built as extensions
type: feature
priority: 2
autonomous: true
blocked_by: none
max_attempts: 2
attempts: 1
claimed_by: qwen@qwen-code
created_at: 2026-10-07T17:06:13Z
updated_at: 2026-10-07T19:09:16Z
source: owner decision 2026-10-07 (in session)
touches:
  - data-demo/app/
  - data-demo/resources/
  - data-demo/routes/
  - data-demo/tests/
---

## Problem

The owner wants `data-demo/` to stop being only a mini CRM and become a
**WordPress-style administration backend** — a professional login screen and a
dashboard resembling the WordPress admin — so the demo is a real application
that exercises the framework and the `dev.py` CLI. The build is also the
instrument: measure the time each screen takes to produce, fix the failures it
surfaces, and turn every `dev.py` friction into an improvement.

## Evidence

- Owner, 2026-10-07: "o data demo e uma versao de um mini crm, preciso que ele
  seja um clone do backend admin do wordpress ... tela de login profissional e
  dashboard similar ao do wordpress, queremos medir o tempo de producao corrigir
  falhas e melhorar nosso comando cli o dev.py".
- Owner answers 2026-10-07: first delivery = **full admin**; build it as
  **extensions on `data-demo`** (modules/plugins/theme + the internal proxy);
  measure time and failures through the **backlog queue + board FINDINGS**.
- Current demo, for reference: modules `companies`, `contacts`, `deals`,
  `activities`, `dashboard`, `extension_manager`, `audit_log`, theme `harbor`
  (`data-demo/README.md`).

## Done when

Slices, in this order; each slice is done when its screens render with the theme,
carry translation keys in en/pt-BR/es, and the demo suite stays green:

- [x] Slice 1 - professional login screen and the admin chrome (left sidebar
      menu, top bar) as a WordPress-style theme.
- [x] Slice 2 - dashboard (Home) with WordPress-like widgets (At a Glance,
      Activity, Quick Draft).
- [x] Slice 3 - Posts (list + editor).
- [x] Slice 4 - Pages (list + editor).
- [ ] Slice 5 - Users (list, add, roles), reusing the RBAC admin.
- [ ] Slice 6 - Media (library + upload) on the storage layer.
- [ ] Slice 7 - Menus (navigation) and Settings.
- [ ] Each slice's History carries `created_at`/`finished_at`, and every `dev.py`
      friction becomes a board FINDING that names the command and the fix.

## Verify

```bash
docker exec craftengine-demo sh -lc 'cd /app && python -m pytest tests -q'
sh .agents/scripts/rehearse-demo.sh
```

## Notes

- Demo context only: nothing here edits `data/` (the framework). A defect that is
  really the framework's becomes a FINDING and a `data/` task, never a demo edit.
- The demo's `craft-engine.lock` pins the released engine (`v4.7.0-r00027` as of
  2026-10-07); a framework change reaches the demo only through a release.
- Coordinates with `p2-20261005-095553` (CRM demo on the extension model, in
  `processing/`): this task extends that deliverable, it does not replace the
  extension-model work already done. Claim only after that task releases the
  `data-demo/` paths.
- Time measurement is the backlog's own History (BQ-03/BQ-04): `created_at` to
  `finished_at` per slice, plus the friction FINDINGS.

## History

- 2026-10-07T17:06:13Z created by qwen@qwen-code (owner decision 2026-10-07: data-demo becomes a WordPress-style admin, built as extensions, measured through the queue)
- 2026-10-07T18:51:10Z claimed by qwen@qwen-code (attempt 1; owner authorised crossing the data-demo/ claim of p2-20261005-095553, dev version)
- 2026-10-07T18:54:33Z slice 1 landed by qwen@qwen-code: the harbor theme gained the WordPress-style chrome (top admin bar + left menu from the active modules) and a dedicated auth shell for login/register; en/pt-BR/es keys, progressive-enhancement menu toggle. Demo suite 66 passed on SQLite and PostgreSQL (rehearse-demo.sh, engine 4.7.0 r00027), data-demo commit a372c26. Slices 2-7 remain; the task stays claimed in processing/
- 2026-10-07T19:00:58Z slice 2 landed by qwen@qwen-code: the overview is now a widget grid (At a Glance, Activity, Quick Draft); the quick draft is scheduled through the activities module's new proxy surface (`expose("activities", ...)`), so the dashboard imports no module and degrades when activities is off. Demo suite 70 passed on SQLite and PostgreSQL (rehearse-demo.sh, engine 4.7.0 r00027), data-demo commit 3e2277c. Slices 3-7 (Posts, Pages, Users, Media, Menus/Settings) remain
- 2026-10-07T19:06:51Z slice 3 landed by qwen@qwen-code: a new `posts` module (repository/service/controller/views, forward-only migration, soft deletes) with a list and an editor plus a publish/draft toggle, exposed on the proxy as `posts`; the dashboard's Quick Draft was corrected to create a post draft (WordPress semantics) and refreshes to the post list. Demo suite 77 passed on SQLite and PostgreSQL (rehearse-demo.sh, engine 4.7.0 r00027), data-demo commits 1e1d839 and 2119597; posts installed and activated in the live demo. Slices 4-7 (Pages, Users, Media, Menus/Settings) remain
- 2026-10-07T19:09:16Z slice 4 landed by qwen@qwen-code: a new `pages` module mirroring posts (list, editor, publish/draft), exposed on the proxy as `pages` with its own dashboard card; demo suite 84 passed on SQLite and PostgreSQL (rehearse-demo.sh, engine 4.7.0 r00027), data-demo commit f144bfe; pages installed and activated in the live demo. Slices 5-7 (Users, Media, Menus/Settings) remain
