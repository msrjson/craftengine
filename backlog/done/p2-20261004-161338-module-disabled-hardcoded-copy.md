---
id: "20261004-161338"
title: The kernel answers a disabled module with hardcoded English copy
type: bugfix
priority: 2
autonomous: true
blocked_by: none
max_attempts: 2
claimed_by: claude@claude-code
attempts: 1
created_at: 2026-10-04T16:13:38Z
updated_at: 2026-10-05T10:26:03Z
source: evaluation of the boundary/proxy release, 2026-10-04
touches: 
  - data/engine/http/kernel.py
  - data/tests/
---

## Problem

A route of a disabled module returns `JSONResponse({"error": "Module Disabled"}, status_code=404)` from the kernel: a rendered English sentence instead of `code` + `message_key`, against R2 and the error contract the kernel itself uses for exceptions (`{"error": {"code", "message_key"}}`).

## Evidence

- `data/engine/http/kernel.py` module check, the `JSONResponse({"error": "Module Disabled"}...)` line.
- The same function renders other errors through `render_exception` with `code` / `message_key`.

## Done when

- [ ] The response carries `{"error": {"code": "MODULE_DISABLED", "message_key": "..."}}` (or a typed exception rendered by the handler), status 404 unchanged.
- [ ] The key has en, pt-BR and es rows in the same change.
- [ ] A test requests a route of a disabled module and asserts the code.

## Verify

```bash
docker exec framework sh -lc 'cd /app && python -m pytest tests -q -k module'
cd data && python tools/check_engine_boundary.py
```

## Notes

Coordinate with `p2-20261004-152410-kernel-event-loop-db-access`, which touches the same check.

## History

- 2026-10-04T16:13:38Z created by claude (source: evaluation of the boundary/proxy release, 2026-10-04)
- 2026-10-05T10:26:03Z claimed by claude@claude-code (attempt 1)
- 2026-10-05T10:26:03Z resolved by claude@claude-code (resolutions/p2-20261004-161338-module-disabled-hardcoded-copy.resolution.md)
