---
id: "20261004-161814"
title: Live form field validation engine as a plugin
type: feature
priority: 2
autonomous: false
blocked_by: owner-decision
max_attempts: 2
attempts: 0
created_at: 2026-10-04T16:18:14Z
updated_at: 2026-10-04T16:18:14Z
source: owner request 2026-10-04 (real-time form field validation plugin)
touches:
  - data/plugins/live-validation/
  - data/engine/validation/
  - data/documentation/
  - data/tests/
---

## Problem

Forms are validated only on submit: the user fills a whole form, posts it, and only then learns that a field was wrong. The framework should validate each field while the user types or leaves it, with the same rules the server enforces on submit - one source of truth, never a second copy of the rules in JavaScript.

It ships as a **capability plugin** (ADR 0003, EB-01..05): removable, off unless enabled, and the core gains at most a seam, never the feature.

## Evidence

- Rules already live server-side: `data/engine/validation/form_request.py` (`FormRequest.rules()` / `messages()`, line 43-61) and `data/engine/validation/validator.py` (`Validator`, 30+ rules, `validate()` line 629), with `MessageBag` in `error_bag.py`.
- Plugin shape: `data/plugins/audit-log/plugin.py` - a `PLUGIN` dict plus hooks bridged from `engine/events/lifecycle.py`.
- Forge already emits `@csrf`, `@honeypot`, `@antispam` and `@error('field')` (`documentation/llms.txt`).
- Reference, read-only: SoftPax `data/packages/craft_form_guard/` (`engine.py`, `checks.py`, `patterns.py`, `schemas.py`) and `data/app/plugins/form_guard/plugin.py`. Port ideas, never copy files across workspaces.

## Capability map

1. **Rule source** - the plugin validates one field against the rules of a named `FormRequest`, reusing `Validator`; rules that need other fields (`same:`, `required_with:`) receive the submitted siblings.
2. **Endpoint** - one route registered by the plugin (e.g. `POST /_validate/{form}`), answering `{"field", "valid", "errors": [{"code", "message_key", "message"}]}` with messages resolved in the request locale.
3. **Allowlist** - only forms that opt in (e.g. `live_validation = True` on the `FormRequest`, or a registry the plugin owns) are reachable; an unknown form is 404. Same deny-by-default idea as the internal proxy.
4. **Client** - one vanilla JS file served as a static asset, no build step (governance §9): debounced on input, immediate on blur, `aria-invalid` + `aria-describedby` and an `aria-live` region; degrades to plain submit validation when JS is off.
5. **Forge directive** - e.g. `@live_validation('signup')` on the form, emitting the data attributes and the script tag.
6. **Submit still decides** - the submit path validates everything again; live results are advisory and never trusted.

## Open decisions (owner)

- Endpoint shape and name; per-field call versus whole-form diff.
- Which rules run live: database-backed rules (`unique:`, `exists:`) reveal whether a record exists - live checks on them enable account enumeration. Default proposal: excluded from live validation unless the form opts in per field, behind rate limiting.
- Whether the plugin lives in `data/plugins/` (shipped, disabled by default) or as an optional extra (ADR 0002).

## Done when

- [ ] Owner settled the open decisions; recorded in this file's History.
- [ ] Plugin enable/disable is real: disabled means the route answers 404 and the directive renders nothing.
- [ ] Live and submit validation give the same result for every rule they share (one test per rule family).
- [ ] Security: CSRF required on the endpoint; rate limited per session/IP; no field value or personal data in logs; enumeration-prone rules excluded by default; tenant context carried as for any request (barrier 1 + 2), never resolved by the plugin.
- [ ] i18n: every message is a key with en, pt-BR and es rows in the same change.
- [ ] Accessibility: errors announced through `aria-live`, focus never stolen, works with keyboard only; checked in a real browser.
- [ ] Engine boundary gate 0 new findings; the core gains only a seam, if any (EB-03).
- [ ] Guide in `documentation/` with an example form; CHANGELOG entry.

## Verify

```bash
docker exec framework sh -lc 'cd /app && python -m pytest tests/test_live_validation*.py -q'
docker exec framework sh -lc 'cd /app && CRAFT_TEST_DB=pgsql python -m pytest tests -q'
cd data && python tools/check_engine_boundary.py
python .claude/rules/lint_language.py --config language-standard.toml
```

## Notes

Security- and privacy-relevant (enumeration, rate limits, personal data in requests): design and review stay with a cloud agent, never the local model. Suggested skills: spec-driven-development first, then security-and-hardening and frontend-ui-engineering.

## History

- 2026-10-04T16:18:14Z created by claude (source: owner request 2026-10-04)
