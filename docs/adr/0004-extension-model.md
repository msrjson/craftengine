# ADR 0004 — One extension model: modules, plugins and themes

- **Status:** accepted (owner, 2026-10-05)
- **Date:** 2026-10-05
- **Follows:** ADR 0003
- **Scope:** how an application grows without rebuilding the engine - what an
  extension is, how it is found, started, stopped and isolated, and how it
  talks to the rest

## Context

ADR 0003 decided that modules, plugins and themes come and go without
touching the engine, and that modules talk through the internal proxy and
events. The code did not deliver it: plugins were a `PLUGIN` dict under
`data/plugins/`, modules were a row of state with nothing to load, themes did
not exist, every view, migration, translation and asset was global, and
nothing stopped one module from importing another. A plugin that was disabled
kept running until the process restarted.

The owner's goal is an engine that behaves like a container runtime: the
engine is the runtime, each extension is a unit it runs. When one unit fails,
the others keep serving. A company that needs to expand the application adds
units; it never rebuilds the engine.

## Decision

1. **One manifest, three kinds.** Every extension is a directory with an
   `extension.toml` naming its `slug`, `kind`, `version`, the `engine` range it
   supports, a `name_key` translation key and the extensions it `requires`.

   | kind | contributes |
   |---|---|
   | `module` | business features and screens: provider, routes, services, views, migrations, translations, assets, listeners and filters |
   | `plugin` | a cross-cutting capability: the same contributions as a module |
   | `theme` | presentation only: views that override others, assets, translations |

   A manifest whose directory contributes something its kind may not (a theme
   with `routes.py`) is refused.

2. **Extensions live in the application.** `data/app/modules/`,
   `data/app/plugins/` and `data/app/themes/`. The engine never names these
   paths: the application lists its roots in `config/extensions.py`
   (`extensions.paths`), so EB-02 holds.

3. **A lifecycle with persisted state.** `discovered → installed → active ⇄
   inactive → uninstalled`, plus `failed`. Install runs the extension's own
   migrations and seeds its translations. Activation checks the engine range
   and that every dependency is active at a compatible version. Deactivation is
   refused while an active extension depends on it. Uninstall never deletes
   data (NR-02): tables and rows stay.

4. **Every contribution goes through the extension's context.** An extension
   registers listeners, filters, routes and proxy exposures through the
   `ExtensionContext` it receives, never on the global objects directly. The
   manager records each contribution, so deactivation undoes all of them in
   the running process - disabled means not running, without a restart.

5. **Fault isolation per extension.** Each extension has its own error
   boundary and circuit breaker:
   - a failure while it boots marks it `failed`; the application boots without it;
   - a failing listener or filter is logged with the slug and skipped - a filter
     passes its input through unchanged;
   - a failing route answers for that extension only;
   - after `failure_threshold` unexpected failures inside `failure_window`
     seconds the breaker opens: the extension's routes answer 503
     `EXTENSION_UNAVAILABLE`, its proxy targets are refused with
     `INTERNAL_TARGET_UNAVAILABLE`, its listeners are skipped. After
     `cooldown` seconds one trial call is let through; success closes the
     breaker.

   Typed domain errors (an exception carrying a `code` and a status below 500)
   are the extension working, and never count as failures.

6. **Extensions never import each other.** The boundary gate refuses
   `EXTENSION_CROSS_IMPORT`: a file under one extension importing another
   extension's package. Synchronous needs go through the internal proxy, whose
   exposures are owned by an extension and disappear with it; reactions go
   through events.

7. **Views resolve through a chain.** `slug::path.view` names a view of an
   extension. The active theme overrides first, then the extension, then
   `resources/views`. The theme comes from configuration (`view.theme`) or a
   resolver the application registers; the engine never resolves a tenant
   (EB-06).

## Limits, stated plainly

The isolation is in-process. The engine catches what an extension raises; it
cannot stop an extension that loops forever, exhausts memory or crashes the
interpreter. Process-level isolation needs an extension running out of
process, which the internal proxy is positioned to reach later through a
pluggable transport, without changing any caller. That transport is not built
by this decision.

The circuit breaker is per worker process: each worker learns about a failing
extension from its own failures.

## Consequences

- A new business capability is a new directory and two CLI commands
  (`extension install`, `extension activate`), or a click in the extension
  manager panel - never an engine change.
- `PluginManager` and `ModuleManager` keep their public API for one release as
  adapters over the extension store, then follow the deprecation path in
  `CHANGELOG.md`.
- The extension manager panel is itself a module: it gets no privilege the
  CLI does not have, and if it fails the application keeps serving.

## Amendment 2026-10-06 — a fourth kind, `connector`

Owner order: the reference application must stress the whole extension model,
so an integration with an outside service gets its own kind instead of
hiding in a module.

| kind | contributes |
|---|---|
| `connector` | a headless integration: provider, services, migrations, translations and optionally `routes.py` for inbound webhooks. No `views`, no `assets` - the manifest is refused with `EXTENSION_KIND_CONTRIBUTION_FORBIDDEN` |

Its root is `app/connectors`. `make:connector <slug>` generates it with an
injectable transport (no network until the application wires one), an
append-only delivery log table and a proxy exposure. `make:module` now also
ships a model and a migration creating `<slug>_records`: a module is born
with its schema. Lifecycle, isolation and the no-cross-import rule are
unchanged.
