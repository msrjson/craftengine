---
task: p3-20261007-080912-adr-stale-extension-kinds-and-engine-commands
outcome: resolved
agent: qwen@qwen-code (Qwen Code, local Ollama)
started_at: 2026-10-07T08:10:00Z
finished_at: 2026-10-07T08:20:00Z
commits: []
---

## What changed

- `docs/adr/0004-extension-model.md` — the `Status` line now points at the two
  2026-10-06 amendments (fourth kind `connector`; ownership/update rules) and
  states that the title and decision 1 keep the original three-kind wording on
  purpose. No decision text was rewritten.
- `docs/adr/0004-extension-model.md` — new dated amendment "2026-10-07 — the
  compatibility managers are not adapters yet", recording that
  `PluginManager` still runs its own registry and `ModuleManager` delegates only
  partially, so the adapter consequence is in progress, not delivered.
- `docs/adr/0005-engine-lifecycle.md` — decision 3 lists the full command set:
  `adopt | status | check | verify-command | patch | hotfix | update | upgrade`.

## Verification

```
grep -c 'connector' docs/adr/0004-extension-model.md          # 5
grep -c 'verify-command' docs/adr/0005-engine-lifecycle.md    # 2
```

Code grounding: `data/engine/cli/engine_commands.py` registers eight `engine`
commands (adopt, status, check, verify-command, patch, hotfix, update, upgrade);
`data/engine/plugins/manager.py` keeps `_plugins`/`_registered_slugs` and the
`plugins` table; `data/engine/modules/manager.py` defers only availability and
failure to `engine.extensions`.

Note: the audit that opened this task overstated the ADR 0004 gap — the
`connector` amendment already existed. Only the Status pointer, the manager
amendment and the ADR 0005 command list were missing.

Documentation only; no code changed, pytest not run.

## Follow-ups

None.
