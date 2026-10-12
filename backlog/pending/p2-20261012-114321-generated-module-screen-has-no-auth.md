---
id: "20261012-114321"
title: A generated module screen is served without sign-in
type: decision
priority: 2
autonomous: false
blocked_by: owner-decision
max_attempts: 2
attempts: 0
created_at: 2026-10-12T11:43:21Z
updated_at: 2026-10-12T11:43:21Z
source: demo README rewrite for release 4.8.0, 2026-10-12
touches:
  - data/engine/cli/extension_templates/module/routes.py.stub
  - data/engine/cli/extension_scaffolder.py
  - data/documentation/
---

## Problem

The module scaffolder writes its index route with no middleware, so a module
generated from the CLI is reachable by anyone until the developer adds
`.middleware("auth")` by hand. The demo shipped two such screens (`/tickets`,
`/invoices`) open to guests for a week before a documentation pass noticed.

## Evidence

- `data/engine/cli/extension_templates/module/routes.py.stub:12` - the route is registered with a name and no middleware.
- `data-demo/app/modules/tickets/routes.py:12` and `data-demo/app/modules/invoices/routes.py:12` - generated from that stub; fixed in the demo on 2026-10-12 with a guest-redirect test.

## Done when

- [ ] The owner decides the default: generated screens behind `auth`, a scaffolder flag, or public by default with a visible warning.
- [ ] The stub, the scaffolder and the guide follow the decision, with a test that pins the generated route.

## Verify

```bash
docker exec framework sh -lc 'cd /app && python -m pytest tests/test_extensions.py -q'
```

## Notes

A secure default would change what the generator emits for projects that have
no auth scaffold yet (`make auth` not run), so the route would point at a
middleware alias the project may not have. That trade-off is the decision.

## History

- 2026-10-12T11:43:21Z created by claude@claude-code (source: demo README rewrite for release 4.8.0, 2026-10-12)
