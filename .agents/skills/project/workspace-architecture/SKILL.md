---
name: craft-workspace-architecture
description: How this workspace is laid out (orchestration root vs. mounted application directory) and what an AI agent must preserve when this repository is cloned to bootstrap a new application.
---

# Craft Workspace Architecture (Project Skill)

This skill governs the **physical layout of the workspace**, not the framework
internals (`craft-framework-development`) or local execution commands
(`craft-project-management`). Read it before moving, renaming, or restructuring
any top-level directory.

---

## 1. The two-tier layout

```
<workspace root>/            Orchestration layer — never mounted in a container
  .agents/                   Agent skills, docs, plans, scripts (this file lives here)
  .claude/                   Claude Code project settings
  .git/  .github/            Version control and CI
  data/                      THE APPLICATION — see below
```

```
data/                        Everything a running Craft app needs. Mounted 1:1
                              into the container as /app. This is the directory
                              you would deploy — it IS production, locally.
  app/  bootstrap/  config/  database/  documentation/
  public/  resources/  routes/  engine/  storage/  tests/
  dev.py  pyproject.toml  Dockerfile  Dockerfile.prod
  docker-compose.yml  docker-compose.prod.yml
  .env  .env.example  README.md
```

**Rule: `data/` is the single source of truth for the running application.**
Nothing that the container needs to run, build, or test may live outside
`data/`. Nothing inside `data/` should assume paths above it.

## 2. Why the split exists

- `docker-compose.yml` (inside `data/`) declares `build: .` and
  `volumes: - .:/app` **relative to its own location** — so the compose
  project root and the bind-mount source are both `data/`, not the workspace
  root. Editing a file under `data/` is reflected in the running container
  immediately, with no rebuild — that is the whole point of the split.
- The orchestration layer (`.agents/`, `.claude/`, `.git/`) carries planning,
  skills, and history that has no business being copied into a container image
  or shipped to production.
- This lets the workspace root stay stable (git history, agent memory, plans)
  while `data/` can be copied wholesale to start a new application — see §3.

## 3. Cloning this repository to start a new application

When an AI agent (or a human) copies this workspace to bootstrap a new app:

1. **Copy `data/` only** — it is the deployable unit. Do not copy `.agents/`,
   `.claude/`, or `.git/` from this repository into the new one; they describe
   *this* project's history, not the new app's.
2. **Do not create a nested `data/` inside the copy.** The copied directory
   *becomes* the new project's `data/` (or, if the new workspace doesn't use
   this two-tier convention, its own root) — never `new-app/data/craft/` or
   any similar re-nesting. If you are unsure whether the target workspace uses
   this convention, ask before restructuring; recreating the split wrong is
   exactly the mistake this skill exists to prevent.
3. **Rename the Compose project.** `docker-compose.yml` pins
   `name: framework` explicitly (the directory name can contain spaces, which
   Compose cannot use to derive a project name). Change it to the new app's
   slug, and update `container_name` for both services so multiple Craft-based
   projects can run side by side without colliding.
4. **Update `pyproject.toml`** (`[project].name`) and `PYTHONPATH`/package
   references only if the internal package layout changes — the framework
   package itself (`engine/`, exposed as `craft.*`) is meant to be reused
   as-is.
5. **Regenerate `.env`** from `.env.example` — never copy a real `.env` (or
   `APP_KEY`) between projects.
6. **Verify the mount, don't assume it.** After `docker compose up -d --build`
   from inside `data/`, edit a harmless file (e.g. append a comment to
   `public/robots.txt`) and confirm `docker exec <container> cat` shows the
   change immediately. If it doesn't, the compose file's build context or
   volume source is pointing at the wrong directory — usually because `data/`
   was copied into a differently-named parent and the relative paths inside
   `docker-compose.yml` still resolve, silently, to the wrong host location.
7. **Clean skeleton for AI agents.** `data/` provides a completely clean
   framework foundation without pre-built domain models or sample blogs.
   `app/modules/` and `app/plugins/` start empty. AI agents must build the new
   domain from scratch, avoiding any hybrid residue or '2 in 1' domain mixing.
   Working reference patterns are provided under `documentation/examples/`.

## 4. What breaks this contract (do not do these)

- Adding application code, migrations, or docs anywhere above `data/`.
- A `docker-compose.yml` or `Dockerfile` outside `data/`, or a second one
  inside `data/` that points back up to the workspace root.
- Symlinking instead of a real bind mount — Compose's relative-path resolution
  and the container's `/app` expectations assume a real directory.
- Committing `data/.env` or any generated `APP_KEY`.
