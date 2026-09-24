# Deployment

## Checklist

Work through this before the first production request.

- [ ] `python dev.py key:generate` — with `APP_ENV=production` and no
      `APP_KEY`, the app now refuses to boot rather than degrading silently.
      Outside production, an empty `APP_KEY` falls back to a random
      per-process key: sessions break on restart and are not shared between
      workers.
- [ ] `APP_DEBUG=false` — with it on, stack traces reach the client.
- [ ] `APP_ENV=production`
- [ ] `SESSION_SECURE_COOKIE=true` — the cookie becomes HTTPS-only.
- [ ] Serve `public/` as the web root. `storage/`, `.env`, `app/` and `config/`
      must not be reachable over HTTP.
- [ ] `python dev.py migrate` — never `migrate:fresh`, which drops everything.
- [ ] Confirm `python dev.py db ping` succeeds as the deploy user.
- [ ] Set up a queue worker if you dispatch jobs.

## The ASGI entry point

`public/index.py` exposes `application`:

```python
from bootstrap.app import asgi_app

application = asgi_app
```

Run it with any ASGI server:

```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker public.index:application \
  --bind 0.0.0.0:9000
```

```bash
uvicorn public.index:application --host 0.0.0.0 --port 9000 --workers 4
```

`dev serve` is for development. It enables reload and binds to localhost.

## Docker

`Dockerfile.prod` is a multi-stage build that installs runtime dependencies
only, drops privileges to a non-root `dev` user, and serves through Gunicorn.

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Set through the environment, not a committed `.env`:

```yaml
environment:
  - APP_ENV=production
  - APP_DEBUG=false
  - APP_KEY=${APP_KEY}
  - DB_CONNECTION=pgsql
  - DB_HOST=db
  - DB_DATABASE=${DB_DATABASE}
  - DB_USERNAME=${DB_USERNAME}
  - DB_PASSWORD=${DB_PASSWORD}
  - SESSION_SECURE_COOKIE=true
```

## Concurrency

One worker process already serves requests in parallel: the synchronous
middleware and controller chain runs on a thread pool, and each thread borrows
a pooled database connection for the request. Measured on the sample app, that
is the difference between ~27 req/s regardless of how many clients are
connected and ~115 req/s at 10+ clients.

Scale further with processes, not threads — the GIL caps a single process:

```bash
python dev.py serve --host 0.0.0.0 --port 9000 --no-reload --workers 4
```

`--workers` needs `--no-reload` (the reloader runs a single process; asking for
both tells you so instead of quietly serving with one). Each worker has its own
connection pool, so plan `pool_size × workers` against the database's
`max_connections`.

### Threads and the connection budget

Threads and `pool_size` are one setting seen from both ends: every thread that
touches the database needs a connection, and one that cannot get a connection
only waits out `pool_timeout` and fails. The thread pool therefore defaults to
`pool_size × 2` (minimum 8) rather than the runtime's own default of 40 —
40 threads against a pool of 4 means 36 of them queueing on a timeout instead
of being turned away at the door. Override with `HTTP_THREADPOOL_SIZE` for a
workload that is mostly cached or static.

Budget connections across the whole deployment, not per process:

```text
(pool_size_write + pool_size_read) × web workers
  + pool_size × queue workers
  + 1 per LISTEN listener
  ≤ max_connections − 3 reserved for the superuser
```

Set `APP_NAME` per deployment: it becomes the connection's `application_name`,
which is what makes `pg_stat_activity` able to tell you *which* process is
holding connections open.

## Multiple workers

Some defaults do not survive more than one process:

| Default | Problem | Fix |
|---|---|---|
| `SESSION_DRIVER=cookie` | Fine — the payload travels with the client | — |
| `CACHE_DRIVER=array` | Each worker caches separately | `file` on one host, `redis` across hosts |
| Missing `APP_KEY` | Each worker signs with a different key, so sessions break as requests move between workers | `key:generate` |

With `SESSION_DRIVER=file`, every worker needs the same
`storage/framework/sessions` — a shared volume, or use `cookie`.

## Queue workers

```bash
python dev.py queue work --queue default
```

Run it under a supervisor that restarts it — systemd, supervisord, or a separate
container. The `sync` driver runs jobs inline and needs no worker, but it makes
the request wait. On `SIGTERM` the worker finishes its current job and exits
cleanly; see [Rolling deploys](#rolling-deploys).

## Migrations on deploy

```bash
python dev.py migrate
```

It is idempotent: already-applied migrations are skipped, and on PostgreSQL it
takes an advisory lock first, so every container in a deployment can run the
same command at boot. The first one migrates; the others wait, then find
nothing pending. `MIGRATION_LOCK_TIMEOUT` (default 120s) bounds that wait, and
exceeding it fails the boot rather than migrating concurrently. Drivers
without advisory locks (SQLite, MySQL) run unlocked.

Check the migration status first. If a release needs correction, deploy a new
forward migration that preserves existing columns and records:

```bash
python dev.py migrate:status
```

## Multi-tenancy

PostgreSQL schema-per-tenant is supported:

```python
DB.set_tenant_schema("tenant_42")     # switch search_path
DB.ensure_tenant_schema("tenant_42")  # create and migrate if new
```

On drivers without schema support this is a no-op, so tenant-aware middleware
still runs in development against SQLite.

## Logging

Errors go through the exception handler. Server faults (5xx) are logged with a
stack trace; client errors (4xx) are logged at info level without one, so a wave
of 404s or failed CSRF checks does not bury a real fault.

Configure the handler in `config/logging.py`. In containers, log to stdout and
let the platform collect it.

## Health checks

Two probes ship with the framework, **off until you ask for them**:

```dotenv
HEALTH_ROUTES_ENABLED=true
```

Off by default because a probe is an unauthenticated path into the
installation. Once on, both are dispatched outside the middleware stack, so
neither loads a session nor verifies CSRF, and both are listed by
`python dev.py route list` like any other route:

| Path | Question | Checks | Fails with |
|---|---|---|---|
| `/health` | Is the process wedged? | Nothing external | never |
| `/ready` | Can this instance serve? | Database round-trip, pool census, cache | `503` |

Keeping them apart is not pedantry. Point a liveness probe at something that
checks the database and a database incident restarts every healthy web
instance on top of it, turning one outage into two. Liveness answers from the
process alone; readiness is the one that takes an instance out of rotation.

### What `/ready` tells whom

By default it answers the verdict and nothing else, to everyone:

```jsonc
// GET /ready
{"status": "ok"}          // 200, or {"status": "unavailable"} with 503
```

That is everything a load balancer routes on. The detail behind it is a map of
the installation - what it runs on, and how close it is to exhaustion - so it
is returned only to a caller presenting the readiness token:

```dotenv
HEALTH_READINESS_TOKEN=a-long-random-string
```

```jsonc
// GET /ready, Authorization: Bearer a-long-random-string
{
  "status": "ok",
  "checks": {
    "database": {"driver": "postgresql", "pool_open": 2, "pool_idle": 1,
                 "pool_size": 4, "status": "pass", "duration_ms": 1.4},
    "cache": {"store": "RedisStore", "status": "pass", "duration_ms": 0.3}
  }
}
```

`pool_open == pool_size` sustained is the signal to alert on: the instance is
about to start failing on `pool_timeout`, and that is visible here before it is
visible in the error rate. Point the alerting scraper at `/ready` with the
token; leave the load balancer on the tokenless form.

The token is optional. With none configured the probe still works - everyone
just gets the reduced payload. A wrong token is answered, not hidden: unlike
`/metrics`, a health check that 404s without a secret is a health check the
orchestrator cannot use.

### The cost of being probed

Each readiness run issues a `SELECT 1` and a cache write, so an unauthenticated
path would otherwise turn request rate into database load. One result is shared
by every request that arrives behind it:

```dotenv
HEALTH_READINESS_CACHE_SECONDS=5   # 0 runs the checks on every hit
```

Five seconds is shorter than any sane probe interval, so an orchestrator
polling every ten seconds still sees every run, while a flood costs one
round-trip instead of thousands.

Move them with `HEALTH_LIVENESS_PATH` and `HEALTH_READINESS_PATH`. An
application route on either path takes precedence,
so defining your own `/health` replaces the built-in one rather than colliding
with it. Add a dependency of your own:

```python
from craft.http.health import HealthCheck

reporter.add_check(HealthCheck("search", lambda: {"healthy": index.ping()}))
```

## Rolling deploys

The process handles the ASGI lifespan, so a `SIGTERM` to the web server drains
in-flight requests and then closes the connection pool. Without that, a
replaced container left connections open on the server until it noticed the
socket was gone — which a managed database counts against `max_connections`
in the meantime.

Queue workers and the scheduler stop cooperatively on `SIGTERM`: the worker
finishes the job in hand and exits rather than being killed mid-job, which
would leave the job reserved until the stale sweep reclaimed it and would
repeat any side effect it had already performed. Give the orchestrator a
`terminationGracePeriodSeconds` (or `stop_grace_period`) longer than the
slowest job.

## What to back up

- The database.
- `.env` — specifically `APP_KEY`. Lose it and every existing session is
  invalidated.
- `storage/app/` if you store uploads there.

`storage/framework/cache` and `storage/framework/sessions` are disposable.
