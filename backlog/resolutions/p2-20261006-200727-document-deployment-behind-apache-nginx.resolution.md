---
task: p2-20261006-200727-document-deployment-behind-apache-nginx
outcome: resolved
agent: qwen@qwen-code (Qwen Code, local Ollama)
started_at: 2026-10-07T08:55:00Z
finished_at: 2026-10-07T09:05:00Z
commits: []
---

## What changed

- `data/documentation/reverse-proxy.md` (new) — how to run the framework behind
  Apache or nginx. Leads with the structural point (an ASGI process that stays
  up, not a script per request), states that `mod_wsgi`/`mod_php`/CGI do not
  apply, lists host requirements (a long-running process, a supervisor or
  container, an internal port) and what that rules out (shared hosting that only
  executes per request). Gives a working Apache `VirtualHost` (`ProxyPreserveHost`,
  `ProxyPass`, `X-Forwarded-Proto`) and the nginx equivalent, then explains the
  two settings that must be right behind a proxy: `TRUSTED_PROXY_HOPS` (read from
  the right, `0` ignores `X-Forwarded-For`; `engine/security/net.py`) and the
  public address (`APP_URL` + preserved `Host`, which `redirect.back()` and the
  CSRF origin check trust; `engine/http/response.py`). Ends with a proxy
  checklist.
- `data/documentation/README.md` — the index links the new page next to
  Deployment.

Language follows the repository rule (no third-party framework named): the PHP
paradigm is described, not a product. The engine defines no WebSocket routes
(`grep websocket engine/` is empty), so the guide says a WebSocket upgrade block
is needed only if the application adds routes.

## Verification

```bash
cd data && grep -rln "reverse proxy" documentation
# documentation/security.md, documentation/reverse-proxy.md, documentation/README.md

docker exec framework sh -lc 'cd /app && python -m pytest tests -q -k "proxy or forwarded"'
# 32 passed, 2010 deselected

python3 .agents/rules/lint_backlog.py   # clean
python3 .agents/rules/lint_board.py     # clean
```

Documentation only; no engine code changed. The `TRUSTED_PROXY_HOPS`, `APP_URL`,
`Host` and health-probe facts were read from `config/app.py:16-20`,
`engine/security/net.py:1-10`, `engine/http/request.py:171-180`,
`engine/http/response.py:136-155` and `documentation/deployment.md`.

## Follow-ups

None.
