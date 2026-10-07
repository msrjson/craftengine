---
id: "20261007-080912"
title: ADR 0004 and ADR 0005 no longer describe the extension kinds and engine commands that exist
type: chore
priority: 3
autonomous: true
blocked_by: none
max_attempts: 2
attempts: 1
claimed_by: qwen@qwen-code
created_at: 2026-10-07T08:09:12Z
updated_at: 2026-10-07T08:20:00Z
source: framework audit 2026-10-07 (ADR review)
touches:
  - docs/adr/0004-extension-model.md
  - docs/adr/0005-engine-lifecycle.md
---

## Problem

Two accepted ADRs lag behind the code they record, and one of them still
promises a migration that has not happened. A reader who trusts the ADR builds
the wrong mental model of the extension system.

## Evidence

- `docs/adr/0004-extension-model.md` titles/describes "three kinds" and its
  decision table lists only module, plugin and theme. The code has four:
  `data/engine/extensions/manifest.py` (`ExtensionKind` includes `connector`),
  added under the owner order of 2026-10-06 (board line 2026-10-06T18:54Z,
  released in v4.6.0-r00026).
- ADR 0004 describes `PluginManager` / `ModuleManager` as adapters over the
  modern extension store. `data/engine/plugins/manager.py:24` still holds its
  own implementation with its own database state; only part of
  `data/engine/modules/manager.py` delegates to `engine.extensions`. The
  migration is partial, not done.
- `docs/adr/0005-engine-lifecycle.md` lists six `engine` commands. The CLI
  exposes more: `data/engine/cli/engine_commands.py` also has `check` and
  `verify-command`.

## Done when

- [ ] ADR 0004 carries a dated amendment recording the fourth kind
      (`connector`, owner order 2026-10-06) and its forbidden contributions.
- [ ] ADR 0004 records the real state of `PluginManager`/`ModuleManager` as
      compatibility paths (partial delegation), not as completed adapters.
- [ ] ADR 0005 lists every `engine` subcommand the CLI registers.

## Verify

```bash
grep -n 'connector' docs/adr/0004-extension-model.md   # expect a match
grep -n 'check\|verify-command' docs/adr/0005-engine-lifecycle.md   # expect a match
```

## Notes

ADRs are historical records of a decision at a point in time: correct them with
a dated amendment / Status note, never by rewriting the original decision text.
The `connector` kind itself was already an owner decision; this task only makes
the record match it.

## History

- 2026-10-07T08:09:12Z created by qwen@qwen-code (source: framework audit 2026-10-07)
- 2026-10-07T08:10:00Z claimed by qwen@qwen-code (attempt 1)
- 2026-10-07T08:20:00Z resolved by qwen@qwen-code (resolutions/p3-20261007-080912-adr-stale-extension-kinds-and-engine-commands.resolution.md)
