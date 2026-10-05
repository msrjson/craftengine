---
id: "20261005-112115"
title: Give the internal proxy a call that degrades when the owner cannot serve
type: feature
priority: 2
autonomous: false
blocked_by: owner-decision
max_attempts: 2
attempts: 0
created_at: 2026-10-05T11:21:15Z
updated_at: 2026-10-05T11:21:15Z
source: CRM demo (data-demo), 2026-10-05
touches:
  - data/engine/container/internal_proxy.py
  - data/tests/test_internal_proxy.py
  - data/documentation/internal-proxy.md
---

## Problem

A screen that shows another module's data must keep working when that module is deactivated or its circuit breaker is open. Extensions cannot share code, so the CRM demo had to copy the same try/except around `Proxy.call` into three modules (contacts, deals, activities). Every consumer of the proxy will repeat it.

## Evidence

- `data-demo/app/modules/{contacts,deals,activities}/services/*_service.py`: identical `_ask(alias, method, *args, default)` helpers catching `InternalProxyError`.

## Done when

- [ ] Owner decides the name and contract, e.g. `Proxy.call_or(default, alias, method, *args)` returning `default` on `INTERNAL_TARGET_NOT_EXPOSED` / `INTERNAL_TARGET_UNAVAILABLE` only (an exception raised by the target itself still propagates).
- [ ] Sync and async variants, tests, guide section; the demo drops its three copies after the release.

## Verify

```bash
docker exec framework sh -lc 'cd /app && python -m pytest tests/test_internal_proxy.py -q'
```

## Notes

Found by the CRM demo, which exercises the extension model as a third party would.

## History

- 2026-10-05T11:21:15Z created by claude@claude-code (source: CRM demo, 2026-10-05)
