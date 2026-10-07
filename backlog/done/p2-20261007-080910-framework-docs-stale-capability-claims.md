---
id: "20261007-080910"
title: Framework overview pages state a stale version and deny capabilities the engine ships
type: chore
priority: 2
autonomous: true
blocked_by: none
max_attempts: 2
attempts: 1
claimed_by: qwen@qwen-code
created_at: 2026-10-07T08:09:10Z
updated_at: 2026-10-07T08:20:00Z
source: framework audit 2026-10-07 (four parallel code explorations of data/engine/)
touches:
  - data/CRAFT_ENGINE.md
  - data/documentation/market_evaluation.md
---

## Problem

`data/CRAFT_ENGINE.md` is the first page every agent is told to read, and it
both claims a version from the past and contradicts the code about what ships.
`data/documentation/market_evaluation.md` repeats the stale version. Both are
what an agent quotes before writing code, so a false claim propagates.

## Evidence

- `data/CRAFT_ENGINE.md` headline: "Version 3.18.0 · **1200+ tests**".
- `data/CRAFT_ENGINE.md`, subsystem table preamble: "There is no third-party
  ORM, **no third-party template engine**, no migration tool borrowed from
  elsewhere". The view layer is Jinja2 preprocessed into the Forge dialect:
  `data/engine/view/forge.py:3` ("Jinja2 with Forge directives. Templates are
  preprocessed before Jinja"), `data/pyproject.toml:41` (`"jinja2>=3.1"`).
- `data/CRAFT_ENGINE.md`, "What does not exist yet" denies four things the code
  has:
  - "No storage/filesystem abstraction. No S3 driver." — `data/engine/storage/drivers/s3.py` exists (boto3, extra `s3`), plus `drivers/local.py`; the subsystem table on the same page already lists "Local & S3-compatible cloud object storage".
  - "No mail subsystem. No SMTP anywhere in the codebase" — `data/engine/mail/drivers/smtp.py` and `drivers/log.py` exist; the same page's table lists "SMTP with TLS/SSL".
  - "No Redis queue driver. `QUEUE_CONNECTION=redis` warns and falls back to `database`" — `data/engine/queue/manager.py:115` (`SUPPORTED_DRIVERS = ("sync", "database", "redis")`) and `:117-124` (`import redis`) implement it.
  - "No broadcasting or notification subsystem." — `data/engine/facades/__init__.py:49` (`class Broadcast`) and `data/engine/queue/listener.py:156` (`class Broadcaster`, PostgreSQL LISTEN/NOTIFY publish/subscribe, bound as the `broadcast` singleton).
- Still true and to be kept: no API key manager (`AuthenticateApiToken` + `api_token` only, `data/engine/http/middleware.py:820`), no password-reset/email-verification flow, eager loading covers one level, no `remember me`, cookie sessions sign but do not encrypt, no SES/Mailgun mail driver, no ffmpeg-free video pipeline.
- `data/documentation/market_evaluation.md` — quadrant chart ("Craft Engine v3.20"), positioning sentence and comparison matrix header ("Craft Engine (v3.20)") all name a version the repository no longer is.

## Done when

- [ ] `data/CRAFT_ENGINE.md` states the real version/release and a test count that matches the last release evidence, or drops numbers that age.
- [ ] No line in `data/CRAFT_ENGINE.md` denies storage/S3, mail/SMTP, the Redis queue driver or the Broadcaster; the template-engine sentence matches Jinja2-preprocessed Forge.
- [ ] Items that remain unimplemented stay listed and only those.
- [ ] `data/documentation/market_evaluation.md` no longer cites v3.20 and its capability claims match the code.

## Verify

```bash
grep -n '3.18.0\|1200+\|no third-party template engine\|No S3 driver\|No mail subsystem\|No Redis queue driver\|No broadcasting' data/CRAFT_ENGINE.md   # expect no match
grep -n 'v3.20\|3\.20' data/documentation/market_evaluation.md   # expect no match
python3 .claude/rules/lint_language.py --config language-standard.toml
```

## Notes

Documentation only; no engine code changes. The code is the authority (repository rule: code wins over documentation). Numbers were verified against `data/engine/__init__.py` (4.7.0) and the v4.7.0-r00027 release evidence on the board (SQLite 1971, PostgreSQL 2033).

## History

- 2026-10-07T08:09:10Z created by qwen@qwen-code (source: framework audit 2026-10-07)
- 2026-10-07T08:10:00Z claimed by qwen@qwen-code (attempt 1)
- 2026-10-07T08:20:00Z resolved by qwen@qwen-code (resolutions/p2-20261007-080910-framework-docs-stale-capability-claims.resolution.md)
