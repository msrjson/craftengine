---
id: "20261005-100115"
title: Move the craftengine.org landing page from website/ to data-website/
type: chore
priority: 2
autonomous: true
blocked_by: none
max_attempts: 2
claimed_by: claude@claude-code
attempts: 1
created_at: 2026-10-05T10:01:15Z
updated_at: 2026-10-05T10:30:44Z
source: owner ruling 2026-10-05 (session)
touches:
  - website/
  - data-website/
---

## Problem

The owner set three separate contexts in the workspace: `data/` (slim framework), `data-demo/` (demo application) and `data-website/` (landing page). The landing page still lives in `website/`.

## Evidence

- `website/` at the workspace root; `data-website/` created empty by the owner on 2026-10-05.

## Done when

- [ ] The local site repository lives in `data-website/`; `.gitignore`, `docker-compose.yml` and the open tasks point at it. The DigitalOcean app builds `/` from the GitHub repository `msrjson/craftengine.org`, not from a local path, so its spec is unchanged and no deploy is triggered.
- [ ] Nothing under `data/` or `data-demo/` is required to build the site.

## Verify

```bash
git ls-files website data-website | head
```

## Notes

Touches the deploy of craftengine.org: the owner confirms before the app spec changes.

## History

- 2026-10-05T10:01:15Z created by claude@claude-code (source: owner ruling 2026-10-05)
- 2026-10-05T10:02:11Z owner ruling: the landing page directory is named data-website/ (was data-craftengine.org/) (owner, relayed by claude@claude-code)
- 2026-10-05T10:30:17Z owner ruling: move now and adjust references, no deploy; autonomous true, blocked_by none (owner, relayed by claude@claude-code)
- 2026-10-05T10:30:17Z claimed by claude@claude-code (attempt 1)
- 2026-10-05T10:30:44Z resolved by claude@claude-code (resolutions/p2-20261005-100115-move-website-to-data-craftengine-org.resolution.md)
