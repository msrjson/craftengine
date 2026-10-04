---
id: "20261004-161341"
title: Replace the landing's stale v3.12 performance numbers with measured ones
type: chore
priority: 2
autonomous: false
blocked_by: owner-decision
max_attempts: 2
attempts: 0
created_at: 2026-10-04T16:13:41Z
updated_at: 2026-10-04T16:13:41Z
source: evaluation of the boundary/proxy release, 2026-10-04
touches: []
---

## Problem

The landing's "Requests in parallel on a single worker" section shows ~115 req/s (10 clients, before ~27) and p95 0.57 s (before 1.9 s), measured on 2026-08-17 at v3.12.0 on the sample application, which the framework no longer ships (ADR 0001). The p95 pair was measured at 50 clients but the card does not say so. The numbers are hand-typed in `website/site.json` (`metric_throughput`, `metric_latency`).

## Evidence

- `data/CHANGELOG.md` line ~1404 (3.12.0): the original measurement.
- Re-measured 2026-10-04, `tools/loadtest.py` against the `framework` container on :9000, route `/`, 10 s: 1 client 992 req/s; 10 clients 1,389 req/s, p95 10 ms; 50 clients 1,271 req/s, p95 57 ms; 0 failures. Not comparable to the old figure: today's `/` is a fresh project's route.

## Done when

- [ ] Owner chooses the wording (what is measured, with how many clients).
- [ ] A `website/sync_loadtest.py` writes the facts from a real `tools/loadtest.py` run, like `sync_tests.py` and `sync_benchmark.py`.
- [ ] The section names the route, the client count of each figure, and keeps the v3.12 figure only as history.

## Verify

```bash
docker exec framework sh -lc 'cd /app && python tools/loadtest.py http://127.0.0.1:9000/ --clients 1 --clients 10 --clients 50 --seconds 10'
```

## Notes

Site copy is en/pt-BR/es in `website/locales/`; the site repo is pushed separately.

## History

- 2026-10-04T16:13:41Z created by claude (source: evaluation of the boundary/proxy release, 2026-10-04)
