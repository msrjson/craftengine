# Performance Checklist

Quick reference for Craft web application performance: Forge server-rendered pages, vanilla JS and CSS served from `public/`, the ASGI request path, Craft ORM and PostgreSQL. Use it alongside the `performance-optimization` skill (`.claude/skills/performance-optimization/SKILL.md`).

## Table of Contents

- [Core Web Vitals Targets](#core-web-vitals-targets)
- [TTFB Diagnosis](#ttfb-diagnosis)
- [Frontend Checklist](#frontend-checklist)
- [Backend Checklist](#backend-checklist)
- [Caching Strategies](#caching-strategies)
- [Measurement Commands](#measurement-commands)
- [Common Anti-Patterns](#common-anti-patterns)

## Core Web Vitals Targets

| Metric | Good | Needs Work | Poor |
|--------|------|------------|------|
| LCP (Largest Contentful Paint) | <= 2.5s | <= 4.0s | > 4.0s |
| INP (Interaction to Next Paint) | <= 200ms | <= 500ms | > 500ms |
| CLS (Cumulative Layout Shift) | <= 0.1 | <= 0.25 | > 0.25 |

## TTFB Diagnosis

When TTFB is slow (> 800ms), check each component in the DevTools Network waterfall:

- [ ] **DNS resolution** slow -> add `<link rel="dns-prefetch">` or `<link rel="preconnect">` for known third-party origins
- [ ] **TCP/TLS handshake** slow -> HTTP/2 at the reverse proxy, keep-alive enabled, deployment closer to users
- [ ] **Server processing** slow -> read `craft_request_duration_seconds` for the route at `/metrics`, count queries, check caching
- [ ] **Waiting on a worker** -> requests queued behind a saturated thread pool or database pool (`craft_db_pool_connections`, `/ready`)

## Frontend Checklist

### Images
- [ ] Images use modern formats (WebP, AVIF)
- [ ] Images are responsively sized (`srcset` and `sizes`)
- [ ] `<img>` and `<source>` elements carry explicit `width` and `height` (prevents CLS, including with art direction)
- [ ] Below-the-fold images use `loading="lazy"` and `decoding="async"`
- [ ] Hero/LCP images use `fetchpriority="high"` and are never lazy loaded
- [ ] Variants are generated once (at upload or in a queued job), not resized per request
- [ ] `alt` text is a translation key (`{{ __('...') }}`), never literal copy

### JavaScript
- [ ] No Node build pipeline, no TypeScript, no npm: scripts are vanilla or vendored minified files under `public/`
- [ ] Page-specific scripts are included only by the templates that use them, not by the global layout
- [ ] Every script uses `defer` or `type="module"`; nothing blocking in `<head>`
- [ ] Heavy, rarely used features (charts, rich editors) load on demand with a native dynamic `import()` of a vendored module
- [ ] Total JavaScript per page reviewed; vendored libraries checked for size before commit
- [ ] Heavy computation offloaded to a Web Worker (if applicable)
- [ ] Long tasks (> 50ms) broken up so the main thread stays available: the main lever for INP
- [ ] A `yieldToMain` helper used inside long-running loops so input events run between chunks
- [ ] Modern scheduling APIs used where available: `scheduler.yield()` (preferred), `scheduler.postTask()` with priorities
- [ ] `requestIdleCallback` for deferrable work (analytics flush, prefetch, warmup)
- [ ] Non-critical work (analytics, logging beacons) deferred out of event handlers so the visual response is not delayed
- [ ] One delegated listener on a container instead of one listener per row
- [ ] `scroll` / `resize` / `touchmove` listeners are `{ passive: true }` and throttled
- [ ] Third-party scripts loaded `async` / `defer`, audited for size, and fronted by a facade when heavy (chat widgets, video embeds)

### CSS
- [ ] Critical above-the-fold CSS inlined in the layout or preloaded
- [ ] No render-blocking stylesheet for non-critical styles (load it with `media` switching or after first paint)
- [ ] No runtime style generation in JavaScript for what a static class can express
- [ ] Unused rules pruned from shared stylesheets during review

### Fonts
- [ ] Limited to 2-3 families with 2-3 weights each (every weight is another request)
- [ ] WOFF2 only
- [ ] Self-hosted under `public/` when possible (third-party font hosts add DNS + TCP + TLS round trips)
- [ ] LCP-critical fonts preloaded: `<link rel="preload" as="font" type="font/woff2" crossorigin>`
- [ ] `font-display: swap` (or `optional` for non-critical faces)
- [ ] Subset with `unicode-range`; Portuguese and Spanish need Latin-1 Supplement and Latin Extended-A glyphs, so check accents before trimming
- [ ] Variable fonts considered when several weights are required
- [ ] Fallback metrics tuned with `size-adjust`, `ascent-override`, `descent-override` to reduce CLS on swap
- [ ] System font stack considered before any custom font

### Network
- [ ] Every static asset referenced through Forge `asset()`, which appends `?ver=<APP_VERSION>` so a release changes the URL
- [ ] Reverse proxy or CDN serves `/assets/` with a long `max-age` and `immutable` (safe only because `asset()` versions the URL)
- [ ] HTML responses short-lived or `no-cache`; per-user pages never publicly cacheable
- [ ] Text responses compressed (gzip or brotli) at the reverse proxy; the application does not compress for you
- [ ] API responses cached where appropriate (`Cache-Control`), keyed correctly
- [ ] HTTP/2 or HTTP/3 enabled at the edge
- [ ] Known cross-origin resources preconnected (`<link rel="preconnect">`)
- [ ] `fetchpriority` used on critical non-image resources (key `<link rel="preload">`, above-the-fold script), not only on `<img>`
- [ ] No unnecessary redirects (trailing slash, http -> https chains, locale redirects that could be resolved in place)

### Rendering
- [ ] No layout thrashing (reading layout properties between DOM writes)
- [ ] DOM built in a `DocumentFragment` or `<template>` clone and inserted once, not row by row
- [ ] Animations use `transform` and `opacity` only
- [ ] Very long lists are paginated server-side rather than rendered in full and hidden
- [ ] Off-screen sections use `content-visibility: auto` with `contain-intrinsic-size`
- [ ] No `unload` handlers and no `Cache-Control: no-store` on HTML that does not need it, to keep back/forward cache eligibility

## Backend Checklist

### Database
- [ ] No N+1 patterns: every list that touches a relation is loaded with `Model.with_("relation", ...)`
- [ ] Queries have indexes that match their shape
- [ ] List routes use `paginate(per_page=..., page=...)` (clamped to 100) or an explicit `limit()`; never an unbounded `get()` on a growing table
- [ ] Deep pages on large tables use keyset pagination (`where("id", "<", last_id)`) instead of large `OFFSET`
- [ ] Only needed columns selected on hot paths (`select("id", "title")`)
- [ ] Queries live in repositories; zero SQL in controllers or services
- [ ] Slow query logging enabled in PostgreSQL (`log_min_duration_statement`) or `pg_stat_statements` installed

#### Query plans
- [ ] `EXPLAIN ANALYZE` captured **before** the fix: it is the baseline
- [ ] `Seq Scan` on a large table understood: index missing, unusable, or genuinely not worth it
- [ ] Estimated vs actual `rows=` within an order of magnitude (if not, `ANALYZE` the table before touching indexes)
- [ ] No `Sort` node that a composite index could absorb
- [ ] Plan re-checked after the change; an index that did not change the plan is removed

#### Index strategy
- [ ] Composite index column order is equality first, then range or sort
- [ ] Index covers the query shape (filter + sort), not one column in isolation
- [ ] Covering index (`INCLUDE`) considered for hot read paths (index-only scan skips the heap fetch)
- [ ] No index on a low-selectivity column for its dominant value; a partial index still serves the rare value (`WHERE status = 'failed'`)
- [ ] Expression index where the query applies a function (`lower(email)`)
- [ ] `pg_trgm` or full-text index for leading-wildcard search, not a B-tree
- [ ] Tenant-scoped tables index `tenant_id` first when every query filters on it
- [ ] Write cost measured on write-heavy tables
- [ ] Unused and duplicate indexes removed (checked in `pg_stat_user_indexes`)
- [ ] Every index change is a forward-only migration named `idx_<table>_<columns>`; large tables use `CREATE INDEX CONCURRENTLY`

#### Connection pooling
- [ ] One bounded pool per connection per process (Craft's default); nothing opens ad hoc connections per request
- [ ] `DB_POOL_SIZE x (web processes + queue workers + scheduler)` stays under PostgreSQL `max_connections`, with headroom
- [ ] `DB_POOL_TIMEOUT` set so exhaustion fails fast instead of queueing forever
- [ ] `framework.HTTP_THREADPOOL_SIZE` left at its default (`pool_size x 2`, at least 8) unless measured otherwise
- [ ] Exhaustion diagnosed before resizing: long transactions, external calls inside `DB.transaction`, locks held across slow work (`python dev.py db:locks`)
- [ ] Autoscaling fronted by a multiplexing proxy (pgbouncer) rather than a larger pool

### Request path
- [ ] Route p95 under 200ms (`craft_request_duration_seconds`)
- [ ] No synchronous heavy computation in controllers; controllers stay thin (15 lines per action)
- [ ] Slow side work (mail, PDF, image variants, third-party calls) dispatched with `Queue.push(job)` and run by `python dev.py queue:work`
- [ ] Production `QUEUE_CONNECTION` is `database` or `redis`, not `sync` (which runs jobs inline)
- [ ] Jobs carry ids and scalars only (payloads serialize to JSON)
- [ ] Bulk inserts and updates instead of a query per item in a loop
- [ ] Outbound HTTP calls have timeouts
- [ ] Appropriate caching (memory, file, Redis, reverse proxy)

### Infrastructure
- [ ] Reverse proxy or CDN in front of the application for static assets, TLS and compression
- [ ] Deployment region close to users
- [ ] Horizontal scaling sized against the database connection ceiling
- [ ] Load balancer uses `/health` for liveness and `/ready` for readiness (readiness includes database and cache checks)
- [ ] `/metrics` scraped and alerted on

## Caching Strategies

The decision material (which layer, which invalidation strategy, what never to cache) lives in the `performance-optimization` skill. This section covers read/write patterns and the checklist.

Craft facts to design around:

- `Cache` facade (`from craft.facades import Cache`): `get`, `put`, `add`, `has`, `forget`, `remember(key, ttl_seconds, callback)`, `remember_forever`, `pull`, `increment`, `decrement`, `flush`.
- Stores chosen by `CACHE_DRIVER`: `memory` (per process, used in tests), `file` (one host), `redis` (shared). An unreachable Redis falls back to memory with a logged warning.
- `add()` is atomic put-if-absent on every store: the primitive for locks and once-only work.
- `remember()` stores a sentinel for `None`, so a cached "nothing" is distinguishable from a miss.
- File and Redis stores serialize to JSON: cache plain data, not models.

### Read and write patterns

| Pattern | How it works | Use when | Watch out for |
|---|---|---|---|
| **Cache-aside** (lazy, `Cache.remember`) | Service checks cache; on miss reads the repository and stores the result | Default choice; read-heavy, tolerant of a cold first hit | Every miss hits PostgreSQL, so hot keys need stampede protection |
| **Read-through** | A dedicated cached repository loads on miss | You want the load path in one place, not at every call site | Hides origin latency; a slow query looks like a slow cache |
| **Write-through** | Writer updates the database and the cache in the same operation | Reads must never see a stale value after a write | Adds cache latency to every write; decide what happens when the cache write fails |
| **Write-behind** | Write hits the cache; a queued job persists later | Write-heavy counters where the database is the bottleneck | Data-loss window if the cache dies before the flush. Never for business records, which need durable writes |

### Negative caching

Cache the *absence* of a result too. A key that misses on every lookup (a nonexistent slug probed in a loop, a missing asset) sends every request to the database, which is a cache that only protects the happy path.

- Store an explicit "not found" marker with a **shorter** TTL than positive entries (`remember` already distinguishes a cached `None`)
- Keep the negative TTL short enough that a newly created record appears promptly
- Never let a database *error* become a negative entry, or one failing minute becomes many

### Request coalescing (stampede protection)

One recompute, N waiters. Prevents a hot key's expiry from delivering the full concurrent load to PostgreSQL. With a shared store, `Cache.add` is the lock:

```python
import time
from collections.abc import Callable

from craft.facades import Cache

LOCK_TTL_SECONDS = 30
WAIT_STEP_SECONDS = 0.05


def load_once(key: str, ttl_seconds: int, loader: Callable[[], object]) -> object:
    """Return a cached value, letting a single caller recompute it on a miss.

    Args:
        key: Full cache key, already including tenant and locale.
        ttl_seconds: Lifetime of the fresh value.
        loader: Callable that produces the value from the repository.

    Returns:
        The cached or freshly loaded value.
    """
    cached = Cache.get(key)
    if cached is not None:
        return cached
    if not Cache.add(f"{key}:lock", 1, LOCK_TTL_SECONDS):
        return _wait_for_value(key, loader)
    try:
        value = loader()
        Cache.put(key, value, ttl_seconds)
        return value
    finally:
        Cache.forget(f"{key}:lock")


def _wait_for_value(key: str, loader: Callable[[], object], attempts: int = 20) -> object:
    """Poll briefly for the winner's value, then load directly as a last resort."""
    for _ in range(attempts):
        time.sleep(WAIT_STEP_SECONDS)
        cached = Cache.get(key)
        if cached is not None:
            return cached
    return loader()
```

Alternatives: keep serving the previous value while one caller refreshes (store the value with a "soft expiry" timestamp and a longer hard TTL), or refresh hot keys ahead of expiry from a scheduled task (`python dev.py schedule:work`).

### Cache checklist
- [ ] The cached call was measured as expensive first
- [ ] Read/write ratio justifies the cache (re-read far more often than written)
- [ ] Key includes every input the result varies on: tenant, viewer, locale, permissions, feature flags
- [ ] No per-user or personal data cached under a key that does not identify the user; personal data in cache has a TTL consistent with the privacy policy
- [ ] One invalidation strategy chosen (TTL, event listener calling `Cache.forget`, or versioned keys), not an accidental mix
- [ ] Acceptable staleness window written down next to the TTL constant
- [ ] Stampede protection on hot keys (`Cache.add` lock, soft expiry, or scheduled refresh)
- [ ] Negative results cached with a shorter TTL; database errors never cached
- [ ] Memory ceiling and eviction policy set on the Redis instance (an unbounded cache is a memory leak); in-process caches bounded
- [ ] The Redis-unavailable fallback warning is alerted on, since it silently makes the cache per process
- [ ] Hit rate monitored; a low hit rate is pure overhead
- [ ] Nothing cached whose staleness is a correctness bug (balances, permissions, stock at checkout)

## Measurement Commands

### INP field data and DevTools workflow

1. **Field data first**: check CrUX (PageSpeed Insights shows it per URL and origin) or your own RUM beacons before optimizing
2. **Identify slow interactions**: DevTools -> Performance panel -> record while interacting; look for long tasks triggered by clicks and keystrokes
3. **Test on mid-range hardware**: INP problems often appear only on slower devices; use a real device or DevTools CPU throttling (4x-6x)

```text
# Lab: Lighthouse
Chrome DevTools -> Lighthouse panel -> Mode: Navigation, Device: Mobile -> Analyze page load
PageSpeed Insights (public URLs) -> lab Lighthouse plus CrUX field data in one report

# Static weight per page
Chrome DevTools -> Network panel -> filter JS / CSS / Img / Font -> read "transferred" vs "resources"
Chrome DevTools -> Coverage panel -> unused bytes per CSS and JS file
```

```bash
# Application side
python dev.py serve                                   # start the app locally
python dev.py route:list                              # confirm which route handles the slow URL
curl -s http://localhost:9000/metrics | grep craft_request_duration_seconds
curl -s http://localhost:9000/ready                   # database and cache checks, pool census
python dev.py db:locks                                # current lock holders and waiters
python -m cProfile -o profile.out scripts/reproduce_slow_report.py
python -m pstats profile.out                          # then: sort cumulative / stats 30

# Database side (psql)
EXPLAIN (ANALYZE, BUFFERS) SELECT ...;
SELECT query, calls, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 20;
SELECT relname, indexrelname, idx_scan FROM pg_stat_user_indexes ORDER BY idx_scan ASC;
```

The local port follows the project's `serve` configuration; adjust the URL if it differs. `/metrics` may require a bearer token when one is configured.

Field measurement in vanilla JS, including INP attribution, uses `PerformanceObserver` with the `event` entry type:

```javascript
new PerformanceObserver((list) => {
  for (const entry of list.getEntries()) {
    if (!entry.interactionId) continue;
    const inputDelay = entry.processingStart - entry.startTime;
    const processing = entry.processingEnd - entry.processingStart;
    const presentation = entry.startTime + entry.duration - entry.processingEnd;
    navigator.sendBeacon("/api/v1/vitals", JSON.stringify({
      name: "interaction",
      duration: entry.duration,
      target: entry.target ? entry.target.tagName : null,
      inputDelay: inputDelay,
      processing: processing,
      presentation: presentation,
    }));
  }
}).observe({ type: "event", durationThreshold: 40, buffered: true });
```

Send aggregate numbers only; no personal data leaves the page without a lawful basis.

## Common Anti-Patterns

| Anti-Pattern | Impact | Fix |
|---|---|---|
| N+1 queries (relation accessed in a loop) | Query count grows linearly with rows | `Model.with_("relation")`, pinned by a query-count test |
| Unbounded queries | Memory exhaustion, timeouts | `paginate()` or `limit()`; keyset pagination on large tables |
| Missing indexes | Reads slow down as data grows | Index filtered and sorted columns in the query's shape |
| Indexing without reading the plan | Write cost paid, read gain unproven | `EXPLAIN ANALYZE` before and after; remove if the plan is unchanged |
| Redundant or unused indexes | Every write pays for them | Audit `pg_stat_user_indexes`, drop in a forward migration |
| Raising the pool on exhaustion | Queue moves into PostgreSQL | Find what holds connections; pgbouncer for autoscaling |
| Slow work inside the request | High p95, held connections | Queued job; confirm the queue driver is not `sync` |
| Cache key missing tenant or viewer | One user's data served to another | Key on tenant, viewer, locale, permissions |
| Unbounded cache | Memory leak disguised as optimization | TTLs, Redis `maxmemory` and eviction policy |
| Cache stampede on a hot key | Database takes full concurrent load at expiry | `Cache.add` lock, soft expiry or scheduled refresh |
| Assets referenced by literal path | Stale files after a release, or no long caching at all | Always `asset()`; long `immutable` caching at the proxy |
| Layout thrashing | Jank, dropped frames | Batch DOM reads, then batch writes |
| Unoptimized images | Slow LCP, wasted bandwidth | WebP/AVIF, responsive sizes, lazy loading below the fold |
| Global layout loading every page's scripts | Slow load and parse on every page | Include scripts per template; dynamic `import()` for heavy features |
| Blocking main thread | Poor INP | Chunk long tasks with `scheduler.yield()` / `yieldToMain`, Web Workers |
| Memory leaks in page scripts | Growing memory, eventual crash | Remove listeners and intervals; use `AbortController` to detach listener groups |
