---
id: "20261003-223200"
title: Port the in-process internal proxy from SoftPax into the engine container
type: feature
priority: 2
autonomous: false
blocked_by: none
max_attempts: 2
attempts: 0
created_at: 2026-10-03T22:32:00Z
updated_at: 2026-10-04T14:26:10Z
source: owner request 2026-10-03 (plan approved in session); SoftPax commits 216ccf8b, 41b7c3a1
touches: [data/engine/container/, data/engine/providers/, data/engine/facades/__init__.py, data/tests/test_internal_proxy.py, data/documentation/internal-proxy.md, data/CHANGELOG.md]
---

## Problem

Module-to-module communication has no sanctioned path, so code either loops back over HTTP through the kernel (full ASGI and middleware cost, worker starvation) or is written into the engine itself. The engine needs an in-process proxy: external traffic enters only through the HTTP kernel; internal calls resolve an exposed service from the container and run in memory. Internal versus external is decided by the channel (only in-process code can reach the proxy, no route maps to it), never by a header.

## Evidence

- SoftPax reference (read-only, never copied): `/data/projects/workspaces/softpax/data/engine/container/internal_proxy.py` (240 lines, no app imports): `expose`, `call`, async `dispatch`, `emit`, `scope`; sync handlers through `asyncio.to_thread` with a cancellation shield (`:85-103`); typed errors with `code` + `message_key`; 20 tests in `data/tests/test_internal_proxy.py`.
- Canonical gaps: no proxy; `Container.bind(concrete=None)` sets `concrete = abstract` (`data/engine/container/application.py:88-89`) and a string key may recurse in `make` (`:138`) - SoftPax fixed this with a `concrete == key` branch.
- Reusable canonical pieces: request context with `request_id` already logged (`data/engine/support/context.py:33`, `support/logging.py`); tenant `current_tenant_id()` / `TenantNotBoundError` (`data/engine/orm/tenancy.py:44,47`); `current_locale` (`data/engine/support/translation.py:36`); `EventDispatcher.dispatch(event, halt)` (`data/engine/events/dispatcher.py:100`).

## Done when

- [x] `data/engine/container/internal_proxy.py` with `expose(alias, abstract, methods)`, `call`, async `dispatch`, `emit`, `scope`; deny by default, `_`-prefixed and missing methods refused at `expose` time (boot), not only in tests. The proxy is routing infrastructure only: no tenant, authorization or business rule inside it.
- [x] Tenant isolation stays with the two barriers that own it - barrier 1, the codebase (modules and controllers), and barrier 2, the database (RLS). The proxy never resolves, guesses or rewrites a tenant; it only carries the caller's context unchanged, including into the `to_thread` path, so barrier 2 still sees the connection and tenant stamp. Proven by a tenant A / tenant B / owner test on a real database.
- [x] Correlation id reuses the existing request context `request_id` (no second ContextVar), so log lines carry it at no extra cost.
- [x] Tenant type is `str`, matching `tenancy.py`.
- [x] Durable-event marker: `emit` refuses events with `durable = True` (they belong to the outbox/queue).
- [x] The `bind` string-key recursion is reproduced by a failing test first, then fixed.
- [x] `InternalProxyServiceProvider` in the default provider list, singleton key `proxy`, facade `Proxy` (additive, NR-05).
- [x] Error keys `internal_proxy.errors.*` seeded in `en`, `pt-BR`, `es`.
- [x] Tests without app imports: allowlist, private/missing methods, sync/async, cancellation waits for the thread, context in nested calls, tenant A/B concurrent context isolation with `asyncio.gather`, `emit`, and an end-to-end request whose action calls the proxy with a spy middleware counting exactly one kernel pass.
- [x] Guide with the `BillingService.generate_invoice` example (docs and test fixtures only, never in `data/app/`).

## Verify

```bash
docker exec <app-container> sh -lc 'cd /app && python -m pytest tests/test_internal_proxy.py -q'
docker exec <app-container> sh -lc 'cd /app && python -m pytest tests -q'
docker exec <app-container> sh -lc 'cd /app && ruff check engine'
python .claude/rules/lint_structure.py
python .claude/rules/lint_language.py --config language-standard.toml
```

## Notes

Owner ruling 2026-10-03: the proxy is routing infrastructure; tenant rules belong to modules/controllers (barrier 1) and the database (barrier 2), never to the proxy, which must stay lean. Architecture: not delegable to the local model. The design was approved by the owner on 2026-10-03; SoftPax's API names (`call` / `dispatch` / `emit`) are kept so both projects speak the same contract. Wait for `p1-20261003-223121-uncommitted-revert-of-v4-2-0` to be settled before editing engine files.

## History

- 2026-10-03T22:32:00Z created by claude (source: owner request + SoftPax study)
- 2026-10-03T22:45:00Z owner ruling: tenant enforcement removed from the proxy scope (two-barrier model); proxy only carries context
- 2026-10-04T14:26:10Z resolved by claude (resolutions/p2-20261003-223200-port-internal-proxy.resolution.md)
