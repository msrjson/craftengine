# Craft Engine application instructions

Craft Engine has Laravel-like ergonomics, but its routes and behavior must be
verified in this Python application's source. Start with `README.md` and
`documentation/README.md`. Framework internals live in `engine/` and are
imported as `craft.*`.

## Authentication and routes

- Read `documentation/authentication.md` and `routes/web.py` before proposing
  a login URL or changing access control.
- The starter application's canonical login route is `GET /login`, with
  credentials submitted to `POST /login`. `GET /signin` only redirects there.
- `Authenticate` resolves the session user globally. A route's `auth` alias
  requires login; authorization needs a separate role, permission, group, or
  Gate check. Inspect `bootstrap/app.py` and `engine/http/middleware.py`.
- Use `python dev.py route list --json` to inspect registered paths, names, and
  middleware. Named route `login` is the stable target for links.

## Data and change safety

- Preserve every database record in every environment. Do not run reset,
  refresh, fresh, wipe, drop, truncate, physical delete, or volume removal.
- Add schema changes through forward migrations and seed only missing reference
  rows. Preserve edited demo data. Never point tests at an existing database.
- Read `.claude/rules/AGENTS.md` when present and the project governance rules before code
  changes. Code and committed documentation are English; the team converses
  in Portuguese. Add a `CHANGELOG.md` entry for code changes.
- Run relevant tests, `ruff check .`, and both language gates when the local
  environment supports them. Report any gate that could not run.
