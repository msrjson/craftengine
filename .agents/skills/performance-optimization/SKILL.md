---
name: performance-optimization
description: Measures and improves Craft application performance across Forge pages, static assets, request handling, ORM queries and PostgreSQL. Use when performance requirements exist, when a regression is suspected, when Core Web Vitals or response times need improvement, when N+1 query patterns need fixing, or when profiling reveals a bottleneck.
---

# Performance Optimization

## Overview

Measure first, then optimize. Performance work without a measurement is a guess, and guesses turn into premature optimization: complexity added in the name of speed that does not move the number users feel. Profile, find the real bottleneck, fix that one thing, measure again. Keep only what the measurement proves.

## When to Use

- The spec states a performance requirement (page load budget, response time SLA, p95 target)
- Users or monitoring report slowness
- Core Web Vitals are outside the "Good" thresholds
- A change is suspected of introducing a regression
- A feature handles large datasets, long lists or high traffic

**When NOT to use:** before there is evidence of a problem. Premature optimization costs more in maintenance than it returns in speed.

## Core Web Vitals Targets

| Metric | Good | Needs Improvement | Poor |
|--------|------|-------------------|------|
| **LCP** (Largest Contentful Paint) | <= 2.5s | <= 4.0s | > 4.0s |
| **INP** (Interaction to Next Paint) | <= 200ms | <= 500ms | > 500ms |
| **CLS** (Cumulative Layout Shift) | <= 0.1 | <= 0.25 | > 0.25 |

## The Optimization Workflow

```
1. MEASURE  -> Establish a baseline with real data
2. IDENTIFY -> Find the actual bottleneck (not the assumed one)
3. FIX      -> Address that specific bottleneck
4. VERIFY   -> Measure again; keep or revert
5. GUARD    -> Add monitoring or tests so it cannot silently regress
```

### Step 1: Measure

Two complementary sources. Use both.

- **Synthetic (Lighthouse, Chrome DevTools Performance panel):** controlled and reproducible. Best for regression detection before merge and for isolating one issue.
- **Field / RUM (real user measurement, CrUX):** real devices on real networks. Required to confirm a fix improved what users actually experience.

**Frontend (Forge pages, vanilla JS):**

```text
# Synthetic
Chrome DevTools -> Lighthouse panel -> Analyze page load
Chrome DevTools -> Performance panel -> Record (with CPU and network throttling)
Browser automation through the chrome-devtools MCP server -> performance trace
  (see .claude/skills/browser-testing-with-devtools/SKILL.md)
```

Field data needs no dependency: the browser exposes the underlying entries through `PerformanceObserver`. Ship it as a static file under `public/`, loaded with `defer`; if you prefer a library, vendor its ES module build into `public/assets/js/vendor/` rather than installing a package.

```javascript
// public/assets/js/vitals.js - minimal field measurement, no build step.
(function observeVitals() {
  "use strict";

  const report = (name, value) => {
    const body = JSON.stringify({ name: name, value: value, path: location.pathname });
    navigator.sendBeacon("/api/v1/vitals", body);
  };

  new PerformanceObserver((list) => {
    const entries = list.getEntries();
    report("LCP", entries[entries.length - 1].startTime);
  }).observe({ type: "largest-contentful-paint", buffered: true });

  let cumulativeShift = 0;
  new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      if (!entry.hadRecentInput) cumulativeShift += entry.value;
    }
  }).observe({ type: "layout-shift", buffered: true });

  addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") report("CLS", cumulativeShift);
  });
})();
```

The collection endpoint is a normal API route; it stores numbers and a route pattern, never personal data (no IP, no user id without a lawful basis and a retention window).

**Backend (Craft request path):**

Craft already measures every request. `RequestContext` middleware records the `craft_request_duration_seconds` histogram and the `craft_requests_total` counter per method and **route pattern**, and `craft_db_pool_connections` reports pool occupancy. They are exposed at `/metrics` (path configurable through `framework.METRICS_PATH`). Read p95 from that histogram before touching code.

For a single suspect code path, time it with the standard library and log structured, English fields:

```python
import logging
import time

logger = logging.getLogger("app.performance")


def timed_report_build(repository: ReportRepository, tenant_id: str) -> Report:
    """Build the monthly report and log how long the query phase took.

    Args:
        repository: Repository that owns the report queries.
        tenant_id: Tenant whose report is built.

    Returns:
        The assembled report.
    """
    started = time.perf_counter()
    report = repository.monthly_summary(tenant_id)
    logger.info(
        "report_query_timed",
        extra={"tenant_id": tenant_id, "elapsed_ms": round((time.perf_counter() - started) * 1000, 1)},
    )
    return report
```

To count queries, wrap `DB.statement` in a test the way the framework's own eager-loading tests do (see "Guard" below). For CPU hotspots use `python -m cProfile -o profile.out` on a reproduction script, or a sampling profiler attached to the running process.

### Where to Start Measuring

Let the symptom choose the first measurement:

```
What is slow?
|-- First page load
|   |-- Too much JS/CSS shipped? --> Measure transferred size per file in the Network panel
|   |-- Slow server response? --> Measure TTFB in the DevTools Network waterfall
|   |   |-- DNS long? --> dns-prefetch / preconnect for known third-party origins
|   |   |-- TCP/TLS long? --> HTTP/2 at the reverse proxy, keep-alive, closer edge
|   |   `-- Waiting (server) long? --> craft_request_duration_seconds for the route, then queries and caching
|   `-- Render-blocking resources? --> Look for CSS/JS in <head> without defer
|-- Interaction feels sluggish
|   |-- UI freezes on click? --> Performance panel, long tasks (> 50ms) on the main thread
|   |-- Form input lag? --> Handlers doing work on every keystroke; debounce, move work off input
|   `-- Animation jank? --> Layout thrashing, forced reflows, non-compositor properties
|-- Page after navigation
|   |-- Data loading? --> Response times of the fetch calls, sequential waterfalls
|   `-- DOM building? --> Large innerHTML rebuilds, per-row fetches from vanilla JS
`-- Backend / API
    |-- One route slow? --> Query count and EXPLAIN ANALYZE for that route
    |-- Every route slow? --> craft_db_pool_connections, thread pool, memory, CPU
    `-- Intermittent? --> Lock contention (python dev.py db:locks), GC pauses, external calls
```

### Step 2: Identify the Bottleneck

**Frontend:**

| Symptom | Likely Cause | Investigation |
|---------|-------------|---------------|
| Slow LCP | Oversized hero image, render-blocking CSS/JS, slow TTFB | Network waterfall, image bytes, TTFB |
| High CLS | Images without dimensions, late-injected content, font swap | Layout shift attribution in the Performance panel |
| Poor INP | Heavy synchronous JS in event handlers, large DOM rewrites | Long tasks in a Performance trace |
| Slow initial load | Too many or too large static files, third-party scripts | Network panel, transferred size, request count |

**Backend:**

| Symptom | Likely Cause | Investigation |
|---------|-------------|---------------|
| Slow responses on one route | N+1 queries, missing index, unbounded query | Query count in a test, `EXPLAIN ANALYZE` |
| Memory growth | Unbounded in-process cache, whole tables loaded into a Collection | `tracemalloc` snapshots compared over time |
| CPU spikes | Heavy computation inside the request, regex backtracking | `cProfile` or a sampling profiler |
| High latency everywhere | Pool exhaustion, missing caching, synchronous external calls | Pool gauge, request traces, logs with request id |

### Step 3: Fix Common Anti-Patterns

#### N+1 Queries (Backend)

Craft ORM relations load lazily. Iterating a list and touching a relation issues one query per row. `with_()` resolves each named relation for the whole batch in one extra query (`has_many`, `has_one`, `belongs_to` and `belongs_to_many` all support it). Queries live in a repository, never in a controller or service.

```python
from craft.support.collection import Collection

from app.Models.post import Post


class PostRepository:
    """Read access for posts."""

    def recent_with_authors_slow(self) -> Collection:
        """BAD: one query for posts, then one per post for its author."""
        posts = Post.query().latest().get()
        for post in posts:
            post.author().first()  # a query per iteration
        return posts

    def recent_with_authors(self) -> Collection:
        """GOOD: two queries total, whatever the number of posts.

        Returns:
            Posts with the `author` relation already loaded.
        """
        return Post.with_("author").latest().get()
```

Several relations load together: `Post.with_("author", "comments")`. A misspelled relation raises `RelationNotFoundError` instead of silently falling back to lazy loading.

#### Unbounded Data Fetching

```python
class PostRepository:
    """Read access for posts."""

    def all_posts(self) -> Collection:
        """BAD: loads the entire table into memory on every request."""
        return Post.query().get()

    def page_of_posts(self, page: int) -> Collection:
        """GOOD: one bounded page, newest first.

        Args:
            page: One-based page number from the request.

        Returns:
            A Collection whose `pagination` holds total, per_page,
            current_page and last_page.
        """
        return Post.with_("author").latest().paginate(per_page=20, page=page)
```

`paginate()` clamps `per_page` to `QueryBuilder.MAX_PER_PAGE` (100), so a client cannot request an arbitrarily large page. Note that it runs a `COUNT` first; on very large tables where the total is not needed, a keyset query (`where("id", "<", last_seen_id).order_by("id", "desc").limit(20)`) avoids both the count and deep `OFFSET` scans. Batch jobs that must visit every row walk keysets in fixed-size pages rather than loading everything.

#### Queries That Ignore Their Index

"Add an index" is the guess. The query plan is the measurement:

```sql
EXPLAIN ANALYZE
SELECT id, title FROM posts
WHERE author_id = 42 ORDER BY created_at DESC LIMIT 20;
```

Three things in the output decide the fix:

| What you see | What it means |
|---|---|
| `Seq Scan` on a large table where an index was expected | No usable index for this predicate |
| Estimated `rows=` off from actual by an order of magnitude | Stale statistics; run `ANALYZE` before touching indexes |
| A `Sort` node above the scan | The index covers the filter but not the `ORDER BY` |

Index the **shape of the query**, not one column in isolation. In a composite index, equality columns come first, then the range or sort column. Add it through a forward-only migration (`python dev.py make:migration`), named per the standard:

```sql
CREATE INDEX idx_posts_author_id_created_at ON posts (author_id, created_at DESC);
```

On a large production table use `CREATE INDEX CONCURRENTLY` so writes are not blocked while it builds.

**When an index will not help:**

| Situation | Why |
|---|---|
| Low selectivity on the dominant value (a `status` that is 95% `active`, filtered on `active`) | A sequential scan is genuinely cheaper and the planner ignores the index. Filtering on the rare value is the opposite case, and a partial index (`WHERE status = 'failed'`) serves it well |
| Leading wildcard (`LIKE '%term'`) | A B-tree cannot seek without a prefix; use `pg_trgm` or full-text search |
| Function on the column (`WHERE lower(email) = ?`) | The plain column index is unusable; create an expression index |
| Write-heavy table | Every index taxes every `INSERT` and `UPDATE`; measure the write cost, not only the read gain |

Run `EXPLAIN ANALYZE` again afterwards. An index that did not change the plan is a revert (Step 4): it still costs on every write. Removing it is also a forward migration, never a rollback in production.

#### Connection Pool Exhaustion

The signature is distinctive: **every** route slows at once, the time is spent waiting for a connection rather than executing SQL, and PostgreSQL reports mostly idle sessions.

Craft keeps one bounded pool per connection per process. The relevant settings live in `config/database.py`:

```python
# config/database.py (excerpt)
"pool_size": env("DB_POOL_SIZE", 4),       # physical connections per process
"pool_timeout": env("DB_POOL_TIMEOUT", 10),  # seconds a request waits, then fails fast
```

The HTTP worker thread pool defaults to `pool_size x 2` (at least 8) unless `framework.HTTP_THREADPOOL_SIZE` is set, so requests beyond capacity are turned away quickly instead of queueing on a connection timeout. When all connections are busy, the pool raises after `pool_timeout` with a message naming the setting.

Rules that follow from that design:

- `processes x pool_size` (web workers plus queue workers plus scheduler) must stay under PostgreSQL `max_connections`, with headroom for migrations and admin sessions.
- Watch `craft_db_pool_connections` and the `/ready` probe, which reports `pool_open`, `pool_idle` and `pool_size`.
- **Bigger is not faster.** A pool larger than what the database can execute concurrently moves the queue from the application into PostgreSQL, where it is harder to see. First find what holds connections: long transactions, external HTTP calls made inside `DB.transaction`, advisory locks held across a slow operation.
- When the number of processes is unbounded (autoscaling), put a multiplexing proxy such as pgbouncer in front of PostgreSQL rather than raising `DB_POOL_SIZE`.

#### Missing Image Optimization (Frontend)

Forge templates emit the markup; alt text is a translation key, never a literal.

```html
{# BAD: no dimensions, no modern format, no priority hint #}
<img src="/assets/img/hero.jpg">

{# GOOD: hero / LCP image - art direction plus resolution switching, high priority #}
<picture>
  {# Mobile: portrait crop (8:10) #}
  <source media="(max-width: 767px)"
          srcset="{{ asset('/assets/img/hero-mobile-400.avif') }} 400w, {{ asset('/assets/img/hero-mobile-800.avif') }} 800w"
          sizes="100vw" width="800" height="1000" type="image/avif">
  <source media="(max-width: 767px)"
          srcset="{{ asset('/assets/img/hero-mobile-400.webp') }} 400w, {{ asset('/assets/img/hero-mobile-800.webp') }} 800w"
          sizes="100vw" width="800" height="1000" type="image/webp">
  {# Desktop: landscape crop (2:1) #}
  <source srcset="{{ asset('/assets/img/hero-800.avif') }} 800w, {{ asset('/assets/img/hero-1200.avif') }} 1200w, {{ asset('/assets/img/hero-1600.avif') }} 1600w"
          sizes="(max-width: 1200px) 100vw, 1200px" width="1200" height="600" type="image/avif">
  <source srcset="{{ asset('/assets/img/hero-800.webp') }} 800w, {{ asset('/assets/img/hero-1200.webp') }} 1200w, {{ asset('/assets/img/hero-1600.webp') }} 1600w"
          sizes="(max-width: 1200px) 100vw, 1200px" width="1200" height="600" type="image/webp">
  <img src="{{ asset('/assets/img/hero-desktop.jpg') }}" width="1200" height="600"
       fetchpriority="high" alt="{{ __('home.hero.image_alt') }}">
</picture>

{# GOOD: below-the-fold image - lazy loaded, async decoding #}
<img src="{{ asset('/assets/img/content.webp') }}" width="800" height="400"
     loading="lazy" decoding="async" alt="{{ __('home.feature.image_alt') }}">
```

Each new key (`home.hero.image_alt`, `home.feature.image_alt`) ships with `en`, `pt-BR` and `es` rows in the same change. The variants themselves are produced once, at upload or in a queued job (Craft's media module handles image processing), never resized per request.

#### Wasteful DOM Work (Frontend)

Server-rendered pages rarely need heavy client code; the typical INP problem is a vanilla script that rebuilds too much or reads and writes layout in a loop.

```javascript
// BAD: rebuilds the whole list and forces a reflow per row.
function renderRows(table, rows) {
  table.innerHTML = "";
  for (const row of rows) {
    table.insertAdjacentHTML("beforeend", row.html);
    row.height = table.lastElementChild.offsetHeight; // read after write: forced layout
  }
}

// GOOD: build off-document once, insert once, read layout after all writes.
function renderRowsBatched(table, template, rows) {
  const fragment = document.createDocumentFragment();
  for (const row of rows) {
    const node = template.content.firstElementChild.cloneNode(true);
    node.querySelector("[data-field=title]").textContent = row.title;
    fragment.append(node);
  }
  table.replaceChildren(fragment);
}
```

Long loops in event handlers yield to the browser between chunks so input can be processed:

```javascript
const yieldToMain = () =>
  "scheduler" in window && "yield" in scheduler
    ? scheduler.yield()
    : new Promise((resolve) => setTimeout(resolve, 0));

async function processInChunks(items, handleItem) {
  for (let index = 0; index < items.length; index += 1) {
    handleItem(items[index]);
    if (index % 50 === 49) await yieldToMain();
  }
}
```

Do not add per-element listeners to hundreds of rows; delegate one listener on the container. Scroll and resize listeners are `{ passive: true }` and throttled.

#### Too Much Static Weight

There is no bundler in a Craft project, so there is no tree shaking to lean on: every byte in `public/` that a page references is a byte the user downloads.

- Load page-specific scripts only on the pages that use them (a Forge section or `@include` per page), not from the global layout.
- Every `<script>` is `defer` (or `type="module"`, which defers by default). Nothing blocking in `<head>`.
- A heavy, rarely used feature (a chart, a rich editor) is loaded on demand with a native dynamic `import()` of its vendored module when the user opens it.
- Vendored libraries are the minified distribution file, reviewed for size before being committed.
- Critical above-the-fold CSS can be inlined in the layout; the rest stays in versioned files.

#### Missing Caching (Backend)

Cache what is expensive to produce **and** read far more often than it changes. Caching a query that was already fast adds a hop, a staleness bug and an eviction policy to maintain, in exchange for nothing.

**Pick the layer deliberately:**

| Layer | Visible to | Use when | Cost |
|---|---|---|---|
| In-process (`CACHE_DRIVER=memory`, the array store) | One process | Small, hot, and per-process staleness is acceptable | Each worker drifts independently; invalidation reaches only one process. Also what tests use |
| Shared (`CACHE_DRIVER=redis`, or `file` on a single host) | All processes | Workers must agree, or the value is expensive to recompute | A network hop and another service to run. If Redis is unreachable Craft falls back to memory and logs a warning; alert on it |
| Reverse proxy / CDN | Everyone, per URL | Responses are public and identical for a given key | Invalidation is the hard part; assume a bad response cannot be recalled quickly |

The `Cache` facade (`from craft.facades import Cache`) offers `get`, `put`, `add`, `forget`, `remember`, `remember_forever`, `increment`. TTLs are seconds. Shared stores serialize to JSON, so cache plain data (ids, dicts, rendered numbers), not model instances. The call belongs in a service resolved from the container, wrapping a repository call:

```python
from craft.facades import Cache

from app.Repositories.plan_repository import PlanRepository

PLAN_CATALOG_TTL_SECONDS = 300  # Staleness window agreed with product: 5 minutes.


class PlanCatalogService:
    """Serve the public plan catalog from cache."""

    def __init__(self, plans: PlanRepository) -> None:
        self._plans = plans

    def catalog(self, tenant_id: str, locale: str) -> list[dict[str, object]]:
        """Return the plan catalog for a tenant and locale.

        Args:
            tenant_id: Tenant the catalog belongs to.
            locale: Resolved request locale; labels differ per locale.

        Returns:
            Plans as plain dictionaries, safe to serialize.
        """
        key = f"plans:catalog:v2:{tenant_id}:{locale}"
        return Cache.remember(key, PLAN_CATALOG_TTL_SECONDS, lambda: self._plans.public_catalog(tenant_id))
```

Static files in `public/` are served by the application with no long-lived `Cache-Control` of their own. Forge's `asset()` helper appends `?ver=<APP_VERSION>` (the file's modification time in debug), so a release changes every asset URL. That makes it safe to have the reverse proxy or CDN in front of the app serve `/assets/` with `Cache-Control: public, max-age=31536000, immutable` and compression (gzip or brotli) for text types, while HTML stays short-lived or `no-cache`. Reference every asset through `asset()`; a hardcoded path is never busted by a release.

**Key design decides correctness.** Every input that changes the result belongs in the key: tenant, locale, viewer or permission set, feature flags. A key that omits the viewer is how one user's data gets served to another, shipped as a performance win. In a multi-tenant module, a key without the tenant id is a data leak and an LGPD/GDPR incident.

**Choose one invalidation strategy, not three:**

| Strategy | Trade-off |
|---|---|
| TTL | Simplest. You accept staleness up to the TTL, so write the acceptable window down |
| Event based (a listener calls `Cache.forget` when the model changes) | Fresh on write, but writers now have to know the cache topology |
| Versioned keys (`plans:catalog:v7:...`) | Never invalidate, just stop reading old keys. Costs memory until eviction |

**Guard against the stampede.** A hot key expires, every concurrent request misses together, and PostgreSQL takes the full load at once. `Cache.remember` does not coalesce concurrent misses by itself. Use `Cache.add` (atomic put-if-absent on every store) as a short lock so one caller recomputes while the others serve the previous value or wait briefly, or refresh hot keys ahead of expiry from a scheduled job.

**Do not cache:** anything whose staleness is a correctness bug (balances, permissions, stock at checkout), or per-user data under a key that does not identify the user. See `.claude/references/performance-checklist.md` for read/write patterns, negative caching, coalescing and the cache checklist.

#### Heavy Work Inside the Request

Anything slow that the response does not need to wait for (sending mail, generating a PDF, resizing images, calling a slow third party, rebuilding a report) moves to a queued job. Jobs serialize their public attributes to JSON, so pass ids, never model instances:

```python
from craft.queue.job import Job


class RebuildInvoiceSummaryJob(Job):
    """Recompute a tenant's invoice summary outside the request."""

    queue = "reports"

    def __init__(self, tenant_id: str, month: str) -> None:
        self.tenant_id = tenant_id
        self.month = month

    def handle(self) -> None:
        """Rebuild the summary; resolves its service from the container."""
        ...
```

Dispatch with `Queue.push(RebuildInvoiceSummaryJob(tenant_id, month))` (or `Queue.later(seconds, job)`) and run workers with `python dev.py queue:work`. The default `QUEUE_CONNECTION=sync` runs the job inline, which is right for tests and wrong for a performance fix: confirm production uses `database` or `redis`, or the "optimization" moved nothing.

### Step 4: Verify (Keep or Revert)

A fix is a hypothesis until it is re-measured. This step decides whether it survives.

**Re-measure exactly the way the baseline was measured:** same command, same data volume, same throttling, same fixed budget (wall-clock, sample count or request count). A cold-cache baseline against a warm-cache result measures the cache, not the change.

**Change one thing at a time.** Three optimizations landed together produce one number that cannot be attributed. If they must ship together, measure each in isolation first.

**Beat the noise, not just the mean.** Repeat the measurement and compare the delta against run-to-run variance. A 3% gain inside a 5% variance is not a gain, it is a different sample.

Then decide strictly:

| Result vs. baseline | Action |
|---|---|
| Past the threshold, all gates green | **Keep.** Commit with the before/after numbers in the message body |
| Within noise | **Revert.** |
| Worse | **Revert.** |
| Improved, but a test went red | **Revert.** A regression wearing a win's clothes |

**"Neutral" is a revert, not a keep.** This is the step teams skip: the change is written, throwing it away feels wasteful, so it lands unmeasured and the codebase accretes complexity that bought nothing. Kept code is maintained forever.

**Correctness gates the metric.** `python -m pytest tests`, `ruff check engine`, `python .claude/rules/lint_language.py` and `python .claude/rules/lint_structure.py` stay green **and** the number moves. An optimization that wins by dropping required work (skipping validation, caching what must be fresh, leaving a translation key unresolved, bypassing a tenant scope) is a regression.

#### Log every attempt, including the reverted ones

Reverted work leaves no trace in git history, which is why the same dead idea is tried again next quarter. Keep a short ledger so a discarded idea stays discarded:

| Idea | Baseline -> Result | Verdict | Why |
|---|---|---|---|
| Cache the dashboard counters | p95 180ms -> 176ms | reverted | Inside noise (+/-10ms); the counters were already indexed |
| `with_("author", "comments")` on the post index | p95 640ms -> 95ms | kept | 41 queries down to 3 |
| Preconnect to the API origin | LCP 2.8s -> 2.8s | reverted | Already same-origin |

A section in the pull request description or a `docs/performance-ledger.md` both work. The next person, or the next agent, reads it before proposing an experiment. Every kept change also gets its `CHANGELOG.md` entry under `## [Unreleased]` (`Changed` or `Fixed`).

### Step 5: Guard Against Regression

Guard the metric users actually feel, the same LCP, INP or p95 latency that justified the fix, not every available number.

Use two layers when the surface is user-facing:

- **Synthetic gate before merge:** a performance budget checked in CI (Lighthouse run against a started `python dev.py serve`, or a pytest assertion on query count). Repeat noisy measurements or compare a median so run-to-run variance does not make the check flaky.
- **Field monitoring:** alert on a meaningful p75 movement in RUM data and on `craft_request_duration_seconds` p95 per route. Treat CrUX's rolling 28-day window as confirmation, not as an immediate alert.

When either guard fires, return to Step 1 and take a fresh baseline before proposing another fix.

A query-count test pins an N+1 fix permanently. It counts the SQL actually issued, because asserting on results alone would pass just as happily with lazy loading:

```python
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any


@contextmanager
def count_selects(db: Any) -> Iterator[list[str]]:
    """Record every SELECT issued through the database manager.

    Args:
        db: The `db` binding resolved from the container.

    Yields:
        The list that collects SELECT statements while the block runs.
    """
    issued: list[str] = []
    original = db.statement

    def counting(query: str, bindings: object = None, read: bool = False) -> object:
        if query.lstrip().upper().startswith("SELECT"):
            issued.append(query)
        return original(query, bindings, read)

    db.statement = counting
    try:
        yield issued
    finally:
        db.statement = original


def test_post_index_query_count_is_constant(migrated_database: Any, seeded_posts: Any) -> None:
    repository = PostRepository()
    with count_selects(migrated_database.make("db")) as issued:
        for post in repository.recent_with_authors():
            post.author().first()
    assert len(issued) == 2
```

**Set budgets and enforce them:**

```
JavaScript per page: < 100KB compressed (server-rendered pages should need far less than SPA budgets)
CSS: < 50KB compressed
Images: < 200KB per above-the-fold image
Fonts: < 100KB total
Route response time: < 200ms p95 (craft_request_duration_seconds)
Queries per request: a fixed number, asserted in tests for list pages
Lighthouse Performance score: >= 90
```

## See Also

For the detailed checklists, caching patterns, measurement commands and anti-pattern table, see `.claude/references/performance-checklist.md`. For live browser measurement, see the `browser-testing-with-devtools` skill (`.claude/skills/browser-testing-with-devtools/SKILL.md`). For an audit-level pass on a web surface, use `/webperf`, which runs the `web-performance-auditor` agent.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "We'll optimize later" | Performance debt compounds. Fix obvious anti-patterns (N+1, unbounded queries) now; defer micro-optimizations. |
| "It's fast on my machine" | Your machine has a warm cache, ten rows and no network latency. Profile with production-like data and throttling. |
| "This optimization is obvious" | If it was not measured, it is not known. Profile first. |
| "Users won't notice 100ms" | Latency affects conversion and perceived quality. Users notice more than expected. |
| "The framework handles performance" | Craft gives you `with_()`, pagination caps, pooling and metrics; it cannot stop a loop that lazily loads a relation per row. |
| "The query is slow, add an index" | Read the plan first. The index may exist and be unusable, and every index taxes writes forever. |
| "Just cache it" | Caching an already cheap call buys nothing and adds a staleness bug. Cache what is expensive and re-read far more than written. |
| "Raise DB_POOL_SIZE, we're running out of connections" | A pool bigger than PostgreSQL can serve moves the queue somewhere less visible. Find what holds connections. |
| "Put it on the queue, it'll be faster" | With `QUEUE_CONNECTION=sync` it still runs inline. And a job the user must wait for is not faster, only harder to see. |
| "It didn't help much, but it doesn't hurt" | Neutral changes are a revert. Maintenance is paid on them forever. |
| "We already wrote it, may as well keep it" | Sunk cost. The measurement does not care how long the change took. |
| "The improvement is obvious, no need to re-measure" | Then re-measuring is cheap and proves it. Unmeasured wins are how neutral complexity lands. |

## Red Flags

- Optimization without profiling data to justify it
- A relation accessed inside a loop without `with_()` on the query that produced the list
- An index added without a query plan before and after
- A cache key that omits an input the result depends on (tenant, locale, viewer)
- A cache with no stated staleness window and no invalidation strategy
- Model instances put into a shared cache or into a job's constructor
- `DB_POOL_SIZE` raised in response to exhaustion without finding what holds connections
- List routes or API endpoints without `paginate()` or a `limit()`
- Images without dimensions, lazy loading or responsive sizes
- Assets referenced by literal path instead of `asset()`, so releases never bust caches
- Static weight in `public/` growing without review; scripts in `<head>` without `defer`
- Slow work (mail, PDF, third-party calls) executed inside the request
- No monitoring of `/metrics` in production
- Optimizations kept without a re-measurement that justifies them
- Several optimizations bundled into one measurement
- A "win" that required a test to be changed, skipped or deleted, or a gate to be relaxed
- The same failed optimization attempted twice because nobody recorded the first attempt

## Verification

After any performance-related change:

- [ ] Before and after measurements exist, with specific numbers
- [ ] The result was re-measured the same way as the baseline (same command, data, conditions)
- [ ] The improvement exceeds run-to-run variance, not just the mean
- [ ] Changes that did not beat the baseline were reverted, not kept as neutral
- [ ] Attempts are logged, kept and reverted alike
- [ ] The specific bottleneck is identified and addressed
- [ ] Core Web Vitals are within "Good" thresholds for the affected pages
- [ ] Static weight per page has not grown significantly
- [ ] No N+1 queries in new data access code; list pages have a query-count test
- [ ] Any new index is justified by a plan before and after, added in a forward-only migration, with its write cost considered
- [ ] Any new cache states what it keys on (tenant and locale included) and how it goes stale
- [ ] The user-facing metric has a synthetic budget or field monitor that can detect regression
- [ ] `python -m pytest tests`, `ruff check engine`, `python .claude/rules/lint_language.py` and `python .claude/rules/lint_structure.py` all pass
- [ ] `CHANGELOG.md` has an entry under `## [Unreleased]`
