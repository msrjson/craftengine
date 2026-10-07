---
task: p3-20261007-193205-admin-fullwidth-and-extension-subgroups
outcome: resolved
agent: qwen@qwen-code (local Ollama)
started_at: 2026-10-07T19:32:05Z
finished_at: 2026-10-07T19:36:58Z
commits: [d480e87 (data-demo)]
---

## What changed

Owner feedback on the WordPress-style admin, all under `data-demo/`:

- **Full width.** `.admin-content` no longer inherits the `main { max-width:
  1200px }` cap (`max-width: none; margin: 0`), and a wide table scrolls inside
  the workspace (`display: block; overflow-x: auto; white-space: nowrap`) so a
  phone shows the page instead of a squeezed table.
- **Responsive dashboard.** `.dash` is 1 column, then 2 from `48rem`, then 3
  from `80rem`; the special activity span that only worked at `64rem` is gone.
- **Menu icons.** Every navigation entry now names its own icon
  (`"icon": "<slug>"` in each module's `crm.navigation` filter). The `harbor`
  theme ships one inline SVG sprite (`views/partials/icons.forge.py`, 13
  symbols, no external request) and the layout renders
  `<use href="#icon-<slug>">`; `admin-menu__link` became a flex row.
- **Extension subgroups.** `ManagerController` groups by `("module", "plugin",
  "theme", "connector")` (the connector kind was silently dropped before) and
  passes the list to the view; the view renders one `<section
  class="kind-group">` per non-empty kind with a live count, and the new
  `extension_manager.kind.connector` key was added in en, pt-BR and es.

## Verification

- `docker exec craftengine-demo sh -lc 'cd /app && python -m pytest tests -q'`
  -> **107 passed** (was 105; two new tests: the panel groups by kind and every
  menu entry carries its own icon).
- `sh .agents/scripts/rehearse-demo.sh` (engine 4.7.0 r00027, fresh database)
  -> SQLite **107 passed**, disposable PostgreSQL 18 **107 passed**.
- Live check in `craftengine-demo` after `docker restart` (the nav lives in boot
  state) and re-seeding the connector key: panel groups `module 13, plugin 2,
  theme 2, connector 1`, "Conectores" renders, **12 menu icons each with its own
  slug, no `#icon-dot` fallback**.

## Follow-ups

- none. Further WordPress fidelity the owner may ask for (drag-ordered menus,
  a block-style editor, media modal) is not in this task.
