# ADR 0003 — Extensions never override the engine

- **Status:** accepted (owner, 2026-10-03); the boundary gate is implemented,
  the internal proxy is queued (`backlog/pending/p2-20261003-223200-port-internal-proxy.md`)
- **Date:** 2026-10-04
- **Follows:** ADR 0002
- **Scope:** where business rules may live, how the engine is extended, how
  modules talk to each other, and what enforces it

## Context

Agents working on applications kept writing business rules into the engine,
most visibly into the HTTP kernel. Nothing stopped them: the structure gate
checks size, SQL and markup, and no check forbade the engine from importing
the application. Release v4.2.0 showed the pattern from the other side: the
kernel's request `finally` began importing `engine.auth.access` and resetting
the auth manager, coupling the transport layer to a subsystem.

A rule an agent must remember fails as soon as the context is long. A
structure that refuses the change does not.

## Decision

1. **Business rules never live in the engine.** They live in the
   application's modules and plugins. The engine offers seams and nothing else:
   - the **HTTP kernel** serves external traffic only, and holds no knowledge
     of any subsystem or module;
   - the **internal proxy** routes module-to-module calls in memory through
     the container, never through the kernel. It is routing infrastructure:
     it carries the caller's context unchanged and holds no tenant,
     authorization or business rule;
   - **events** carry reactions;
   - **plugins** add capabilities with a real lifecycle (disabled means not
     running);
   - **themes** are presentation only.

   Modules, plugins and themes come and go without touching the engine.

2. **Tenant isolation is two barriers, neither of them infrastructure.**
   Barrier 1 is the codebase (modules and controllers); barrier 2 is the
   database (row-level security). The kernel and the proxy never resolve,
   guess or rewrite a tenant.

3. **The boundary is enforced by a gate, not by memory.**
   `data/tools/check_engine_boundary.py` parses the source (it imports
   nothing) and fails on:
   - `ENGINE_APP_IMPORT`: a file under `engine/` importing `app`, `routes`,
     `database`, `config` or `bootstrap`, including literal
     `importlib.import_module` / `__import__` calls;
   - `SERVICE_CONTROLLER_IMPORT`: an application service importing a controller;
   - `BOUNDARY_SYNTAX`: a file it cannot parse.

   It is **ratcheted**: findings are counted per (file, code, target) against
   the base commit pinned in `data/tools/engine-boundary-policy.json`. Existing
   debt may shrink; anything beyond it fails. A base that is not a full SHA, or
   a history the gate cannot read, blocks the gate (exit 2) instead of
   guessing. The base never advances to hide a finding; advancing it needs an
   explicit owner ruling recorded in the commit message.

   The gate runs in CI on every push and before every release (NR-03);
   `data/tests/test_engine_boundary.py` holds the same boundary inside the
   suite.

4. **When a module needs behavior the engine lacks, add a seam.** Example:
   the engine used to import `routes.console` to register scheduled tasks. The
   application now names the module in `config/app.py` (`console_routes`) and
   the engine imports whatever it is told.

## Known debt

`engine/cli/app.py` imports `bootstrap.app` three times: the CLI launcher loads
the application's composition root. It is held by the ratchet and may only
shrink; the way out is a launcher that receives the application through an
entry point instead of importing it.

## Consequences

- An agent that writes a business rule into the engine is stopped by CI, not
  by a reviewer remembering to look.
- Every new need of a module becomes a seam in the engine, reviewed once,
  rather than a special case inside it.
- The written rules can shrink: each rule a gate enforces no longer needs to
  sit in every agent's context.
