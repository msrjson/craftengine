---
id: "20261007-083001"
title: support/branding.py is never executed but documents itself as the brand source
type: decision
priority: 2
autonomous: false
blocked_by: owner-decision
max_attempts: 2
attempts: 0
created_at: 2026-10-07T08:30:01Z
updated_at: 2026-10-07T08:30:01Z
source: framework audit 2026-10-07 (dead-code sweep), verified by hand
touches:
  - data/engine/support/branding.py
  - docs/brand/README.md
  - docs/adr/0001-bare-engine-distribution.md
---

## Problem

`engine/support/branding.py` is executed by nothing, yet two documents call it
the canonical source of the Craft Engine palette and wordmark. Removing it as
dead code and removing it as the brand source are different decisions.

## Evidence

- `data/engine/support/branding.py:71` - `console_banner(version, release)` is
  defined and never called; `serve` does not print a banner; no module imports
  `engine.support.branding` anywhere in `data/`, `data-demo/`, `data-website/`.
- `docs/brand/README.md:34` - "These are mirrored in
  `data/engine/support/branding.py`, which is what the ..."; `:48` -
  "`craft.support.branding.WORDMARK_STACKED` is what the banner prints".
- `docs/adr/0001-bare-engine-distribution.md:160` - "The brand palette survives
  in `engine/support/branding.py` even though the ...".
- `data/engine/cli/skeleton/resources/views/welcome.forge.py.stub:48` and
  `data/resources/views/welcome.forge.py:48` - a comment points at
  `craft.support.branding`.
- `data/CHANGELOG.md:621` - the module was added holding the wordmark and palette.

## Done when

- [ ] The owner picks one:
      (a) **remove** the module and move the palette/wordmark into `docs/brand/`
      (which the README already treats as the mirror), updating the two
      documents and the two comments; or
      (b) **use** it - print `console_banner()` from the CLI (`about`/`serve`),
      so the code and the documented banner agree.
- [ ] Whichever way, no document points at a symbol that does not exist.

## Verify

```bash
grep -rn 'support.branding\|console_banner' docs/ data/ --include='*.md' --include='*.py' --include='*.stub'
docker exec framework sh -lc 'cd /app && python -m pytest tests -q'
```

## Notes

The automated sweep reported this as plainly dead ("safe to delete"); reading
the brand documents shows it is referenced as the source of truth. It is a
decision, not a sweep. `console_banner()` being uncalled is a fact; whether the
CLI should print a banner is the owner's call.

## History

- 2026-10-07T08:30:01Z created by qwen@qwen-code (source: dead-code sweep 2026-10-07, cross-checked)
