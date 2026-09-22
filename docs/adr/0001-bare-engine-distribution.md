# ADR 0001 — The distributed framework is the bare engine

- **Status:** accepted
- **Date:** 2026-09-22
- **Supersedes:** nothing
- **Scope:** what a developer downloads, how a new project starts, how the
  presentation site and the framework are built and published

## Context

Craft Engine ships as a repository that *is* an application. A developer who
downloads it, or an AI coding agent asked to start a project with it,
inherits:

- 12 controllers under `app/Http/Controllers/` (Admin, Auth, Docs, Panel)
- 21 models under `app/Models/`, of which the engine genuinely needs one
- 3,116 lines of Forge views under `resources/views/`
- 1,654 lines of theme CSS and JS under `public/assets/`
- roughly 30 routes in `routes/web.py`, most of them `/admin/*` and `/panel/*`
- a presentation landing page and a documentation site

Nothing in the tree marks which of these is the engine and which is a
demonstration. The observed failure follows: an agent starting a new project
cannot tell what it is supposed to reuse, so it either rebuilds what already
exists or grafts its feature onto a demo layout that was never meant to
survive. The framework acquired the shape of a content management system when
it was meant to be an engine.

Three couplings make the demonstration structurally load-bearing rather than
merely present:

1. `engine/cli/app.py` imports `app.Models.{Role,Permission,Group,User}` in
   roughly twenty places across the `role:*`, `permission:*`, `group:*` and
   `user:*` commands. The engine cannot run its own CLI without the
   application's models.
2. `bootstrap/app.py` imports `PanelServiceProvider`, `DatabaseLoggingMiddleware`
   and `TenantMiddleware` unconditionally. Booting requires the admin panel to
   exist, and the tenant middleware is imported even with multi-tenancy off.
3. `engine/auth/manager.py` defaults to the string `"app.Models.User.User"`.

A fourth problem is invisible rather than structural: the engine attaches
`StarletteRoute` objects directly to the kernel — the MSR manifest at
`/.well-known/msr.json`, the health endpoints, and the static file mount.
`route:list` iterates `router.routes` and never sees them. Routes exist,
answer requests, and do not appear in the tool a developer uses to find out
which routes exist.

## Decision

### 1. Two products, two repositories, two containers

| Product | Repository | Visibility | Contents |
|---|---|---|---|
| Framework | `msrjson/framework` | **public** | The bare engine. What a developer downloads. |
| Workspace | `msrjson/craftengine` | **private** | Development monorepo: engine under development, the demo application as an example, deployment and container orchestration. |
| Site | `msrjson/craftengine.org` | private | The craftengine.org presentation site. |

`msrjson/framework` is created with an **orphan history**: a clean initial
commit of the already-cleaned engine. It is not a filtered mirror of
`craftengine`. The reason is that `craftengine` is public today and is being
made private; publishing a new repository that carries its history would
re-publish exactly what the privatization is meant to withdraw, and would
require auditing every historical commit for secrets first.

Making `craftengine` private does not retroactively unpublish it. Existing
forks, clones and third-party archives are unaffected. Privatization limits
future access; it is not a remediation for anything already disclosed.

The two containers are composed at the workspace root: `website` builds and
serves the static site, `framework` runs the engine. They are kept apart in
development because a change that requires rebuilding both has crossed a
boundary that should not be crossed.

### 2. The engine owns contracts; the application owns concretes

`engine/auth/` gains abstract bases — an authenticatable contract and a
role-holding contract. The concrete `User` model is emitted by
`craft make:auth` into the application, not shipped in the engine.

The engine therefore stops importing `app.*`. The RBAC CLI commands resolve
their models through `config/auth.py`, and the command group registers only
when those models exist.

### 3. A new project starts from a generator, not from this repository

`craft new <name>` writes a minimal project: configuration, providers with
empty bodies, one route, the migrations the engine itself needs, and nothing
else. There is no admin panel, no theme, no demo seeders, no views beyond a
single starter page.

The admin surface is not deleted — it is demoted from *present by default* to
*generated on request*, as `craft make:auth` and `craft make:crud` already
work. `craft make:admin` emits the four admin controllers and six Forge views
and registers their routes using the marker-and-token append strategy that
`crud_builder._append_web_route` already implements.

### 4. Zero theme, zero phantom routes

The skeleton ships no CSS and no reusable layout. Generator stubs stop
emitting `@extends("layouts.app")` and framework-specific utility classes, so
generated code carries no dependency on a theme that is not there.

The starter page answers `/` with the Craft Engine wordmark in block
characters, brand orange on dark slate, and the version stamp. It is a single
self-contained view with inline styling and no layout to extend: a developer
deletes one file and the page is gone. It exists to prove the installation
boots, not to be built upon.

`route:list` is extended to report engine-attached routes alongside declared
ones, marked as engine-owned. A route that answers requests and does not
appear in `route:list` is a defect, regardless of who registered it.

### 5. Versioning

The semantic version stays at `3.23.0`; the release counter advances
`r00016` → `r00017`. Removing the demonstration application is a breaking
change for any project depending on `app.Models.Role` or the `/admin/*`
routes, which would ordinarily argue for `4.0.0`. The project is published as
`Development Status :: 3 - Alpha` with no known external consumer, and the
owner has elected to advance the release counter only. NR-01 permits this:
the counter is monotonic regardless of the semantic bump.

## Consequences

### Accepted costs

- Six test files that exercise the demo application are removed or become
  generator tests: `test_panel`, `test_admin_authorization`,
  `test_identity_and_rbac_lifecycle`, `test_auth_route_contract`,
  `test_multi_tenancy_default`, and two tests in `test_docs_site`.
- Nineteen further test files use `app.Models.User` as a convenient subject
  while testing engine behavior. They move to a test-owned model or to the
  model the auth generator emits.
- The public history of the first sixteen releases stays in the private
  workspace and does not appear in the public repository.
- A developer who wants an admin panel runs one command instead of finding it
  already there.

### Retained

- The RBAC admin surface, the authentication scaffolding and the CRUD builder
  all survive as generators. Nothing of substance is deleted; the default
  changes from opt-out to opt-in.
- The brand palette survives in `engine/support/branding.py` even though the
  theme does not.

### Follow-on work not covered here

- The migration `2025_01_01_000004_framework_dynamic_tables.py` mixes engine
  concerns (`translations`, `settings`) with RBAC (`roles`, `permissions`,
  `role_user`, `permission_role`) in one file and must be split before the
  skeleton can have internationalization without inheriting RBAC.
- `TranslationSeeder` seeds four locales — `en`, `pt`, `pt-BR`, `es`. The
  European `pt` alongside `pt-BR` is the drift that the governance file
  requires to be collapsed into `pt-BR`.
- `auth_scaffolder.register_auth_routes` returns an empty string when
  `routes/web.py` is absent, so the first scaffold registers nothing and the
  second cannot detect that authentication is configured. It is masked today
  because this repository always has the file; a project generated by
  `craft new` walks exactly that path.
