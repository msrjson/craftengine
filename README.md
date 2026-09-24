# Craft Engine — Workspace

Official site: <https://craftengine.org>
Official repository: <https://github.com/msrjson/craftengine>

This is the **orchestration root**, not the application. If you are looking
for the engine's own README (install, CLI, ORM, HTTP, docs index), that
lives one level down at [`data/README.md`](data/README.md) — everything a
running Craft Engine app needs is there.

## Layout

```
.agents/     Agent skills, docs, plans, scripts — read before restructuring anything
.claude/     Claude Code project settings
.git/ .github/  Version control and CI
data/        THE APPLICATION. Mounted 1:1 into the Docker container as /app.
             Editing a file here is live in the running container immediately.
```

**`data/` is the single source of truth for the running application** — it is
what gets deployed, and it is what `docker compose` (run from inside `data/`)
builds and mounts. Nothing outside `data/` is copied into the container image.

AI coding agents should read [AGENTS.md](AGENTS.md) at the workspace root and
[data/AGENTS.md](data/AGENTS.md) before editing the application.

## Cloning this workspace to start a new application

Read `.agents/skills/project/workspace-architecture/SKILL.md` first — it is
the authoritative, step-by-step contract for this (rename the Compose
project, regenerate `.env`, verify the live mount, what never to nest inside
`data/`). This section is a pointer, not a substitute for it.

## For AI agents working in this repository

**Start with [`data/CRAFT_ENGINE.md`](data/CRAFT_ENGINE.md)** — what the engine
is, the build loop for a new feature, how the same codebase carries an
application from a blog to multi-tenant scale, and an explicit list of what is
*not* built yet (storage/S3, mail, API key manager, Redis queue driver). Then:

- `.agents/skills/framework/craft-development/SKILL.md` — framework internals
  (`engine/`, exposed as `craft.*`): what each subsystem owns, what must
  stay framework-agnostic.
- `.agents/skills/project/scaffolding/SKILL.md` — local commands, Docker
  service/port/mount reference.
- `.agents/skills/project/workspace-architecture/SKILL.md` — this workspace's
  physical layout and the clone-to-new-app procedure.
- `.agents/docs/backlog.md` — what's done, what's next, decisions still open.
- Inside `data/`: `documentation/` is the framework reference, `tests/` is the
  executable specification. **Code wins over documentation** — verify in
  `engine/` before trusting a doc page or your own memory of the framework.
