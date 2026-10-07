---
task: p2-20261005-095531-extension-manager-panel
outcome: resolved
agent: qwen@qwen-code (local Ollama)
started_at: 2026-10-07T18:49:19Z
finished_at: 2026-10-07T18:49:19Z
commits: []
---

## What changed

- No code change. The deliverable already exists: the `extension_manager`
  module of `data-demo` (`app/modules/extension_manager/`), delivered under the
  CRM demo task `p2-20261005-095553`. Verified against every Done-when
  criterion:
  - `controllers/manager_controller.py` lists modules/plugins/themes via
    `ExtensionManager.status()` (kind, version, state, availability) and drives
    `install`/`activate`/`deactivate`/`uninstall` and the theme choice.
  - `routes.py` guards every route with `.middleware("auth", "role:admin")`;
    `views/index.forge.py` carries `@csrf` on every POST form; the copy lives in
    `lang/catalog.json` for `en`, `pt-BR` and `es`.
  - A refusal redirects with `{"extension": [message_key], "slug", "detail"}`
    and the view renders it in a `role="alert"` notice.

## Verification

- `docker exec craftengine-demo sh -lc 'cd /app && python -m pytest tests -q'`
  -> **55 passed**.
- `data-demo/tests/test_walkthrough.py::test_the_panel_explains_a_refusal`
  posts a deactivate of `companies` (which has the active dependent `contacts`)
  and asserts `role="alert"` plus `"contacts"` on the page -> covered.
- `data-demo/tests/test_walkthrough.py::test_the_panel_switches_a_module_off_and_on`
  and `test_crm.py` (route set, `EXTENSION_HAS_ACTIVE_DEPENDENTS`, three-locale
  keys) -> passed inside the same run.

## Follow-ups

- none. The task's `data/tests/` touch turned out to be unnecessary: no
  framework change was needed.
