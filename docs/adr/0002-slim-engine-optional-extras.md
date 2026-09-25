# ADR 0002 — The engine is slim: non-core subsystems become optional extras

- **Status:** accepted (owner, 2026-09-25); not yet implemented
- **Date:** 2026-09-25
- **Supersedes:** nothing; follows ADR 0001
- **Scope:** which subsystems a project gets by default, how the rest are
  installed and switched on, and the order in which they move

## Context

ADR 0001 removed the *application* from the distribution. It did not remove
the weight of the *engine*: a bare project still registers every subsystem
the framework has ever shipped, and `pyproject.toml` still called it
"batteries-included". The backlog item P3 asked the owner to choose between a
bare engine and a batteries-included one. The owner chose **slim**.

Sizing taken on 2026-09-25 at v4.1.0-r00019 (read-only survey of `engine/`):

| Measure | Now |
|---|---|
| Providers registered by default | 24 (`engine/providers/engine_providers.py:61-97`) |
| Container keys | 35 |
| Facades | 36 |
| Engine source | 31,871 lines of Python in 154 files |
| Core dependencies | 14 (`pyproject.toml:38-64`) |

Facts that shape the decision:

1. Every subsystem is already a lazy singleton, so runtime cost is close to
   zero. The real gains are **dependencies** and **public surface**, not
   memory or boot time.
2. Two core dependencies are dead or misplaced: `fastapi` is imported
   nowhere; `faker` appears only inside the text of the `make:factory` stub.
   `boto3`, used by the S3 storage driver, is declared nowhere.
3. `pillow` is required by every HTTP application by accident:
   `engine/http/middleware.py:961` imports the firewall at module level, which
   runs `engine/security/__init__.py`, which imports the captcha eagerly, which
   imports `PIL` at the top of `engine/security/captcha.py`.
4. The project's `PluginManager` discovers `plugins/<slug>/plugin.py` inside
   a *project* and keeps state in the database (`engine/plugins/manager.py`).
   It is not a vehicle for engine subsystems.
5. Governance pins part of the list: NR-05 names the `Firewall`, `Honeypot`,
   `AntiSpam` and `Image` facades and the `antispam`/`firewall` container keys;
   NR-06 requires `@honeypot`/`@antispam` on public forms, and the sign-in form
   `make:auth` generates uses them.

## Decision

1. **An optional subsystem is an extra of the same package.** Its code stays
   in `craft.*`; its provider leaves the default list in
   `engine_providers.py`; its third-party dependency moves to
   `[project.optional-dependencies]`; a project that wants it installs the
   extra and registers the provider explicitly in `bootstrap/app.py`.
   Separate distributions are not ruled out, but are not the first step.
2. **Facades stay importable** (NR-05). A facade whose provider is not
   registered raises a named diagnostic from
   `engine/support/diagnostics.py` - which extra to install and which provider
   to register - instead of the container's generic "not bound".
3. **Each move goes through one deprecation release**: the first release keeps
   the provider registered and emits a `DeprecationWarning` naming the extra;
   the next removes it from the default list. One subsystem per commit, each
   with its CHANGELOG entry.
4. **What stays in core:** HTTP, routing, ORM and migrations (vector search
   included - it is persistence grammar, not a package), Forge, validation,
   auth, sessions and CSRF, Firewall/Honeypot/AntiSpam (until NR-05/NR-06 are
   amended), Queue, Cache, Schedule, Modules/Plugins/Settings, observability
   (metrics, health, logging), Vault and Signer.

## Plan, lowest risk first

| Step | What | Breaking | Effect |
|---|---|---|---|
| 0 | Remove `fastapi`; move `faker` to `dev`; declare `s3 = ["boto3"]`; make the captcha, `security/__init__.py` and the firewall import in `http/middleware.py` lazy | no | 14 -> 12 core dependencies; unblocks `pillow` |
| 1 | PQC (113 lines, stdlib, already behind a flag) | provider only | -1 provider |
| 2 | AI (793) + Agents/MCP (269); `httpx` is already an extra | provider only | -2 providers |
| 3 | Docs builder (529) and MSR manifest (408); `markdown-it-py` becomes the `docs` extra | CLI commands | -1 core dependency |
| 4 | Mail (431) and Storage (377) | provider only | -2 providers |
| 5 | Datagrid (491): deprecate the re-export in `engine/http/__init__.py` | import path | - |
| 6 | Media (732) + Captcha (144) together; `pillow` becomes the `media` extra | NR-05 names `Image` | -2 providers, -1 core dependency |
| - | Firewall, Honeypot, AntiSpam | only after amending NR-05/NR-06 | - |

After steps 0-6: 24 -> 17 default providers, 35 -> 27 container keys, 14 -> 10
core dependencies (9 if `cryptography` follows Vault into an extra), about
4,300 lines (13.5%) off the default path. The facade count stays 36.

## Consequences

- `pyproject.toml` stops describing the framework as batteries-included.
- `craft new` projects get fewer providers; generated code must not depend on
  an optional one. `make:auth` depends on AntiSpam and Honeypot, which stay.
- `craft doctor` gains a check: a facade used in the project whose provider is
  not registered.
- The documentation gets one page listing each extra, what it enables and the
  provider line to add.
- A project upgrading across a removal must add the extra and the provider;
  the deprecation release tells it exactly what to add.

## Alternatives considered

- **Batteries-included, no change.** Rejected by the owner: the comparison
  with a micro-framework does not hold while 24 subsystems load by default.
- **Separate distributions per subsystem now.** More packaging, versioning and
  CI for the same user-visible result; deferred until an extra proves it needs
  its own release cycle.
- **The project `PluginManager`.** Built for project plugins with database
  state, not for engine subsystems; using it would couple the core's boot to a
  database table.
