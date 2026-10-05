---
id: "20261004-161339"
title: Give the internal proxy its first real consumer and decide on typed contracts
type: decision
priority: 2
autonomous: false
blocked_by: owner-decision
max_attempts: 2
attempts: 0
created_at: 2026-10-04T16:13:39Z
updated_at: 2026-10-05T10:26:14Z
source: evaluation of the boundary/proxy release, 2026-10-04
touches: []
---

## Problem

The internal proxy is used only by its tests and the benchmark. Targets are string aliases (`"billing"`, `"generate_invoice"`): a typo surfaces only at call time when `expose` received a container key instead of a class, and editors cannot rename across modules.

## Evidence

- `data/engine/container/internal_proxy.py`: `expose(alias, abstract, methods)`, `call`, `dispatch`.
- SoftPax has one consumer (`app/Http/Controllers/Fiscal/TaxInvoiceController.py`); the canonical framework has none.

## Done when

- [ ] Owner decides: keep string aliases, add typed contracts (a Protocol per exposed service, `proxy.contract(BillingContract)`), or both.
- [ ] A first real module-to-module call in a generated project (or the skeleton's docs example turned into a tested fixture) goes through the proxy.
- [ ] `make:` generators or docs show how a module exposes a service.

## Verify

```bash
docker exec framework sh -lc 'cd /app && python -m pytest tests/test_internal_proxy.py -q'
```

## Notes

Architecture: not delegable to the local model.

## History

- 2026-10-04T16:13:39Z created by claude (source: evaluation of the boundary/proxy release, 2026-10-04)
- 2026-10-05T10:26:14Z note by claude@claude-code: criterion 2 now has a tested consumer - fixture module `ordering` calls `catalog` only through the proxy (tests/test_extensions.py, commit 9352e47); exposures can be owned by an extension (`context.expose`). The typed-contract decision is still the owner's.
