---
id: "20261003-223128"
title: Get craftengine.org categorized so corporate proxies stop blocking it
type: chore
priority: 3
autonomous: false
blocked_by: owner-action
max_attempts: 2
attempts: 0
created_at: 2026-10-03T22:31:28Z
updated_at: 2026-10-03T22:31:28Z
source: docs/backlog.md Also open
touches: []
---

## Problem

The current registration dates from 2026-09-18 (GoDaddy, Cloudflare DNS), so web filters classify `craftengine.org` as a Newly Registered Domain and block it, usually for the first 30 days (until about 2026-10-18).

## Evidence

- Earlier owners (2017-2025) only parked the domain; the archive shows no abusive content.

## Done when

- [ ] The domain was submitted as Software/Technology to Palo Alto, Fortinet, Zscaler, Cisco Talos, Broadcom and Trellix.
- [ ] The site opens from a corporate network.

## Verify

```bash
curl -sSI https://craftengine.org | head -1
```

## Notes

Submissions use the owner's identity; agents do not file them.

## History

- 2026-10-03T22:31:28Z created by claude (source: docs/backlog.md Also open; migrated from the single-file backlog)
