---
id: "20261004-161342"
title: Format landing numbers per locale (1.513 in pt-BR and es)
type: bugfix
priority: 3
autonomous: true
blocked_by: none
max_attempts: 2
attempts: 0
created_at: 2026-10-04T16:13:42Z
updated_at: 2026-10-05T10:30:44Z
source: evaluation of the boundary/proxy release, 2026-10-04
touches: []
---

## Problem

Facts in `data-website/site.json` are rendered verbatim in every locale, so pt-BR and es pages show English digit grouping ("1,513 req/s", "1,834"). Affects the tests section and the new proxy section.

## Evidence

- `data-website/build.py` `field()` escapes `facts[name]` with no locale formatting.
- `data-website/sync_tests.py` and `sync_benchmark.py` write English-formatted strings.

## Done when

- [ ] Numeric facts are stored as numbers (or raw) and formatted per locale at build time.
- [ ] pt-BR and es pages show `1.513`; en keeps `1,513`.

## Verify

```bash
cd website && python3 build.py && grep -o '1[.,]513' public/pt-BR/index.html public/index.html
```

## Notes

Touches only `data-website/` (separate repository).

## History

- 2026-10-04T16:13:42Z created by claude (source: evaluation of the boundary/proxy release, 2026-10-04)
- 2026-10-05T10:30:44Z paths updated: the site repository moved from website/ to data-website/ (owner ruling 2026-10-05) by claude@claude-code
