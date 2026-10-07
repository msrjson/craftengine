# Slice 1 — Data Integrity and Tenant Isolation

## Context

Slice 0 (12 correctness/security bugs in the canonical Craft Engine) is complete
and verified — full suite green (1385 passed, 4 skipped). The user's goal is to
implement all phases of `.claude/plans/softpax-upstream-roadmap.md`, validated
along the way with local Ollama models. This plan covers **Slice 1: Data
integrity and tenant isolation**, the next slice in that roadmap.

A code survey (two Explore agents + one Plan agent, all read-only) found that
Craft Engine already ships a real, well-tested tenant-isolation framework
(`TenantScoped`, `TenantManager`, PostgreSQL RLS, `ScopeTenant` middleware,
`db:audit-rls` CLI) — but **zero application models currently use it**, so the
gaps below are framework-level and latent, not yet exploited by real data. The
roadmap's "destructive SQL guard" and "RLS audit with CI exit code" items are
**already built** in Slice 0 / existing code; this slice extends rather than
duplicates them. Everything else — write-path tenant safety, relationship
tenant safety, host-based tenant resolution hardening, a scope guardian, and a
proper test harness — is new work.

Scope confirmed with the user: full breadth, landed as sequential, independently
verifiable steps (not necessarily separate PRs, but each step green before the
next starts). The pooler-probe item detects and **logs a warning**, never
blocks — statement_timeout is applied unconditionally regardless of probe result.

## Step order

Harness lands first so every later step's tests can use it from day one.

### Step 1 — Test harness (`tests/conftest.py`)

- Per-agent test database name: derive a suffix from `PYTEST_XDIST_WORKER` (or
  equivalent), always ending in `_test` so `is_disposable_database()`
  (`engine/migrations/safety.py`, from Slice 0) accepts it.
- Refuse dev == test DB: call `is_disposable_database()` against the resolved
  connection at conftest import time; `pytest.exit(...)` if it fails — reuses
  Slice 0's function, no new logic.
- PostgreSQL advisory lock (`pg_advisory_lock`/`pg_try_advisory_lock`) wrapping
  schema-mutating fixtures, keyed off a hash of the DB name, guarding parallel
  workers against the same physical test DB.
- New `two_tenants` fixture: creates two tenant rows, yields `(tenant_a_id,
  tenant_b_id)`, cleans up — promotes the ad-hoc `ACME`/`BETA` pattern already
  hand-rolled in `tests/test_tenancy_rls.py` into a shared fixture.
- New `client_for_host(host)` helper: issues a test request with the `Host`
  header set, for exercising `ScopeTenant.resolve()` end-to-end.
- New unprivileged-connection fixture: a second PostgreSQL role without
  `BYPASSRLS`, for `enforcement()` tests.

Verify: existing tenancy tests (`test_tenancy_rls.py`, `test_tenancy_wiring.py`,
`test_multi_tenancy_default.py`) still pass unmodified against the new fixtures.

### Step 2 — ORM write-path hardening (gaps 1–4)

**Gap 1 — fail-closed `_write_predicate`** (`engine/orm/tenant_scoped.py`):
replace the silent fallback to an unscoped predicate (when
`self._original.get(tenant_column)` is `None`) with a raise. New exception
`UnaddressableTenantRowError` in `engine/orm/tenancy.py`, same `code`/
`message_key` pattern as `TenantNotBoundError`/`DestructiveOperationRefused`.

**Gap 2 — `TenantScoped` + `SoftDeletes` compatibility** (`engine/orm/tenant_scoped.py`,
`engine/orm/soft_deletes.py`):
- Move the tenant `where` from `TenantScoped.query()` into a new
  `TenantScoped._base_query()` override; make `SoftDeletes._base_query()`
  delegate to `super()._base_query()` when present. This makes both mixins
  cooperate through `_base_query()` regardless of declaration order.
- Change `SoftDeletes.delete()`/`force_delete()`/`restore()` to build their
  UPDATE/DELETE through `self._write_predicate()` instead of a hardcoded
  `WHERE {primary_key} = ?` — this makes gap 1's fail-closed behavior apply to
  soft-delete/restore automatically.
- No new MRO guard class: add a test asserting both mixin orderings compile and
  both predicates apply (cheaper than a third guard).

**Gap 3 — `QueryBuilder.insert()` tenant stamping** (`engine/orm/query_builder.py`):
auto-stamp via `setdefault` when `model_class` declares `tenant_column` —
consistent with `TenantScoped.force_create()`'s existing precedent (explicit
value wins, matches the documented data-import use case). No effect on
non-tenant models (`tenant_column` is `None`).

**Gap 4 — `QueryBuilder.truncate()` tenant safety** (`engine/orm/query_builder.py`):
raise `DestructiveOperationRefused` (Slice 0's existing exception, extended
with an optional `reason: str | None` kwarg — backward compatible, NR-05-safe)
when `model_class` is tenant-scoped. No archive-only mode here (that's a
CLI-level concept, not this method's).

Verify: `tests/test_tenancy_rls.py` extended with cases for all four gaps
(new `UnaddressableTenantRowError`, combined-mixin ordering, `.insert()`
stamping, `.truncate()` refusal), plus one documented regression test for the
existing `force_create` `setdefault` precedent (gap 7 from the survey —
intentional, not changed, just pinned).

### Step 3 — Relationship tenant safety (gap 5)

`engine/orm/relationships.py`, `BelongsToMany.attach()`/`detach()`/`sync()`:
add a `_pivot_tenant_column()` helper that checks whether the pivot table
actually has a tenant column (via the schema introspection already used by
`Schema.column_listing()` — reuse that helper, don't round-trip through the
facade per call). When present: `attach()` stamps it on INSERT, `detach()`
adds it to the DELETE predicate. No behavior change for pivots without a
tenant column (the common case today).

New test file: `tests/test_tenancy_relationships.py` — attach/detach/sync
tenant stamping and cross-tenant detach refusal, with and without a
`tenant_id` column on the pivot.

### Step 4 — Tenant resolution by host

`engine/http/middleware.py` (`ScopeTenant.resolve()`): currently silently
falls back to the authenticated user's tenant on an unbound host, and treats a
suspended tenant identically to a nonexistent one. Fix:
- Unbound host (no matching tenant, not a reserved subdomain) → 404.
- Suspended tenant → 403, distinguishable from "doesn't exist." Requires
  checking whether `tenants` has a `status` column beyond boolean `is_active`
  (a boolean can't distinguish "suspended" from "not yet activated") — add a
  migration for a `status` text column if needed, defaulting existing rows to
  `active`.
- Host resolves to tenant A but the session's `tenant_id` is B → 403.

New exceptions (`engine/orm/tenancy.py`, same pattern):
`UnboundTenantHostError` (→ 404, subclass `NotFoundHttpException`),
`TenantSuspendedError`, `TenantHostMismatchError` (→ 403, subclass whatever
the existing `AuthorizationException` base is) — reuses
`engine/exceptions/handler.py`'s existing status-code dispatch, no new handler
logic needed.

New test file: `tests/test_tenancy_host_resolution.py`, using `client_for_host()`
from Step 1: unbound → 404, suspended → 403, host×session mismatch → 403,
and the legitimate resolution path still works.

### Step 5 — Tenant scope guardian (warn | strict)

New file `engine/orm/tenant_guardian.py` (keeps `tenancy.py` under the 300-line
cap): `TenantScopeGuardian` with a `mode: "warn" | "strict"` and a
`check(*, context: "request" | "console")` method. A request proceeding with no
tenant bound: warn mode logs a structured warning and continues; strict mode
raises. Console/background-job context is exempt (migrations, queue workers
bind explicitly per job already). Config key `database.tenancy.guardian_mode`,
default `"warn"` — wired into `ScopeTenant.handle()` after `tenant.bind(...)`.

New test file: `tests/test_tenancy_guardian.py` — warn logs and proceeds,
strict raises, console/job context exempt.

### Step 6 — Pooler transaction-mode probe + statement_timeout

`engine/orm/connection.py`: add `Connection._probe_pooler_mode()`, run once per
pool (mirrors `enforcement()`'s once-per-process pattern), checking backend PID
stability across two statements without an explicit transaction wrapper. Per
the user's decision: **on suspected transaction-mode pooling, log a structured
warning only — never block or force a different binding mode.**
`statement_timeout`: new `database.statement_timeout_ms` config, applied via
parameterized `SET statement_timeout = ?` (same pattern as `_set_tenant`) on
every checked-out connection, unconditionally (not gated on the probe result).

New test file: `tests/test_pooler_probe.py` (postgres_only) — probe emits a
warning under simulated transaction-mode conditions, statement_timeout is
always applied regardless of probe outcome.

### RLS audit — verify only, no new code

`db:audit-rls` (`engine/cli/app.py`, backed by `TenantManager.audit()`/
`enforcement()`) already implements inheritance-class reporting, declared
exclusions with reason, and a CI-friendly exit code. Add one regression test in
`tests/test_tenancy_wiring.py` pinning the CLI exit code for both a clean and a
deliberately-unprotected-table scenario — no implementation change.

## Critical files

- `engine/orm/tenant_scoped.py`, `engine/orm/soft_deletes.py`,
  `engine/orm/query_builder.py`, `engine/orm/relationships.py` — write-path and
  relationship hardening (Steps 2–3)
- `engine/orm/tenancy.py` — new exception types (all steps), kept under the
  file's existing size discipline; split into `tenant_guardian.py` if it grows
  past cap (Step 5)
- `engine/http/middleware.py` (`ScopeTenant`) — host resolution (Step 4)
- `engine/orm/connection.py` — pooler probe, statement_timeout (Step 6)
- `engine/migrations/safety.py` — extend `DestructiveOperationRefused` with an
  optional `reason` kwarg (Step 2, gap 4)
- `tests/conftest.py` — harness (Step 1); may split into
  `tests/conftest_tenancy.py` if it grows large
- New test files as listed per step above

## Verification

After each step: `docker exec framework sh -lc 'cd /app && python -m pytest -q'`
(full suite on PostgreSQL — matches how Slice 0 was verified) must stay green,
plus the new tests for that step passing specifically. Run
`python .claude/rules/lint_language.py` and `python .claude/rules/lint_structure.py`
before considering any step done, per project governance. Final check after all
six steps: full suite green, both lint gates exit 0, and a manual smoke read of
the new exception messages/`message_key`s to confirm they follow the
`code`/`message_key` contract (no rendered sentences reaching a client
directly). As in Slice 0, once implementation is underway, spot-check
non-trivial pieces (e.g. the guardian's warn/strict logic, the host-resolution
403/404 split) against a local Ollama model's independent read for a second
opinion, consistent with the user's stated goal of using local LLM agents to
validate the work.
