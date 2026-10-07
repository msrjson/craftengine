---
id: "20261004-161340"
title: Benchmark the proxy on PostgreSQL and with several workers
type: chore
priority: 3
autonomous: true
blocked_by: none
max_attempts: 2
attempts: 1
claimed_by: qwen@qwen-code
created_at: 2026-10-04T16:13:40Z
updated_at: 2026-10-07T18:19:40Z
source: evaluation of the boundary/proxy release, 2026-10-04
touches: 
  - data/tests/benchmark_internal_proxy.py
  - data/documentation/internal-proxy.md
  - data/documentation/assets/
---

## Problem

The published benchmark ran on a throwaway SQLite file, one process, loopback network. The ratios are architectural, but nobody has measured the proxy against PostgreSQL or with several uvicorn workers.

## Evidence

- `.claude/reports/20261004-internal-proxy-benchmark.md` - Setup section.
- `tests/benchmark_internal_proxy.py` forces `DB_CONNECTION=sqlite`.

## Done when

- [ ] The benchmark accepts a database choice (an isolated PostgreSQL test database, never a shared one) and a worker count.
- [ ] A PostgreSQL run and a multi-worker run are recorded as reports and, if they change the conclusions, in the guide.

## Verify

```bash
docker exec framework sh -lc 'cd /app && python tests/benchmark_internal_proxy.py --json /tmp/proxy.json'
```

## Notes

Never point the benchmark at a database that holds data (NR-02).

## History

- 2026-10-04T16:13:40Z created by claude (source: evaluation of the boundary/proxy release, 2026-10-04)
- 2026-10-07T18:18:30Z claimed by qwen@qwen-code (attempt 1)
- 2026-10-07T18:18:30Z scope note by qwen@qwen-code: `tests/benchmark_internal_proxy.py` gains `--database {sqlite,pgsql}` (pgsql creates an isolated `craft_*` database, never dropped) and `--workers N` (N>1 serves from N uvicorn worker processes via the new `tests/bench_proxy_app.py`, which registers the routes so workers see them); the guide and a report were added
- 2026-10-07T18:19:40Z resolved by qwen@qwen-code (resolutions/p3-20261004-161340-benchmark-postgres-multiworker.resolution.md): default run reproduces the saturation conclusion (proxy@64 1,316 req/s 0 failures; loopback@64 4 req/s 103 failures); pgsql run proxy@8 1,195 vs loopback@8 0 (8 failures); 2-worker run proxy@8 2,864 vs loopback@8 1,142
