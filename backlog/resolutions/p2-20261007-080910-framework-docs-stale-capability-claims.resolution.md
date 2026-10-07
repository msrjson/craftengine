---
task: p2-20261007-080910-framework-docs-stale-capability-claims
outcome: resolved
agent: qwen@qwen-code (Qwen Code, local Ollama)
started_at: 2026-10-07T08:10:00Z
finished_at: 2026-10-07T08:20:00Z
commits: []
---

## What changed

- `data/CRAFT_ENGINE.md` — headline version/test count corrected from
  "Version 3.18.0 · 1200+ tests" to "Version 4.7.0 (r00027) · 1900+ tests".
- `data/CRAFT_ENGINE.md` — the template-engine sentence no longer claims "no
  third-party template engine"; it now states the view layer is Jinja2
  preprocessed into the Forge dialect (`engine/view/forge.py`).
- `data/CRAFT_ENGINE.md` — "What does not exist yet" dropped the three false
  denials (storage/S3, mail/SMTP, Redis queue driver) and the false "no
  broadcasting" item. Remaining, verified-missing items kept: no API key
  manager, no email-verification/password-reset flow (no SES/Mailgun), no
  client-facing notification subsystem (the `Broadcast` facade is PostgreSQL
  `LISTEN`/`NOTIFY` in-process).
- `data/documentation/market_evaluation.md` — quadrant chart and comparison
  matrix now say "Craft Engine v4.7" instead of "v3.20".

## Verification

```
grep -n '3\.18\.0\|1200+\|no third-party template engine\|No S3 driver\|No mail subsystem\|No Redis queue driver\|No broadcasting' data/CRAFT_ENGINE.md
# OK: none
grep -n 'v3\.20' data/documentation/market_evaluation.md
# OK: none
cd data && python3 ../.claude/rules/lint_language.py --config language-standard.toml
# Language standard: clean. (exit 0)
```

Code grounding for the corrected claims: `data/engine/storage/drivers/s3.py`,
`data/engine/mail/drivers/smtp.py`,
`data/engine/queue/manager.py:115` (`SUPPORTED_DRIVERS`),
`data/engine/queue/listener.py:156` (`Broadcaster`),
`data/engine/view/forge.py:3`, `data/pyproject.toml:41`.

Documentation only; no engine code changed, so the pytest suite was not run.

## Follow-ups

`p3-20261007-081500-language-gate-invocation-documented-wrong` and
`p2-20261007-080911-governance-python-and-frontend-policy-stale` cover further
documentation divergences found in the same audit.
