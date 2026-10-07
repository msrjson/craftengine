---
id: "20261007-080911"
title: governance.md states Python 3.10+ and forbids TypeScript/Node, against the manifest and the owner ruling
type: chore
priority: 2
autonomous: true
blocked_by: none
max_attempts: 2
attempts: 1
claimed_by: qwen@qwen-code
created_at: 2026-10-07T08:09:11Z
updated_at: 2026-10-07T08:20:00Z
source: framework audit 2026-10-07 (documentation review)
touches:
  - data/documentation/governance.md
---

## Problem

Two statements in the engineering governance page are stale and one of them
contradicts a standing owner ruling. Agents treat this page as mandatory, so
both mislead.

## Evidence

- `data/documentation/governance.md` §5: "**Backend Runtime:** 100% pure Python
  (3.10+)".
  The package requires 3.14: `data/pyproject.toml:12` (`requires-python = ">=3.14"`);
  `data/README.md`, `data/CRAFT_ENGINE.md` and `data/documentation/introduction.md`
  all state Python 3.14+.
- `data/documentation/governance.md:70`: "**Frontend Layer:** Vanilla or vendor
  static `.js` and `.css` assets only. **Zero TypeScript (`.ts`)** and **zero
  Node.js build pipelines**."
  The owner's ruling of 2026-09-17 (workspace `AGENTS.md`, §0.4) permits
  JS/TypeScript, React and a Node-based build for the UI in every project, with
  the constraint that the frontend holds no business rule, money decision,
  tenant resolution, authorization or data access, no Node runtime serves
  requests, and built output ships as static assets. The ruling explicitly says
  a project rule that still forbids TS/React/Node is outdated and must be
  aligned to it.
- `governance.md` §5 also requires "strict static typing (`typing` / `mypy`
  compliant)" while the repository ships no mypy configuration (`mypy.ini` /
  `setup.cfg` absent, no `[tool.mypy]` in `pyproject.toml`, no mypy entry in
  `language-standard.toml`) — the claim is unenforced; verify before keeping it.

## Done when

- [ ] `data/documentation/governance.md` states the real Python floor (3.14+) or
      justifies a different one against `pyproject.toml`.
- [ ] The frontend rule matches the owner ruling of 2026-09-17: JS/TS/React and a
      Node build are permitted for the UI, with the stated boundary (no business
      rule, no Node serving requests, static built output, tooling kept out of
      the production image).
- [ ] The `mypy` claim is either backed by a real configuration or reworded.

## Verify

```bash
grep -n '3\.10+' data/documentation/governance.md   # expect no match
grep -n 'Zero TypeScript\|zero Node' data/documentation/governance.md   # expect no match
python3 .claude/rules/lint_language.py --config language-standard.toml
```

## Notes

The owner ruling is newer and wins over the page (`AGENTS.md` global §0.4: a
project rule that still forbids TS/React/Node is outdated). Fix the page, never
the ruling. Documentation only.

## History

- 2026-10-07T08:09:11Z created by qwen@qwen-code (source: framework audit 2026-10-07)
- 2026-10-07T08:10:00Z claimed by qwen@qwen-code (attempt 1)
- 2026-10-07T08:20:00Z resolved by qwen@qwen-code (resolutions/p2-20261007-080911-governance-python-and-frontend-policy-stale.resolution.md)
