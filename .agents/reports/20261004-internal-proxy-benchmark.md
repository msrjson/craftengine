# Internal proxy benchmark - 2026-10-04

**Command:** `docker exec framework sh -lc 'cd /app && python tests/benchmark_internal_proxy.py --json /tmp/proxy-benchmark.json'`
**Raw results:** `20261004-internal-proxy-benchmark.json` (same directory).
**Code:** `data/tests/benchmark_internal_proxy.py` at the commit that adds this report.

## Setup

- The real Craft kernel served by uvicorn 0.53.0 on a loopback TCP port, one
  process, inside the `framework` container (Python 3.14.7, x86_64, 8 CPUs).
- Thread pool for synchronous actions: 40 workers (anyio default).
- Database: a throwaway SQLite file. Module B (`BillingService.generate_invoice`)
  runs one `SELECT 1` and returns a small dict, so every path below includes one
  real database round trip.
- Clients use keep-alive connections, and so does module A's loopback call, so
  the HTTP numbers are not inflated by connection setup.

## 1. Cost per call - the same invoice, five paths

| Path | Calls/s | Mean (us) | p50 (us) | p95 (us) | p99 (us) | x direct |
|---|---:|---:|---:|---:|---:|---:|
| Direct method call | 105,926 | 9.2 | 8.1 | 14.5 | 20.3 | 1.0 |
| `Proxy.call` | 61,201 | 16.1 | 14.8 | 25.7 | 30.9 | 1.7 |
| `Proxy.dispatch` | 82,585 | 11.9 | 11.7 | 12.3 | 19.2 | 1.3 |
| Kernel in process (ASGI, no socket) | 502 | 1,990.5 | 1,878.8 | 2,473.2 | 3,234.5 | 215.4 |
| HTTP over TCP (keep-alive) | 1,224 | 816.6 | 767.4 | 1,197.9 | 1,543.0 | 88.4 |

The proxy adds a few microseconds over a direct call (container lookup and
allowlist check). Reaching the same method over HTTP costs about 50 to 70 times
more than through the proxy. The gap between `call` and `dispatch` is
measurement order and noise, not a property of either path: both run the
target inline on the caller's thread.

## 2. Requests end to end - module A needs module B

An external request reaches module A through the full kernel; module A then
reaches module B either through the proxy or through a loopback HTTP request.
Five seconds per scenario. Latency in milliseconds.

| Route | Clients | Req/s | p50 | p95 | p99 | Failures |
|---|---:|---:|---:|---:|---:|---:|
| proxy | 1 | 1,308 | 0.74 | 0.93 | 1.30 | 0 |
| loopback | 1 | 663 | 1.44 | 1.88 | 2.62 | 0 |
| proxy | 8 | 1,395 | 5.48 | 8.89 | 11.40 | 0 |
| loopback | 8 | 746 | 10.31 | 15.36 | 19.08 | 1 |
| proxy | 32 | 1,513 | 20.08 | 29.11 | 37.61 | 0 |
| loopback | 32 | 740 | 41.81 | 56.15 | 66.42 | 15 |
| proxy | 64 | 1,426 | 43.23 | 58.36 | 71.83 | 0 |
| loopback | 64 | 8 | 73.55 | 9,983.39 | 10,002.64 | 89 |

## 3. Reading

- **Throughput:** the proxy serves about 2x the requests per second of the
  loopback pattern at every concurrency level up to 32, at half the latency.
- **Saturation:** a loopback request holds two thread-pool workers - its own and
  the inner request's. With 40 workers, 32 clients already start failing, and at
  64 clients the pool deadlocks: every worker waits on an inner request that
  needs a worker. Throughput collapses from 740 to 8 req/s and p95 hits the
  10-second client timeout. The proxy holds one worker per request and keeps
  serving about 1,400 req/s with zero failures.
- **Scope:** one process, SQLite, loopback network. Absolute numbers change with
  hardware, database and worker count; the ratios and the saturation shape are
  what the architecture decides.
