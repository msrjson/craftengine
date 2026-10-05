---
id: "20261005-095553"
title: Complete CRM demo application built only from extensions
type: feature
priority: 2
autonomous: true
blocked_by: none
max_attempts: 2
claimed_by: claude@claude-code
attempts: 1
created_at: 2026-10-05T09:55:53Z
updated_at: 2026-10-05T10:54:46Z
source: owner request 2026-10-05 (session), after the extension model plan
touches:
  - data-demo/
---

## Problem

The slim engine needs a complete, database-backed application that proves the extension model end to end, without changing the official demo: a CRM built only from modules, plugins and a theme.

## Evidence

- ADR 0001 removed the demo application from the framework repository; the extension model (tasks extension-*) gives the seams a demo must exercise.

## Done when

- [x] Location: `data-demo/` at the workspace root (owner ruling 2026-10-05); `data/` holds only the slim framework, `data-website/` only the landing page; the three never share code.
- [x] Engine source: the canonical remote pinned to a tag, `git+https://github.com/msrjson/craftengine.git@<tag>` (owner ruling 2026-10-05).
- [x] Publication: built and committed locally; the owner pushes after review (owner ruling 2026-10-05).
- [x] Release v4.4.0-r00022 published (tag on 166741d) and public repository msrjson/craftengine-demo created (owner, 2026-10-05).
- [ ] CRM modules (contacts, companies, deals, activities), one plugin, one theme and the extension manager panel, with migrations, seeders and three-locale keys.
- [ ] The engine comes from the canonical Git remote, never copied from this workspace.
- [ ] A failing CRM extension leaves the rest of the CRM serving (demonstrated by a test).

## Verify

```bash
docker exec <crm-demo-app> sh -lc 'cd /app && python -m pytest tests -q'
```

## Notes

Owner request 2026-10-05: "framework slim + demo"; the demo is a complete application with a database. Depends on every extension-* task.

## History

- 2026-10-05T09:55:53Z created by claude@claude-code (source: owner request 2026-10-05)
- 2026-10-05T10:01:15Z owner ruling: the demo lives in data-demo/, data/ is the slim framework only, data-website/ holds the landing page; no context is mixed (owner, relayed by claude@claude-code)
- 2026-10-05T10:02:11Z owner ruling: the landing page directory is named data-website/ (was data-craftengine.org/) (owner, relayed by claude@claude-code)
- 2026-10-05T10:29:04Z owner ruling: data-demo installs the engine from the canonical Git remote pinned to a tag; nothing is pushed before the owner reviews. Blocked on the owner cutting and pushing the release with the extension model (owner, relayed by claude@claude-code)
- 2026-10-05T10:54:46Z owner ruling: release v4.4.0-r00022 published and craftengine-demo created; build the demo now (autonomous true, blocked_by none) (owner, relayed by claude@claude-code)
- 2026-10-05T10:54:46Z claimed by claude@claude-code (attempt 1)
