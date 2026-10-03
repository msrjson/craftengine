---
id: "20261003-223127"
title: Confirm craftengine.org nameservers at the registrar
type: chore
priority: 3
autonomous: false
blocked_by: owner-action
max_attempts: 2
attempts: 0
created_at: 2026-10-03T22:31:27Z
updated_at: 2026-10-03T22:31:27Z
source: docs/backlog.md Also open
touches: []
---

## Problem

On 2026-09-24 `craftengine.org` did not resolve from the development machine while other domains did.

## Evidence

- Observation from the development machine, 2026-09-24.

## Done when

- [ ] The registrar lists the Cloudflare nameservers.
- [ ] The domain resolves from the development machine and from a public resolver.

## Verify

```bash
dig +short NS craftengine.org
dig +short craftengine.org @1.1.1.1
```

## Notes

Registrar access is the owner's. An agent may run Verify and resolve the task if both checks pass.

## History

- 2026-10-03T22:31:27Z created by claude (source: docs/backlog.md Also open; migrated from the single-file backlog)
