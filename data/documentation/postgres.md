# PostgreSQL

Craft runs on SQLite, PostgreSQL and MySQL, but it is not neutral about them.
On PostgreSQL a set of capabilities becomes available that the other two cannot
provide — tenant isolation the application cannot forget, a queue that scales
with workers instead of contending, locks the database releases when a process
dies, and query macros for JSONB, ranges, full-text search and vectors.

This guide covers those. Everything here is additive: an application written
against SQLite keeps working, and a migration written for PostgreSQL still
builds a usable development database.

## Which version

**PostgreSQL 18.4 or newer** is what the framework is developed and validated
against, and what `docker-compose.yml` provisions. 14 is the minimum — row-level
security, `SKIP LOCKED`, declarative partitioning and generated columns all
predate it — but 18 is where `uuidv7()` becomes a built-in, which is the
difference between a time-ordered primary key being a column `DEFAULT` and
being something the application has to generate.

```bash
python dev.py db:show
```

reports the server version and says so when it is below the recommended one.
The framework does not guess: version-gated capabilities are probed the same
way extension-gated ones are, so on an older server `uuidv7()` is refused at
the call site with a message naming the version, rather than emitted and left
to fail at insert time.

### Upgrading from 15 or earlier

Two things change together, and doing only one leaves the container
restart-looping:

1. **The data directory format.** A major version writes a different on-disk
   layout, so an 18 server refuses to start on a 15 directory.
2. **The mount point.** From 18 the official image stores data in a
   major-version subdirectory of `/var/lib/postgresql`, and refuses to start if
   it finds a volume at the old `/var/lib/postgresql/data`. The compose file
   moves the mount up one level to match.

```bash
docker compose exec db pg_dumpall -p 5499 -U craft > backup.sql
docker compose down
docker volume rm framework_framework_db_data
docker compose up -d db
docker compose exec -T db psql -p 5499 -U craft -d postgres < backup.sql
```

Take the dump before removing anything, and verify the restore before deleting
the backup. For vector search use `pgvector/pgvector:pg18` instead of the
official image, which does not carry pgvector.

## Capabilities are asked, not assumed

`DB.dialect` answers one question — can this driver do X?

```python
from craft.facades import DB

DB.dialect.name                      # "postgresql"
DB.dialect.supports("skip_locked")   # True
DB.dialect.supports("vector")        # depends on the extensions installed

DB.dialect.require("rls", "isolates one tenant's rows from another's")
```

`require()` raises `UnsupportedFeatureError` rather than warning. That is
deliberate: the previous multi-tenant middleware logged a line and kept serving
requests against shared tables, which is a data-isolation failure wearing the
costume of a working feature.

Two capabilities — `vector` and `trigram` — come from **extensions**, not from
the server version. Craft probes `pg_extension` on first use rather than
assuming, so a query that needs pgvector is refused at the call site with a
message naming the extension, instead of compiling, travelling to the server
and failing there with `type "vector" does not exist`.

```bash
python dev.py db:extensions
```

Install one from a migration:

```python
def up():
    Schema.extension("pg_trgm")
    Schema.extension("vector")
```

## Multi-tenancy

Off by default. `MULTI_TENANCY_ENABLED=true` turns it on, and that is meant to
be a deliberate act: multi-tenancy costs a tenant bound on every request, an
isolation policy on every table, and a database that can enforce one. A
single-tenant application — most personal projects, and plenty of commercial
ones — should not acquire any of that by accident, and pays for none of it
while the flag is off.

Once it *is* on, everything below applies, including the refusals. A driver
that cannot isolate stops the request rather than serving it, because at that
point the application has declared that tenant boundaries matter.

Everything it needs ships with the framework: the `tenants` table is created by
the first migration whether or not you use it, `t.tenant_scoped()` works with
no arguments, and `dev.py db:provision-role` creates the database role the
policies actually apply to. Turning tenancy on is a config change, not an
assembly job.

```bash
# 1. Turn it on
MULTI_TENANCY_ENABLED=true
MULTI_TENANCY_STRATEGY=rls

# 2. Create the role policies apply to, and point the app at it
python dev.py db:provision-role craft_app

# 3. Confirm
python dev.py db:audit-rls
```

Two strategies, selected with `MULTI_TENANCY_STRATEGY`:

| Strategy | What it does | When |
|---|---|---|
| `rls` | Shared tables, `tenant_id`, row-level security policy | The default choice. Migrates once, scales to many tenants |
| `schema` | One PostgreSQL schema per tenant, via `search_path` | A handful of tenants that need physical separation |

### The model

Tenant rows live in shared tables with a `tenant_id` column, and a **row-level
security policy** decides what each connection may see. The application binds a
tenant to a session variable; the policy reads it.

The point is what happens when the application *forgets*. A query with no
tenant bound compares against `NULL` and matches nothing — it does not return
everybody's rows. Isolation stops being something every query has to remember.

Schema-per-tenant is still available through `DB.set_tenant_schema()` for the
few tenants that need physical separation. It is no longer the default: it
migrates every tenant separately, does DDL on the request path for each new
one, and multiplies the system catalogue by the tenant count.

### Declaring a tenant-scoped table

```python
def up():
    Schema.create_table("invoices", lambda t: (
        t.id(),
        t.string("reference"),
        t.decimal("total"),
        t.tenant_scoped(),          # column + index + RLS + policy
        t.timestamps(),
    ))
```

`tenant_scoped()` does four things that must all be true together — adds
`tenant_id`, indexes it first, enables **and forces** row-level security, and
creates the isolation policy. Writing them separately is how a table ends up
with three of the four, which looks isolated and is not.

The generated policy:

```sql
ALTER TABLE "invoices" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "invoices" FORCE  ROW LEVEL SECURITY;
CREATE POLICY "invoices_tenant_isolation" ON "invoices"
    USING      ("tenant_id" = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
    WITH CHECK ("tenant_id" = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);
```

`USING` filters reads, `WITH CHECK` filters writes. Both, or a tenant could
insert a row it can never read back.

### The model mixin

```python
from craft.orm.model import Model
from craft.orm.tenant_scoped import TenantScoped


class Invoice(TenantScoped, Model):
    __table__ = "invoices"
    fillable = ["reference", "total"]
```

List `TenantScoped` **first**. Listed after `Model` it loses the MRO and every
query runs unscoped; the mixin raises at class definition rather than letting
that happen quietly.

```python
Invoice.query().get()          # scoped; raises if no tenant is bound
Invoice.create({...})          # tenant_id filled in automatically
Invoice.across_tenants().get() # deliberately unscoped, for admin paths
```

The `where tenant_id = ?` the mixin adds is **not** the isolation boundary —
the policy is. It is there so the planner picks the tenant-leading index, and
so a suite running on SQLite still fails a cross-tenant assertion.

### Binding a tenant

```python
from craft.facades import Tenant

Tenant.id()          # the bound tenant, or None
Tenant.id_or_fail()  # or a refusal naming the fix
Tenant.bind(tenant_id)

with Tenant.scope(tenant_id):
    Invoice.query().get()
```

`scope()` restores the previous tenant on the way out rather than clearing it,
so an admin task iterating tenants comes back out where it started.

In HTTP, register `ScopeTenant` after `Authenticate`:

```python
kernel.with_middleware(Authenticate, ScopeTenant, ...)
```

It resolves the tenant from the request host, then from the authenticated
user's `tenant_id`. Override `resolve()` or `tenant_for_subdomain()` to change
that.

Queue jobs carry the tenant they were dispatched under and rebind it before
`handle()` runs — otherwise a job runs under whichever tenant the previous job
left behind, or under none, in which case it succeeds against an empty result
set and reports success.

### The role matters more than the policy

> **Row-level security does not apply to a superuser, and does not apply to a
> role with `BYPASSRLS`.** Neither is affected by `FORCE ROW LEVEL SECURITY`,
> which only reaches the table's owner.

A table can report `relrowsecurity = true`, `relforcerowsecurity = true`, carry
a correct policy, and still return every tenant's rows to everyone. Nothing
about the table says so.

Connect the application as a role that is none of those. The framework
provisions it:

```bash
python dev.py db:provision-role craft_app
```

It creates the role `NOBYPASSRLS`, grants it on the current tables *and* on
future ones (`ALTER DEFAULT PRIVILEGES` — without that the role works until the
next migration and then stops), then **re-reads `pg_roles` and fails if the
role still bypasses**. Creating a role is not the same as the role being
subject to policies, and the difference is the whole point. `--dry-run` prints
the SQL without running it.

Run migrations as the owning role, which is a separate credential.

`ScopeTenant` checks this once per process and refuses to serve tenant traffic
it cannot isolate. Put the audit in CI:

```bash
python dev.py db:audit-rls
```

It reports the connecting role, lists every table carrying `tenant_id` that is
not actually protected, and exits non-zero. That is the check that catches the
realistic decay: a table added later without `t.tenant_scoped()`, where nothing
errors and nothing looks wrong.

### How the binding reaches the database

`SET LOCAL app.current_tenant_id = :tenant_id` **does not work** — `SET` is not
a parameterizable statement, so the value would have to be interpolated into
SQL, from request input. Craft uses `set_config()`, which is an ordinary
function call and binds cleanly:

```sql
SELECT set_config('app.current_tenant_id', %s, false);   -- session scope
SELECT set_config('app.current_tenant_id', %s, true);    -- transaction scope
```

Session scope is cleared by `Connection.release()` at pool checkin, and a
connection that cannot be cleared is discarded rather than reused. This is the
most consequential line in the design: a session variable lives on the physical
connection, so one left set is read by whoever borrows it next.

## Queues

On PostgreSQL the queue claims jobs with `SELECT … FOR UPDATE SKIP LOCKED`:

```sql
WITH claimed AS (
    SELECT id FROM jobs
     WHERE queue = ? AND reserved_at IS NULL AND available_at <= ?
     ORDER BY priority DESC, available_at, id
     FOR UPDATE SKIP LOCKED
     LIMIT ?
)
UPDATE jobs AS j SET reserved_at = ?, reserved_by = ?, attempts = j.attempts + 1
  FROM claimed WHERE j.id = claimed.id
RETURNING j.*;
```

Every worker gets a *different* row instead of contending on the head of the
queue, so adding workers adds throughput. A partial index covers the whole hot
path, because a claim never looks at a reserved row.

Everywhere else the same driver falls back to a select-then-conditional-update
claim, which is correct but contends. The rest — push, backoff, dead-letter —
is shared, so the two paths cannot drift.

### Retries and the dead letter

A failing job is released with exponential backoff and **full jitter**, so a
hundred jobs that failed together against one downed dependency do not all wake
at the same instant and knock it over again. When its attempts are spent it
moves to `failed_jobs` — payload intact — in a single transaction.

```bash
python dev.py queue failed
python dev.py queue retry <uuid>
python dev.py queue retry --all
python dev.py queue reclaim        # free reservations held by dead workers
```

Schedule `queue reclaim`: it is what frees jobs whose worker died mid-flight.

### Instant dispatch

```bash
python dev.py queue work --listen
```

An `AFTER INSERT` trigger calls `pg_notify()`, and PostgreSQL holds the
notification until the transaction commits — so a listener is never woken for a
job that then rolled back. Polling stays as the safety net at a five-second
floor, which bounds how long a notification lost to a reconnect can delay a job.

Broadcasting rides the same machinery:

```python
from craft.facades import Broadcast

Broadcast.publish("orders", {"id": order.id, "status": "shipped"})
```

The notification payload ceiling is 8000 bytes. Send an identifier and let the
receiver read the row; `Broadcast.publish()` refuses anything larger rather than
truncating it.

## Locks

```python
from craft.facades import Lock

with Lock.transaction("invoices:close:2026-08") as held:
    if not held:
        return
    close_the_month()

Lock.key("reports:nightly").get(build_report)        # skip if held
Lock.key("ledger").block_for(10).get(post_entries)   # wait, then give up
```

`Lock.transaction()` is the default because the database releases it at
`COMMIT` or `ROLLBACK` with no cooperation — including when the process dies
mid-block, which is exactly the case a TTL-based lock cannot rule out.

`Lock.key()` is session-scoped and lives on the *connection*, so it must be
released by the same connection that took it. `get()` and `hold()` do that in a
`finally`.

Advisory locks are re-entrant within one session: a backend that holds a lock is
granted it again. They exclude *other* connections, which is what overlap
protection is for.

```python
Schedule.command("reports:build").daily_at("02:00").without_overlapping()
```

Where advisory locks are unavailable this falls back to `Cache.add()`, an atomic
put-if-absent. Reach for `Cache.add()` rather than `has()` then `put()` whenever
the answer decides who does the work — the pair is a race, and every guarantee
built on it silently does not hold.

```bash
python dev.py db:locks
python dev.py db:locks "reports:nightly"
```

## Types and query macros

Declare the shape on the model and both directions of the round trip become the
framework's problem:

```python
class Account(Model):
    __table__ = "accounts"
    casts = {
        "meta": "jsonb",
        "tags": "array:str",
        "period": "tsrange",
        "embedding": "vector",
    }
```

Without a cast, a JSONB column arrives as a `dict` under PostgreSQL and a `str`
under SQLite, and writing the `dict` back raises *can't adapt type 'dict'*.

### Money

`"money"` stores an exact amount and its currency as a JSON object
(`{"amount": "10.00", "currency": "BRL"}`) and hands the attribute back as a
`craft.support.money.Money`, so arithmetic is exact and never a float:

```python
from craft.support.money import Money

class Invoice(Model):
    __table__ = "invoices"
    casts = {"total": "money"}      # or "money:EUR" to fix the currency

invoice.total = Money("19.99") + Money("0.01")   # -> BRL 20.00
invoice.total.currency                            # "BRL"
```

Adding or comparing two different currencies raises `CurrencyMismatch`; the
amount is a `Decimal` quantized to the currency's minor unit (two places by
default, none for `JPY` and friends).

### JSONB

```python
Account.query().where_json_contains("meta", {"plan": "pro"})
Account.query().where_json_has_key("meta", "trial_ends_at")
Account.query().where_json_key("meta", "usage.seats", ">", "10")
Order.query().where_json_path("lines", "$[*] ? (@.qty > 100)")
Account.query().order_by_json("meta", "score", "desc")
```

`where_json_contains` is the one predicate a `jsonb_path_ops` index can serve —
about a third the size of the default opclass and faster, at the cost of
supporting `@>` alone:

```python
t.gin_index("meta", ops="jsonb_path_ops")
```

Extraction yields text, so `where_json_key` compares textually. For typed
comparisons use `where_json_path`.

### Arrays and ranges

```python
Post.query().where_array_contains("tags", ["python", "postgres"])   # all of them
Post.query().where_array_overlaps("tags", ["python", "rust"])       # any of them
Post.query().where_array_has("tags", "python")
Post.query().where_array_length("tags", ">", 3)

Booking.query().where_range_contains("period", when)
Booking.query().where_range_overlaps("period", start, end)          # double-booked?
Booking.query().where_range_adjacent("period", start, end)
```

Ranges are half-open (`[lower, upper)`), the only convention under which
adjacent ranges neither overlap nor leave a gap. The database enforces the same
rule:

```python
Schema.extension("btree_gist")   # needed for the equality half
Schema.create_table("bookings", lambda t: (
    t.id(),
    t.big_integer("room_id"),
    t.tsrange("period"),
    t.exclude_with(("room_id", "="), ("period", "&&"), name="no_double_booking"),
))
```

### Full-text search

Compute the document once, in a stored generated column, and index that:

```python
Schema.create_table("articles", lambda t: (
    t.id(),
    t.string("title"),
    t.text("body"),
    t.tsvector("search_document").generated_from({"title": "A", "body": "B"}),
    t.gin_index("search_document"),
))
```

Weights (`A` through `D`) are what let a title match outrank a body match.

```python
Article.query() \
    .where_search("search_document", 'queue "skip locked"') \
    .order_by_relevance("search_document", 'queue "skip locked"') \
    .paginate()
```

`websearch_to_tsquery` is the default because it accepts what a person actually
types — quoted phrases, `OR`, a leading minus — and never raises on input the
other parsers reject. A search box must not return a 500 because somebody typed
an unbalanced quote.

Ranking uses `ts_rank_cd` (cover density), which rewards terms appearing near
each other, so a document containing the phrase outranks one that mentions both
words on different pages.

### Fuzzy matching

```python
Schema.extension("pg_trgm")

User.query().where_similar("name", "jonh doe", threshold=0.3)
User.query().order_by_distance("name", "jon")
```

An explicit threshold rather than the `%` operator, which reads its cutoff from
a session setting the connection pool would then have to manage.

### Vectors

```python
Schema.extension("vector")
Schema.create_table("documents", lambda t: (
    t.id(),
    t.text("body"),
    t.vector("embedding", 1536),
    t.hnsw_index("embedding"),
))
```

```python
Document.query() \
    .where_vector_similar("embedding", query_vector, min_similarity=0.7) \
    .order_by_vector_similarity("embedding", query_vector) \
    .limit(10) \
    .get()
```

A similarity floor becomes the distance ceiling the index understands, so an
HNSW index answers it rather than the process reading the table. On drivers
without pgvector the same calls fall back to scoring in Python — correct, but a
full read of the candidate set, and not a way to search a real corpus.

## Schema

### Indexes

```python
t.index_on(["queue", "priority", "available_at", "id"],
           name="jobs_claim_idx", where="reserved_at IS NULL")

t.unique_index([Expr('lower("email")')], name="users_email_lower_uniq")

t.gin_index("payload", ops="jsonb_path_ops")
t.gist_index("period")
t.hnsw_index("embedding", m=16, ef_construction=64)

t.index_on(["slug"], concurrently=True)
```

A partial index over only the rows that are queried is the difference between a
claim that scans and one that seeks, and keeps the index small enough to stay
resident.

`concurrently=True` builds without an exclusive lock, which PostgreSQL refuses
to do inside a transaction block — so that migration must declare
`transactional = False` at module level, and must be written to be re-runnable.

### Partitioning

```python
Schema.create_table("events", lambda t: (
    t.big_increments("id"),
    t.timestamptz("occurred_at"),
    t.jsonb("payload"),
    t.partition_by_range("occurred_at"),
))

Schema.partition("events", "events_2026_08",
                 values_from="2026-08-01", values_to="2026-09-01")
Schema.partition("events", "events_other", default=True)
```

Uniqueness cannot be enforced across partitions, so every unique constraint must
contain the partition key. Craft folds it into the primary key rather than
letting `CREATE TABLE` fail with a message about index columns.

> A range-partitioned table with **no partition covering `now()` rejects
> inserts.** The maintenance task is not an optimisation — it is what keeps the
> table writable.

```python
Schedule.command("db:partitions events --ahead=3").daily()
```

Keep the `DEFAULT` partition as a backstop and alert on rows landing in it:
they mean the maintenance task stopped running.

### Migrations are atomic

A migration and its ledger row are one transaction where the driver has
transactional DDL, which PostgreSQL does. A failure partway leaves nothing
behind, rather than a half-built schema and no ledger row to describe it.

```python
transactional = False   # for CREATE INDEX CONCURRENTLY, ALTER TYPE … ADD VALUE
```

### UUID keys

```python
t.uuid_primary(default="gen_random_uuid()")   # needs pgcrypto below PG 13
```

`gen_random_uuid()` is version 4 — uniformly random, so every insert lands on a
different B-tree leaf and the index write set is effectively the whole index. On
a hot table prefer the time-ordered version 7 that `Model.new_uuid()` generates:
identically opaque in a URL, and sequential in the index.

## Testing against PostgreSQL

Most of what this guide describes cannot be exercised on SQLite. Point the suite
at a real server:

```powershell
$env:CRAFT_TEST_DB = "pgsql"
$env:DB_HOST = "127.0.0.1"; $env:DB_PORT = "5432"
$env:DB_DATABASE = "craft_validation"
$env:DB_USERNAME = "craft"; $env:DB_PASSWORD = "secret"
python -m pytest
```

The suite creates a purpose-made non-superuser role to verify that policies
genuinely filter. Under a superuser they do not, and a test asserting isolation
would pass for the wrong reason.

## See also

- [ORM](orm.md) — models, relationships, eager loading, soft deletes
- [Migrations](migrations.md) — the schema builder, batches, rollback
- [Queues and events](queues_events.md) — jobs, workers, listeners
- [Database safety](database_safety.md) — absolute data persistence
- [Vector search](vector_search.md) — semantic search through the ORM
- [Cache](cache.md) — stores, TTL, and the atomic `add()`
