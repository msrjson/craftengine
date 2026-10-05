---
id: "20261005-100115"
title: Move the craftengine.org landing page from website/ to data-website/
type: chore
priority: 2
autonomous: false
blocked_by: owner-decision
max_attempts: 2
attempts: 0
created_at: 2026-10-05T10:01:15Z
updated_at: 2026-10-05T10:02:11Z
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

- [ ] The landing page builds from `data-website/`; the DigitalOcean app spec and deploy scripts point at it (skill do-app-isolation).
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
