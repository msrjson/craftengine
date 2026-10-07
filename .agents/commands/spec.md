---
description: Start spec-driven development — write a structured specification, architecture included, before any code
argument-hint: [feature or project idea]
---

Apply the `spec-driven-development` skill (`.claude/skills/spec-driven-development/SKILL.md`).

$ARGUMENTS

Start by understanding what the user wants to build. Ask clarifying questions, one
at a time, about:

1. The objective and the target users
2. Core features and acceptance criteria
3. Constraints: Craft Engine version, plugins or optional extras involved, whether
   personal data is processed (LGPD/GDPR)
4. Known boundaries (what to always do, what to ask about first, what to never do)

State your assumptions explicitly before writing anything and let the user correct them.

Then confirm the **architecture before any domain code**: which business modules,
domain services, plugins (resolved from the container), models and migrations are
involved, and the shape of the data. Get that shape approved.

Then write the spec covering all six core areas: objective, commands
(`python dev.py ...`, `python -m pytest tests`, the gates in `.claude/rules/`),
project structure, code style, testing strategy, and boundaries. Include the
personal data section and the list of new translation keys with `en`, `pt-BR` and
`es` values.

If the request bundles several independently testable capabilities, first propose
a capability map (module ids, dependency direction, build order) per the skill's
Phase 0, get it approved, save it as `.agents/plans/CAPABILITY-MAP.md`, then spec
each module in dependency order as `.agents/plans/SPEC-<module-id>.md`.

Otherwise save the spec as `.agents/plans/SPEC.md` at the repository root. Specs
never go inside `data/`. Confirm with the user before proceeding to `/plan-tasks`.
