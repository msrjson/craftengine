# Engine boundary — extensions never override the engine

**Status:** mandatory. **Decision:** `docs/adr/0003-engine-boundary-and-internal-proxy.md`.
**Gate:** `cd data && python tools/check_engine_boundary.py` (CI and NR-03).
**Test:** `data/tests/test_engine_boundary.py`.

This file is project-owned on purpose: the shared governance files under
`.claude/rules/` are re-provisioned from a global source and would lose a
section added to them.

## Rules

- **EB-01 — No business rule in the engine.** Nothing under `data/engine/`
  encodes a domain decision: no prices, tenants, plans, permissions of a
  specific product, documents or workflows. Business rules live in the
  application's modules and plugins.
- **EB-02 — The engine never imports the application.** No file under
  `data/engine/` imports `app`, `routes`, `database`, `config` or `bootstrap`,
  statically or through a literal `importlib.import_module` / `__import__`.
  Hiding an import behind a computed name to pass the gate is a violation of
  this rule, not a fix.
- **EB-03 — Extend through seams.** When a module needs behavior the engine
  lacks, add a seam the application configures (a config key, an event, a
  contract, a plugin hook) — never a special case for one application.
- **EB-04 — The kernel serves external traffic only.** It knows no subsystem
  by name: it does not import or reset auth, ORM, i18n or any module.
  Per-request state lives in context variables that die with the request.
- **EB-05 — Modules talk through the internal proxy, events or contracts.**
  Never through loopback HTTP into the kernel, never by importing another
  module's controller. A service never imports a controller.
- **EB-06 — Infrastructure holds no tenant rule.** Tenant isolation is barrier
  1 (modules and controllers) and barrier 2 (database row-level security). The
  kernel and the internal proxy carry context unchanged; they never resolve,
  guess or rewrite a tenant.
- **EB-07 — The ratchet only tightens.** `data/tools/engine-boundary-policy.json`
  pins the base commit. Debt may shrink; the base never advances to hide a new
  finding. Advancing it needs an explicit owner ruling in the commit message.

## Definition of done (added to every change touching `data/engine/`)

- [ ] `python tools/check_engine_boundary.py` exits 0 (run from `data/`)
- [ ] `tests/test_engine_boundary.py` passes in the `framework` container
- [ ] No new domain vocabulary in `data/engine/`; any new need became a seam
