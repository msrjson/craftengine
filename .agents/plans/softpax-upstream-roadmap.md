# SoftPax → Craft Engine upstream roadmap

Status: **proposed — awaiting owner approval** · Created: 2026-09-15 · Canonical baseline: 3.20.0 r00013

SoftPax (`/data/projects/workspaces/softpax`) is a production multi-tenant ERP running an
old fork of the engine. It is a **read-only learning source**: nothing is edited there, and
nothing is copied verbatim. Every item below is re-implemented here to Craft standards
(English, layer caps, DB-backed i18n, tests in the container, CHANGELOG entry, NR-01..07).

Sources: three read-only surveys (engine diff, application layer, agent workspace).
`VERIFIED` means confirmed by reading canonical code on 2026-09-15; everything else is a
survey finding still to be confirmed at the start of its slice.

## Slice 0 — Correctness and security bugs in the canonical engine

| # | Defect | Canonical location | SoftPax reference | Evidence |
|---|---|---|---|---|
| 0.1 | Firewall reads the **left-most** `X-Forwarded-For` entry unconditionally (client-controlled → IP spoofing bypasses blocks and throttles); `Request.ip()` does the same when proxies are trusted | `engine/security/firewall.py:209-214`, `engine/http/request.py:171-186` | `engine/security/net.py:56-145` (right-most, `TRUSTED_PROXY_HOPS`) | VERIFIED |
| 0.2 | `migrate fresh` / `db wipe --force` / `Migrator.fresh()` run on any database — NR-02 is documented, not enforced | `engine/cli/app.py:165,496`, `engine/migrations/migrator.py:337` | `engine/migrations/migrator.py:326-390`, `tests/test_banco_permanente.py` | VERIFIED |
| 0.3 | Scoped container instances are never released (`forget_scoped_instances` has no caller) → per-request state leaks across requests and tenants | `engine/container/application.py` | `engine/http/kernel.py:552-561` (port as ContextVar scope) | VERIFIED |
| 0.4 | `Model.save()` writes the whole row (lost update) and has no tenant predicate on UPDATE | `engine/orm/model.py:296-321` | `engine/orm/model.py:136-183`, `tests/test_motor_endurecido.py` | VERIFIED |
| 0.5 | Captcha code is rendered as plain text spans in HTML (script-readable) | `engine/security/captcha.py:35-51` | `engine/security/captcha.py:716-903` (signed stateless cookie + PNG) | VERIFIED |
| 0.6 | `%` not escaped when bindings are present (psycopg2 `LIKE 'a%'` breaks) | `engine/orm/connection.py:140-186` | `engine/orm/db.py:683-737` | to confirm with a failing test |
| 0.7 | No SAVEPOINT per statement inside `transaction()` (caught error aborts the PG transaction) | `engine/orm/connection.py:769-808` | `engine/orm/db.py:847-900` | to confirm |
| 0.8 | Kernel fallback returns `str(exc)` to the client (may leak PG `DETAIL`) | `engine/http/kernel.py:47` | `engine/http/kernel.py:28-52` | to confirm |
| 0.9 | Image RGBA→RGB without compositing (black background on transparent PNG) | `engine/media/image.py:402-405` | `engine/media/image.py:71-165` | to confirm |
| 0.10 | `Settings` are global in a multi-tenant app (cross-tenant leak) | `engine/support/settings.py:35-81` | `engine/support/settings.py` | to confirm |
| 0.11 | Honeypot login check is read-decide-write (race), stores identifier in clear, answers distinguishably | `engine/security/honeypot.py:414-536` | `engine/security/limiter.py`, `attempts.py`, `honeypot.py:966-997` | to confirm |
| 0.12 | Route params: raw strings and positional fallback to the wrong argument | `engine/http/kernel.py:437-462` | `engine/http/kernel.py:124-139` | to confirm |

## Slice 1 — Data integrity and tenant isolation

- Destructive-SQL guard for non-disposable databases (`_test` suffix / `DB_DISPOSABLE_DATABASES`), CLI and statement funnel; optional archive-only deletion mode.
- Tenant resolution by host (status allow-list, unbound host 404, suspended tenant, host×session mismatch 403).
- Tenant scope guardian (`warn|strict`) as a second layer behind RLS; request-without-tenant vs console distinction; pooler transaction-mode probe; `statement_timeout`; single retry outside transactions.
- RLS audit: inheritance class, declared exclusions with reason, CI exit code.
- Test harness: per-agent test database, shared/exclusive advisory lock, refuse dev == test DB; `two_tenants` fixture, `client_for_host()`, unprivileged-connection fixture.

## Slice 2 — Auth and security hardening

Context-bound signer (`auth/signer.py`), sliding-window login limiter with atomic upsert,
firewall pipeline (CIDR rules, decaying reputation, shadow-mode patterns, health exempt),
database session store with idle timeout and revocation, step-up auth, TOTP plugin,
Argon2id verification, origin-based CSRF as an extra layer, per-prefix CSP with report-only,
sensitive-data redaction in logs and error handler, credential vault (**AES-GCM**, not the
SoftPax hand-rolled cipher).

## Slice 3 — Migrations, scheduler, release

Converging schema builder (alter type/nullability/default, rename, partial indexes,
idempotent constraints), materialized-view suspension, once-per-window scheduler claim with
catch-up, single app clock (`APP_TIMEZONE`), `Schedule.per_tenant`, seed ledger,
`release:sync` / `release:status` with advisory lock, `VERSION` file, production
Dockerfile (healthcheck, tzdata, real home), `docker/entrypoint.sh`, `.dockerignore`.

## Slice 4 — Platform

DB i18n with tenant override, bundle cache, ICU plural/params, validator errors as
`code` + `message_key`; transactional outbox; plugin circuit breaker; notification contract
with provider failover and quotas; `Idempotency-Key` middleware; `Money` type and ORM cast;
tenant-scoped storage disk with public-path validation; bounded memory cache with prefix
flush; fallback routes ordered last; static files cache headers; server-side datagrid
(dialect-aware); `route:check`; `data:audit`.

## Slice 5 — Official plugins

Brazil validator (alphanumeric CNPJ, IE for 27 states), PIX BR Code, QR/barcode (segno),
XLSX export, XMLDSig/PKCS#12, mTLS channel, cookieless SEO, privacy kit (portability,
legal pages), document seal, e-signature, hash-chained audit trail.

## Slice 6 — Last-generation agent workspace (`agent:scaffold`)

Single root `AGENTS.md` with symlinks and `.agents -> .claude` (fix the duplicate copies
written by `engine/cli/agent_scaffolder.py`); coordination kit (`.claude/team/board.md`,
sessions, `multi-session-coordination.md`, `team-lead` agent); integration points
(`.claude/handoffs/`, `journeys/smoke.json`, `validation.json`, `lessons.md`, generated
`local-brief.md`); Python environment guard hook; generated pre-commit, CI workflow,
VS Code tasks/launch; catalog skills `tests-in-container` and `craft-engine-pitfalls`.

## Explicitly not ported

PHP/Laravel legacy skills; funeral-domain services and skills; auto-learn numbered skills;
auto-approve rule; PowerShell scripts; TypeScript/React islands (STRUCT-F); hand-rolled
cipher; `resource_controller.py` as-is (2593 lines, app-coupled).

## Open decisions for the owner

1. Order: Slice 0 first (bugs) is recommended before any feature work.
2. Release cadence: one release per slice, or a patch release for Slice 0 alone.
3. Datagrid and resource controller: port into the engine or keep in the CRUD Builder.
4. Propagation back to sibling projects (softpax, eventbus, brplaces…) stays out of this
   roadmap — each project's own session decides.
5. **Discovered during Slice 1, Step 4 (host resolution) — an Ollama review flagged
   this, verified by re-reading the code:** `ScopeTenant.resolve()`'s host-tenant
   mismatch check is `if session_tenant_id not in (None, record["id"]): raise
   TenantHostMismatchError(...)`. `None` deliberately passes this check — an
   authenticated user whose account has `tenant_id = NULL` (per the schema's own
   comment: an operator, a support account, or any user of a single-tenant
   deployment) gets silently bound to *whichever* tenant's host they visit, with no
   separate authorization check that they actually belong to it. For an
   **unauthenticated guest** this is correct and intended (a visitor must see tenant
   A's public marketing/login page when they land on tenant A's subdomain — that is
   the entire point of host-based resolution). It is genuinely ambiguous only for an
   **authenticated but tenant-unassigned account** (operator/support): is silently
   granting that account whichever tenant's context the host names intended support
   behavior, or should reaching another tenant's context require an explicit
   impersonation action instead of just typing the subdomain? This is an
   authorization-model decision, not a resolution bug — Slice 1 did not change this
   behavior and did not silently "fix" it pending an answer here.
