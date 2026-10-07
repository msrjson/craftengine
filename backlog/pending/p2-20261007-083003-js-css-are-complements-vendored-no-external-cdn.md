---
id: "20261007-083003"
title: Record the owner policy: Python is the codebase, JS/CSS libraries are vendored complements, no external CDN
type: decision
priority: 2
autonomous: false
blocked_by: owner-decision
max_attempts: 2
attempts: 0
created_at: 2026-10-07T08:30:03Z
updated_at: 2026-10-07T08:30:03Z
source: owner ruling 2026-10-07, relayed in session
touches:
  - data/documentation/governance.md
  - .claude/rules/RELEASE_NON_REGRESSION_STANDARD.md
  - data/documentation/deployment.md
---

## Problem

The owner's policy of 2026-10-07 has three parts that no single rule states:
Python is the official codebase; JavaScript **and CSS** third-party libraries
are allowed as complements; and the framework is agnostic - it **packages**
those libraries and never depends on an external CDN to serve an application.
`governance.md` now allows JS/TS for the UI, but `NR-07` still says "zero Node.js
or TypeScript build toolchains", and nothing states the vendoring/no-CDN rule.

## Evidence

- Owner, 2026-10-07: "JS libraries may be used as plugins, but the official
  codebase is Python; we use third-party libraries as a complement"; "the same
  for CSS libraries"; "the framework must be agnostic: it packages, but does not
  depend on an external CDN to serve the applications".
- `.claude/rules/RELEASE_NON_REGRESSION_STANDARD.md`, NR-07.1 - "Craft Engine is
  100% Python 3.14+; zero Node.js, Webpack, or TypeScript build toolchains."
- `data/documentation/governance.md` §5 - already aligned to the 2026-09-17
  ruling (JS/TS/React permitted for the UI, with the boundary).
- Global rule `~/.claude/agent-team/AGENTS.md` §0.4 - "JavaScript is a support
  layer, never the codebase"; the codebase is Python on Craft Engine.

## Done when

- [ ] `NR-07` and `governance.md` say the same thing: Python is the codebase;
      JS/TS and CSS libraries are permitted as complements, with the no-business-
      rule / no-Node-serving-requests boundary.
- [ ] The vendoring rule is written down where a developer will find it: a
      dependency is packaged with the application (no external CDN at runtime),
      in `governance.md` and, if it is a deployment concern, `deployment.md`.
- [ ] The owner confirms the wording, since `.claude/rules/` is re-provisioned
      from a global source and a change there can be overwritten.

## Verify

```bash
grep -n 'Node.js\|TypeScript' .claude/rules/RELEASE_NON_REGRESSION_STANDARD.md data/documentation/governance.md
grep -rn -i 'cdn' data/documentation/governance.md data/documentation/deployment.md
```

## Notes

`ENGINE_BOUNDARY.md` records that files under `.claude/rules/` are re-provisioned
from a global source and would lose an added section - so a durable statement may
belong in a project-owned document (`data/documentation/governance.md`) with NR-07
corrected at the source. `autonomous: false` until the owner confirms the wording
and whether the global standard changes.

## History

- 2026-10-07T08:30:03Z created by qwen@qwen-code (source: owner ruling 2026-10-07)
