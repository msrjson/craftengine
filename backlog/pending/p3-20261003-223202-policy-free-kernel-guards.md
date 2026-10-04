---
id: "20261003-223202"
title: Evaluate SoftPax's policy-free kernel (route guards declared by the app)
type: decision
priority: 3
autonomous: false
blocked_by: owner-decision
max_attempts: 2
attempts: 0
created_at: 2026-10-03T22:32:02Z
updated_at: 2026-10-04T16:13:45Z
source: SoftPax commit bd378ca6; study 2026-10-03
touches: []
---

## Problem

SoftPax moved application policy out of its kernel: the kernel runs guards the application declares instead of holding them. Decide whether the canonical engine adopts the same seam, plus SoftPax's plugin/module lifecycle findings.

## Evidence

- SoftPax `data/engine/http/guards.py`: `RouteContext`, `run_guards`, fail-closed `ROUTE_POLICY_UNDECLARED` (`:115-129`); `Kernel.set_guards` / `with_scope_router` / `with_error_handler`; app policy in `app/Http/Guards/`, declared in `bootstrap/app.py`.
- SoftPax `data/tests/test_kernel_is_policy_free.py:78,100`: the kernel serves with every `app.*` module unimportable; default guard chain fails closed.
- SoftPax audit `data/documentation/backlog/audit-2026-10-03-craft-isolation.md` CA-01..12: two plugin managers, a disabled plugin's hooks still run, plugin dependencies not enforced. Canonical `data/engine/plugins/manager.py` and `data/engine/modules/manager.py` also have no dependency or cycle handling - check whether the disabled-hook bug exists here too.

## Done when

- [ ] Owner decides adopt / adapt / reject for the guard seam.
- [ ] The disabled-plugin-hook and plugin-dependency findings are checked against canonical managers; any confirmed bug becomes its own `backlog/bugfix/` task.

## Verify

Read-only study; no command.

## Notes

Canonical `data/engine/http/kernel.py` has zero `app` imports today, so this is a design improvement, not a leak fix.

## History

- 2026-10-03T22:32:02Z created by claude (source: SoftPax study)
- 2026-10-04T16:13:45Z note by claude: the internal proxy and RequestTerminated seam now exist (1dfb16f, 913c956); the disabled-plugin-hook check from SoftPax audit CA-10 is still unverified in the canonical managers
