---
task: p2-20261005-095553-crm-demo-on-extension-model
outcome: resolved
agent: qwen@qwen-code (owner-authorised closure of a stale claim)
started_at: 2026-10-07T18:57:24Z
finished_at: 2026-10-07T18:57:24Z
commits: []
---

## What changed

- No new code. The task was built by `claude@claude-code` on 2026-10-05 and its
  claim was never released, so it held every path under `data-demo/` and blocked
  the whole demo queue (BQ-06). The owner authorised closing it.
- Verified that the three remaining Done-when items were already met.

## Verification

- `docker exec craftengine-demo sh -lc 'cd /app && python -m pytest tests -q'`
  -> **66 passed**.
- Modules, plugin and theme exist and are active: `app/modules/`
  (companies, contacts, deals, activities, dashboard, extension_manager,
  tickets, invoices), `app/plugins/` (activity_digest, audit_log),
  `app/themes/` (harbor, midnight) - three-locale keys proven by
  `tests/test_crm.py::TestTranslations`.
- Engine from the canonical remote, not a copy: `data-demo/craft-engine.lock`
  pins `"source": github.com/msrjson/craftengine`, `"ref": "v4.7.0-r00027"`.
- A failing extension leaves the rest serving:
  `data-demo/tests/test_crm.py::TestOneModuleFailingNeverTakesTheCrmDown::test_contacts_still_render_when_companies_is_out_of_service`
  -> passed inside the same run.

## Follow-ups

- none. Closing this releases `data-demo/` so the demo tasks queued behind it
  become claimable again.
