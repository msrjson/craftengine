---
id: "20261004-161343"
title: Stop the CLI launcher importing bootstrap.app
type: chore
priority: 3
autonomous: false
blocked_by: owner-decision
max_attempts: 2
attempts: 0
created_at: 2026-10-04T16:13:43Z
updated_at: 2026-10-04T16:13:43Z
source: evaluation of the boundary/proxy release, 2026-10-04
touches: 
  - data/engine/cli/app.py
  - data/tools/engine-boundary-policy.json
---

## Problem

`engine/cli/app.py` imports `bootstrap.app` three times to load the application's composition root - the only engine-to-application imports left, held as known debt by the boundary gate's ratchet.

## Evidence

- `cd data && python tools/check_engine_boundary.py --full` lists `engine/cli/app.py:114`, `:824`, `:1779` -> `bootstrap.app`.
- ADR 0003, section Known debt.

## Done when

- [ ] The launcher receives the application through an entry point (config or `pyproject` entry point) instead of a hardcoded import.
- [ ] `--full` reports 0 findings; `KNOWN_ENGINE_DEBT` in `tests/test_engine_boundary.py` becomes empty.

## Verify

```bash
cd data && python tools/check_engine_boundary.py --full
```

## Notes

Advancing the policy base is not part of this task (EB-07).

## History

- 2026-10-04T16:13:43Z created by claude (source: evaluation of the boundary/proxy release, 2026-10-04)
