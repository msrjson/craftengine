---
id: "20261007-193205"
title: Full-width responsive admin and extensions grouped by kind
type: feature
priority: 3
autonomous: true
blocked_by: none
max_attempts: 2
attempts: 1
claimed_by: qwen@qwen-code
created_at: 2026-10-07T19:32:05Z
updated_at: 2026-10-07T19:36:58Z
source: owner feedback 2026-10-07 (in session) on the WordPress-style admin
touches:
  - data-demo/app/
  - data-demo/resources/
  - data-demo/tests/
---

## Problem

Two refinements the owner asked for after using the new admin:

1. The dashboard should use the full width and be optimised for desktop and
   mobile. Today `.admin-content` is capped by the global `main { max-width:
   1200px; margin: 0 auto }`, so a wide screen wastes space, and the table
   screens overflow on a phone.
2. The Extensions panel (extension manager) does not list by subgroup: the
   `connector` kind never appears (it is left out of the grouped data), so
   `outbound_webhooks` is invisible, and the subgroup headings carry no
   hierarchy.

## Evidence

- `app/themes/harbor/assets/css/harbor.css`: `main { max-width: 1200px; margin: 0 auto; ... }`
  and `.dash` breaks at `64rem` only.
- `app/modules/extension_manager/controllers/manager_controller.py`: the groups
  dict is built for `("module", "plugin", "theme")` only.
- Rendered check 2026-10-07 (authenticated GET `/admin/extensions`): sections
  `['module', 'plugin', 'theme']`, no connector, 20 rows.

## Done when

- [x] The admin workspace spans the full width on desktop and the table screens
      scroll horizontally instead of breaking the page on a phone.
- [x] The dashboard widget grid is 1 column on mobile, 2 on tablet and 3 on a
      wide desktop.
- [x] The Extensions panel shows every kind as its own subgroup (module, plugin,
      theme, connector) with a live count, and an empty kind is not rendered.
- [x] Every menu entry carries its own icon, matching its function (owner
      feedback 2026-10-07: "os itens do menu não têm ícones de acordo com a
      função").
- [x] The demo suite stays green in the container.

## Verify

```bash
docker exec craftengine-demo sh -lc 'cd /app && python -m pytest tests -q'
sh .agents/scripts/rehearse-demo.sh
```

## Notes

- Copy in en, pt-BR and es (the connector kind key is new).
- Demo context only; no `data/` change.

## History

- 2026-10-07T19:32:05Z created by qwen@qwen-code (owner feedback 2026-10-07: full-width responsive dashboard; extensions grouped by subgroup)
- 2026-10-07T19:32:05Z claimed by qwen@qwen-code (attempt 1)
- 2026-10-07T19:36:58Z scope extended by qwen@qwen-code: the owner added menu icons ("os itens do menu não têm ícones de acordo com a função") to the same request, so a fifth Done-when was added
- 2026-10-07T19:36:58Z resolved by qwen@qwen-code (resolutions/p3-20261007-193205-admin-fullwidth-and-extension-subgroups.resolution.md; data-demo d480e87)
