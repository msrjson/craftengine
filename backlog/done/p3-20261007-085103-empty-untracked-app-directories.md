---
id: "20261007-085103"
title: Empty untracked directories app/Services/Identity and app/Support linger in data/
type: chore
priority: 3
autonomous: true
blocked_by: none
max_attempts: 2
attempts: 1
claimed_by: qwen@qwen-code
created_at: 2026-10-07T08:51:03Z
updated_at: 2026-10-07T17:48:37Z
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
- 2026-10-07T17:46:13Z claimed by qwen@qwen-code (attempt 1)
- 2026-10-07T17:46:13Z scope note by qwen@qwen-code: the two directories held only `__pycache__` (ignored bytecode), not literally nothing; decided `app/Services/` is documented (README line 106) so it is declared with the repo's convention - a tracked `app/Services/__init__.py`, matching every other code dir - and the undocumented `app/Support/` plus the stray `app/Services/Identity/` are removed (bytecode only, regenerated on import; no source references either)
- 2026-10-07T17:48:37Z resolved by qwen@qwen-code (resolutions/p3-20261007-085103-empty-untracked-app-directories.resolution.md)
