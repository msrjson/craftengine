# Craft Engine - instructions for agents

This repository is the engine, not an application. There is no admin panel,
no login screen, no theme and no demo data to reuse or build on top of. A
fresh project answers exactly one route, `/`, with a starter page meant to be
deleted.

Verify behaviour in the source, never from memory of another framework.
Framework internals live in `engine/` and are imported as `craft.*`. Start with
`README.md` and `documentation/README.md`.

## Starting a project

- `craft new <name>` writes a bare project: configuration, three empty
  providers, one route, the migrations the engine itself needs. Nothing else.
- Add what the project needs, and only that:

  | Command | Writes |
  |---|---|
  | `craft make:auth` | `User` model and migration, login/registration/logout, `config/auth.py` entries |
  | `craft make:admin` | RBAC panel: `Role`/`Permission`/`Group` models, RBAC migration, `/admin/*` screens |
  | `craft make:crud <Entity> --fields=...` | model, migration, request, resource, controllers, views, routes |
  | `craft make:<kind> <Name>` | a single class: `model`, `controller`, `middleware`, `request`, `job`, ... |

- Generated code belongs to the project from the moment it is written. Edit it
  freely; the engine does not read it back.
- Run `craft doctor` after changing routes, views, models or `config/auth.py`,
  and before calling work done. It resolves every route's middleware and
  action, the identity models, every template's directives, the tables the
  models and the engine need, and the translation rows the views use; each
  finding carries a code, a location and the fix. It exits 1 on any error.
  `craft doctor --json` gives the same findings to a script.

## Routes

- Every route a project answers is declared in `routes/web.py` or
  `routes/api.py`. The engine adds only what configuration switches on - the
  health probes, the metrics scrape and the MSR manifest are all off until a
  flag in `config/` turns them on - plus the static file mount.
- `craft route:list` shows every route that answers, the engine's included,
  each marked with its origin. If a path answers and is not in that list, it is
  a defect. Use `craft route:list --json` for paths, names and middleware.
- There is no login route until `craft make:auth` has run. After it, the
  canonical route is `GET /login` (named `login`), credentials go to
  `POST /login`, and `GET /signin` redirects there.

## Identity and access

- The engine resolves `User`, `Role`, `Permission` and `Group` from
  `config/auth.py` under `models`; it never imports `app.Models.*`. Point those
  entries at your own classes, or let `make:auth`/`make:admin` fill them.
- A user model mixes in `craft.auth.models.AuthenticatableMixin` (password
  hashing on every insert path) and `AuthorizableMixin` (`has_role`,
  `has_permission`, `can`). The `role:` and `permission:` route middleware call
  those methods; without them every check denies.
- `auth` on a route means signed in, nothing more. Authorization is a separate
  `role:`, `permission:`, group or Gate check. Inspect `bootstrap/app.py` and
  `engine/http/middleware.py`.

## Data and change safety

- Preserve every database record in every environment. Do not run reset,
  refresh, fresh, wipe, drop, truncate, physical delete, or volume removal.
- Add schema changes through forward migrations only. Never edit or remove a
  migration that has already run somewhere: it breaks the migrations table of
  every database that applied it. Never point tests at an existing database.
- Read `.claude/rules/AGENTS.md` when present and the project governance rules
  before code changes. Code and committed documentation are English; the team
  converses in Portuguese. Add a `CHANGELOG.md` entry for code changes.
- Run relevant tests, `ruff check engine`, and both language gates when the
  local environment supports them. Report any gate that could not run.
