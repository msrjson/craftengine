---
task: p2-20261003-223200-port-internal-proxy
outcome: resolved
agent: claude
started_at: 2026-10-04T01:00:00Z
finished_at: 2026-10-04T14:26:10Z
---

## What changed

- `data/engine/container/internal_proxy.py`: `InternalProxy` (`expose`, `exposed`, `call`, async `dispatch`, `emit`) and `InternalProxyError` (machine `code`, `message_key`). Ported from the SoftPax design, with these differences:
  - no own context type and no `scope()`: tenant, connection, auth, locale and request id already live in context variables and travel with the call (`asyncio.to_thread` copies the context);
  - no tenant check, per the owner's two-barrier ruling (2026-10-03);
  - `expose` refuses undefined methods at boot, not only in tests;
  - errors follow the engine's pattern for programming errors (`code` + `message_key` class attribute, rendered as a 500 `error.server`), so no translation rows were seeded - the same as `SignerKeyMissingError` and `TenantNotBoundError`.
- `InternalProxyServiceProvider` in the default provider list (singleton `proxy`, aliased by class) and the `Proxy` facade.
- `Container.make`: a dotted path bound to itself no longer recurses (reproduced first by `tests/test_container_self_binding.py`: RecursionError, then 2 passed).
- Guide `documentation/internal-proxy.md` with the `BillingService.generate_invoice` example; nothing was added to `data/app/`.
- Non-ASCII dashes in `engine/container/application.py` and `engine/facades/__init__.py` normalized (the edit-time gate blocked on them).

## Verification

```bash
docker exec framework sh -lc 'cd /app && python -m pytest tests/test_internal_proxy.py -q -s'
#   18 passed; proxy_call_seconds=0.0000046 loopback_http_seconds=0.0025916
#   includes tenant-a / tenant-b / owner concurrent context on the worker thread,
#   one kernel pass (RequestTerminated count) for a request that calls another module
docker exec framework sh -lc 'cd /app && python -m pytest tests/test_container_self_binding.py -q'   # 2 passed (RecursionError before the fix)
docker exec framework sh -lc 'cd /app && ruff check .'                                              # All checks passed
docker exec framework sh -lc 'cd /app && python -m pytest tests -q'                                 # 1759 passed, 66 skipped
docker exec framework sh -lc 'cd /app && CRAFT_TEST_DB=pgsql python -m pytest tests -q'             # 1821 passed, 4 skipped
docker exec framework sh -lc 'cd /app && python dev.py docs:check'                                  # 37 page(s), no broken links
cd data && python tools/check_engine_boundary.py                                                    # ENGINE_BOUNDARY_NEW_FINDINGS 0
```

The tenant-context test uses context variables only. Row-level security under PostgreSQL with the proxy's worker thread is UNVERIFIED beyond the full PostgreSQL suite passing.
