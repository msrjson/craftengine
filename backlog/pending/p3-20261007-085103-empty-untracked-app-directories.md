---
id: "20261007-085103"
title: Empty untracked directories app/Services/Identity and app/Support linger in data/
type: chore
priority: 3
autonomous: true
blocked_by: none
max_attempts: 2
attempts: 0
created_at: 2026-10-07T08:51:03Z
updated_at: 2026-10-07T08:51:03Z
source: dead-code audit 2026-10-07 (tree inspection)
touches:
  - data/app/Services/
  - data/app/Support/
  - data/README.md
---

## Problem

Two directories exist in the running tree, hold nothing, and are tracked by
nothing — leftovers from earlier work. One of them (`app/Services/`) is part of
the layout the README documents, so removing it blindly would contradict the
documented structure; the other (`app/Support/`) is documented nowhere.

## Evidence

- `data/app/Services/Identity/` — exists, empty; `git ls-files data/app/Services`
  returns nothing.
- `data/app/Support/` — exists, empty; `git ls-files data/app/Support` returns
  nothing.
- `data/README.md` lists `app/Services/` in the project structure; `app/Support/`
  appears in neither the README nor `data/AGENTS.md`.

## Done when

- [ ] `app/Services/` is either declared part of the tree (a tracked
      `.gitkeep` and a README line) or removed; `app/Support/` follows the same
      decision.
- [ ] No empty untracked directory is left in `data/app/`.

## Verify

```bash
git ls-files data/app/Services data/app/Support | wc -l
ls -la data/app/Services data/app/Support
```

## Notes

Untracked and empty, so removal loses nothing; do it only after deciding whether
`app/Services` belongs in the documented layout.

## History

- 2026-10-07T08:51:03Z created by qwen@qwen-code (source: dead-code audit 2026-10-07)
