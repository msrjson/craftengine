---
id: "20261003-223201"
title: Enforce the engine boundary - no business rules in the engine, ratcheted gate
type: feature
priority: 2
autonomous: false
blocked_by: none
max_attempts: 2
attempts: 0
created_at: 2026-10-03T22:32:01Z
updated_at: 2026-10-03T23:13:11Z
source: owner request 2026-10-03 (agents writing business rules into the kernel); SoftPax Rule 192
touches: [deploy/, .claude/rules/CRAFT_ENGINEERING_GOVERNANCE.md, docs/adr/, data/engine/providers/service_providers.py, data/config/app.py, data/tests/test_engine_boundary.py, .github/workflows/, data/CHANGELOG.md]
---

## Problem

Agents have been writing business rules into the kernel. No gate stops it: `lint_structure.py` has STRUCT-A..I only, and nothing forbids the engine from importing the application. The rule must be written, tested and blocking at release and in CI.

## Evidence

- Real inversion today: `data/engine/providers/service_providers.py:254` imports `routes.console`.
- `from app...` hits under `data/engine/cli/` are template strings (scaffolders) - an AST check does not flag them.
- SoftPax reference (read-only): `deploy/craft_boundary_gate.py` (189 lines, stdlib, AST): `ENGINE_APP_IMPORT`, `SERVICE_CONTROLLER_IMPORT`, `THEME_BUSINESS_IMPORT`, `MODULE_APPLICATION_DECORATOR`, `BOUNDARY_SYNTAX`; resolves aliases, relative imports and literal `importlib.import_module` / `__import__`; debt ratchet by (path, code, target) count against a pinned base in `deploy/craft-boundary-policy.json`; 18-20 tests; wired into `release_gate.py:190-203`.
- SoftPax rule text: `.claude/rules/craft-module-plugin-theme-boundaries.md` R-MOD-01..12; its governance section survives only in `.claude/rules/_replaced/CRAFT_ENGINEERING_GOVERNANCE.md.2026-10-03:228-232`.
- SoftPax weaknesses not to copy: default `--base HEAD` only checks uncommitted work; CI never runs the gate.

## Done when

- [x] Boundary gate in this repo with configurable path predicates (engine roots, app roots `app`/`routes`/`database`/`config`/`bootstrap`, services/controllers), pinned base commit in a policy file, ratchet semantics, exit 0/1/2.
- [x] Default base is the pinned policy commit, not `HEAD`.
- [x] Runs in CI on every push and in the release checklist (NR-03).
- [x] `service_providers.py:254` reads a dotted path from config (`app.console_routes`) and resolves it through the container; behaviour unchanged.
- [x] `tests/test_engine_boundary.py` fails the suite if the engine imports the application.
- [x] ADR 0003 (engine boundary + internal proxy) and an "Engine boundary" section in `.claude/rules/CRAFT_ENGINEERING_GOVERNANCE.md` with the generic R-MOD rules (01-08, 10-12) stripped of SoftPax domain wording; Definition of Done item added.
- [x] Proof the gate bites: a temporary `from app ...` in `data/engine/` fails both the gate and the test, then is reverted.

## Verify

```bash
python deploy/craft_boundary_gate.py --full
docker exec <app-container> sh -lc 'cd /app && python -m pytest tests/test_engine_boundary.py -q'
python .claude/rules/lint_structure.py
```

## Notes

Guiding principle (owner, 2026-10-03): business rules never override the framework. The engine is extended only through the seams it offers - internal proxy for calls, events for reactions, plugins with a real lifecycle (a disabled plugin stops running), themes for presentation only - so modules, plugins and themes come and go without touching the core. The goal is a full-featured framework that stays simple to organize. ADR 0003 states this principle in the project's own terms, without naming third-party frameworks.

The canonical governance file is synced into other projects (it overwrote SoftPax's Rule 192 section at 15:26 on 2026-10-03); once the section lands here, SoftPax gets it back on the next sync. Not delegable to the local model (architecture).

## History

- 2026-10-03T22:32:01Z created by claude (source: owner request + SoftPax study)
- 2026-10-03T22:50:00Z owner principle recorded: extensions never override the core; ADR 0003 must state it
- 2026-10-03T23:13:11Z resolved by claude (resolutions/p2-20261003-223201-engine-boundary-gate.resolution.md)
