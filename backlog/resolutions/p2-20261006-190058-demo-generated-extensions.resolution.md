---
task: p2-20261006-190058-demo-generated-extensions
outcome: resolved
agent: claude@claude-code
started_at: 2026-10-06T19:24:37Z
finished_at: 2026-10-06T19:24:37Z
---

## Verification

Generated with `docker compose exec -T app python dev.py make module tickets|invoices`, `make plugin activity_digest`, `make theme midnight`, `make connector outbound_webhooks` in `data-demo` (engine v4.6.0-r00026), then installed and activated with `dev.py extension install|activate`: all five `active serving`. Hand-written: only business rules (services, event listeners, two views, one webhook route). Demo commit `ee2d6d3`.

```bash
docker compose exec -T app python -m pytest tests -q   # 55 passed (SQLite)
```
