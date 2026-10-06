---
task: p2-20261006-190059-demo-stress-suite
outcome: resolved
agent: claude@claude-code
started_at: 2026-10-06T19:24:37Z
finished_at: 2026-10-06T19:24:38Z
---

## Verification

`tests/test_extension_matrix.py` (27 tests) covers: kind, state and availability of each extension; tables born from the generated migrations; three-locale titles; no cross-extension imports (static scan); plugin and connector reacting to model events; injected and failing transports (8 failures, business writes and plugin unaffected); deactivate/reactivate of plugin and connector at runtime; uninstall keeping rows; inbound webhook under `api/` without CSRF, refused once the connector is off; theme swap at runtime and back.

```bash
docker compose exec -T app python -m pytest tests -q                       # 55 passed (SQLite)
CRM_TEST_DB=pgsql ... (disposable PostgreSQL 18 server) pytest tests -q    # 55 passed
```

Not covered: tenant A/B/owner isolation - the demo has no tenant tables, so there is nothing to isolate. Browser check of `/admin/engine` is UNVERIFIED: the demo has no seeded admin and no account was created in its database. The tests found and fixed one bug of their own: `summary.items` in a view resolves to `dict.items`; the views now use `summary["items"]`.
