# Cache

```python
from craft.facades import Cache

Cache.put("stats", value, ttl=300)
Cache.get("stats", default=None)
Cache.has("stats")
Cache.forget("stats")
Cache.flush()
```

## Stores

| Driver | Where | Use it for |
|---|---|---|
| `array` | Process memory | Default; tests and single-process development |
| `file` | `storage/framework/cache` | Survives a restart, no extra service |
| `redis` | Redis | Shared across processes and machines |

```ini
CACHE_DRIVER=array
```

Redis needs the extra:

```bash
pip install -e ".[redis]"
```

If Redis is configured but unreachable, the manager degrades to the array store
rather than failing the request. Cache misses are cheaper than downtime — but it
does mean a misconfigured Redis looks like a very cold cache.

## remember

Compute a value once and reuse it until it expires:

```python
def dashboard_stats():
    return Cache.remember("dashboard.stats", 300, lambda: expensive_query())
```

The callback runs only on a miss. `remember_forever` skips the TTL.

A callback that returns `None` is cached too — `remember` stores a sentinel in
its place, so an expensive lookup that legitimately produced `None` is not
re-run on every call.

## Counters

```python
Cache.increment("page.views")        # 1
Cache.increment("page.views", 5)     # 6
Cache.decrement("page.views", 2)     # 4
```

A missing key starts at zero. Incrementing or decrementing an existing entry
keeps whatever TTL it already had — a counter stored with a 60-second TTL does
not become eternal just because it was bumped.

## pull

Read and forget in one step — handy for one-shot values:

```python
token = Cache.pull("one_time_token")
```

## TTL

`ttl` is in seconds. Omit it, or use `forever`, to store without expiry:

```python
Cache.put("key", value, ttl=60)
Cache.forever("key", value)
```

Expired entries are removed on read, so an expired key behaves exactly like a
missing one.

## What can be cached

The array store keeps the object as-is. The file and Redis stores serialise to
JSON, so values must be JSON-serialisable — dicts, lists, strings, numbers,
booleans and `None`. Model instances are not; cache `model.to_dict()` instead.

## Clearing

```bash
python dev.py cache clear
```

## In tests

The array store is the default under `pytest`, and each `CacheManager` holds its
own store, so tests do not leak cached values into each other. To be explicit:

```python
from craft.cache.manager import ArrayStore, CacheManager

cache = CacheManager()
cache._store = ArrayStore()
```

## Atomic put-if-absent

`Cache.add(key, value, ttl)` stores only when the key is absent and returns
whether this caller won. Reach for it instead of `has()` then `put()`
whenever the answer decides who does the work: the pair is a race, and every
guarantee built on it silently does not hold.

## Idempotent writes

The cache backs the `IdempotencyKey` middleware. With
`IDEMPOTENCY_ENABLED=true` a write carrying an `Idempotency-Key` header has its
response stored for `IDEMPOTENCY_TTL` seconds, and a retry of the same key is
answered from the store instead of running the handler again:

```bash
curl -X POST https://app.example.com/payments \
  -H 'Idempotency-Key: 0f2b7c1e-...' -H 'Content-Type: application/json' \
  -d '{"amount": "19.90"}'
```

The key is scoped to the tenant and the authenticated user, so one caller's key
can never replay another's response. The first request claims the key with
`Cache.add()`; a retry that arrives while it is still running gets a `409`, and
the claim is released when the handler finishes (or fails). A `5xx` response is
not stored - a retry after a transient failure must be able to run again.

On more than one worker the store must be shared: the array store is
per-process, so a retry that lands on another worker would run the write a
second time. Use `redis` (or a shared `file` store) when the app runs behind a
load balancer.

