---
task: p3-20261004-161340-benchmark-postgres-multiworker
outcome: resolved
agent: qwen@qwen-code (Qwen Code, local Ollama)
started_at: 2026-10-07T18:18:30Z
finished_at: 2026-10-07T18:19:40Z
---

## What changed

- `data/tests/benchmark_internal_proxy.py`: the benchmark is now parameterised.
  `--database {sqlite,pgsql}` picks the database (sqlite stays the default,
  a throwaway file); `--database-name` names the isolated PostgreSQL database,
  which must start with `craft_` and is created if absent and **never dropped**.
  `--workers N` serves from N uvicorn worker processes instead of one in-process
  server. The database kind and worker count are reported in the `environment`
  block of the JSON.
- `data/tests/bench_proxy_app.py` (new): the ASGI app with the bench routes,
  importable as `tests.bench_proxy_app:application` so the multi-worker uvicorn
  processes register the routes themselves (a forked worker never sees the
  parent's in-memory registration — the first cut produced 0 req/s).
- `data/documentation/internal-proxy.md`: "Reproduce it" documents both flags.
- `.agents/reports/20261007-internal-proxy-benchmark-postgres-and-workers.md`
  plus the three raw JSON results.

## Verification

```bash
# the task's Verify, default (sqlite, 1 worker)
docker exec framework sh -lc 'cd /app && python tests/benchmark_internal_proxy.py --json /tmp/proxy.json'
# proxy@64 clients 1,316 req/s, 0 failures; loopback@64 4 req/s, 103 failures

docker exec framework sh -lc 'cd /app && python tests/benchmark_internal_proxy.py --database pgsql --seconds 1 --clients 1 --clients 8 --scale 100'
# proxy@8 1,195 req/s; loopback@8 0 req/s, 8 failures (connections exhausted)

docker exec framework sh -lc 'cd /app && python tests/benchmark_internal_proxy.py --workers 2 --seconds 1 --clients 1 --clients 8 --scale 100'
# proxy@8 2,864 req/s; loopback@8 1,142 req/s
```

Neither axis changes the conclusions: the proxy stays ~2x the loopback pattern
per request, PostgreSQL raises the absolute cost of both, and a second worker
roughly doubles throughput.

## Follow-ups

None. The isolated `craft_proxy_bench` database is left in place by design (the
benchmark never drops data).
