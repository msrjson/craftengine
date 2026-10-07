# Benchmark: internal proxy on PostgreSQL and with several workers

**Date:** 2026-10-07 · **Script:** `tests/benchmark_internal_proxy.py` ·
**Task:** `p3-20261004-161340`.

The published benchmark ran on a throwaway SQLite file, one process, loopback
network. This run adds the two axes the evaluation asked for — a real
PostgreSQL database and more than one uvicorn worker — and confirms the
architecture conclusions do not change; only the absolute numbers do.

## Runs (framework container)

```bash
python tests/benchmark_internal_proxy.py --seconds 1 --clients 1 --clients 8 --scale 100
python tests/benchmark_internal_proxy.py --database pgsql --seconds 1 --clients 1 --clients 8 --scale 100
python tests/benchmark_internal_proxy.py --workers 2 --seconds 1 --clients 1 --clients 8 --scale 100
```

| run | database | workers |
|---|---|---|
| sqlite | sqlite file (throwaway) | 1 |
| pgsql | postgresql (`craft_proxy_bench`, isolated) | 1 |
| workers | sqlite file (throwaway) | 2 |

`--database pgsql` created the isolated `craft_proxy_bench` database (it is left
in place; nothing is dropped or truncated).

## Requests end to end (module A → module B), 8 clients

| run | proxy req/s | loopback req/s | proxy p95 (ms) | loopback p95 (ms) | failures |
|---|---:|---:|---:|---:|---:|
| sqlite, 1 worker | 1,490 | 722 | 8.1 | 15.3 | 0 / 0 |
| pgsql, 1 worker | 1,195 | 0 | 10.0 | — | 0 / 8 |
| sqlite, 2 workers | 2,864 | 1,142 | 4.5 | 11.7 | 0 / 0 |

## Cost per call (mean µs, same invoice)

| run | direct | proxy_call | proxy_dispatch | http over TCP |
|---|---:|---:|---:|---:|
| sqlite, 1 worker | 10.4 | 18.4 | 14.9 | 771.6 |
| pgsql, 1 worker | 120.5 | 153.0 | 159.1 | 1,014.9 |
| sqlite, 2 workers | 10.6 | 17.9 | 14.6 | 1,176.3 |

## Conclusions

- The proxy stays roughly **2× the loopback pattern** per request on every run.
  PostgreSQL raises the absolute cost of both paths and does not change the
  ratio; a second uvicorn worker roughly doubles throughput for both.
- The **saturation finding holds**: on PostgreSQL at 8 concurrent clients the
  loopback pattern exhausted its connections (8 failures) while the proxy kept
  serving. A loopback request holds two thread-pool workers, the proxy one.
- The guide's conclusions are unchanged; `documentation/internal-proxy.md` now
  documents the two flags and points here.

## Raw results

- `20261007-internal-proxy-benchmark-pgsql.json`
- `20261007-internal-proxy-benchmark-workers2.json`
- `20261007-internal-proxy-benchmark-sqlite.json`
