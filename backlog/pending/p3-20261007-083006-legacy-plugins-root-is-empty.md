---
id: "20261007-083006"
title: The legacy plugins/ root is empty while the extension model uses app/plugins
type: decision
priority: 3
autonomous: false
blocked_by: owner-decision
max_attempts: 2
attempts: 0
created_at: 2026-10-07T08:30:06Z
updated_at: 2026-10-07T08:30:06Z
source: framework audit 2026-10-07 (dead-code sweep)
touches:
  - data/plugins/
  - data/engine/plugins/manager.py
  - data/AGENTS.md
  - data/documentation/plugins.md
  - data/engine/cli/skeleton/
---

## Problem

`data/plugins/` holds only a `.gitkeep` since the one example plugin moved to the
demo, but it is still read at boot by the legacy `PluginManager` and documented
in the project tree. The modern extension model puts plugins under
`app/plugins` (`config/extensions.py`), so the empty root is a second, dead
location a reader can mistake for the real one.

## Evidence

- `data/plugins/` - `.gitkeep` only; board 2026-10-05 records the `audit-log`
  plugin moved to the demo.
- `data/engine/plugins/manager.py:142` - `os.path.join(base_path, "plugins")`
  walks that root; called at boot (`engine/providers/service_providers.py:284`)
  and by the legacy `plugin sync` command; `tests/test_plugins.py` uses a
  `tmp_path/plugins`.
- `data/engine/cli/skeleton/config/extensions.py.stub:14` - the extension roots
  are `["app/modules", "app/plugins", "app/themes", "app/connectors"]`.

## Done when

- [ ] The owner picks one: keep the legacy root as a documented compatibility
      path, or retire it (remove the disk-discovery branch, the root and its
      mentions) as part of the plugin deprecation.
- [ ] Either way the project tree and `documentation/plugins.md` describe one
      place to put a plugin's code, not two.

## Verify

```bash
ls -a data/plugins/
docker exec framework sh -lc 'cd /app && python -m pytest tests/test_plugins.py -q'
```

## Notes

Retiring it is an engine change (a legacy code path with its own tests) and part
of the ADR 0004 compatibility path; not autonomous.

## History

- 2026-10-07T08:30:06Z created by qwen@qwen-code (source: dead-code sweep 2026-10-07)
