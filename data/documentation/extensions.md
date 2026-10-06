# Extensions: modules, plugins, themes and connectors

An application grows by adding extensions, never by changing the engine. The
engine is the runtime; each extension is a self-contained unit it discovers,
starts, stops and isolates. When one extension fails, the others keep serving.
The decision and its limits are in `docs/adr/0004-extension-model.md`.
Start with [architecture.md](architecture.md) for the engine/application split,
domain ownership and how to compose a CMS from these pieces.

| Kind | What it is | It may ship |
|---|---|---|
| `module` | A business feature and its screens (contacts, billing, deals) | provider, routes, controllers, services, views, migrations, translations, assets |
| `plugin` | A cross-cutting capability (audit trail, pricing adjustments, document validation) | the same as a module |
| `theme` | Presentation only | views that override others, assets, translations |
| `connector` | A headless integration with an outside service | provider, services, migrations, translations, optional webhook `routes.py`; never views or assets |

Module and plugin use the same runtime and contribution permissions. Choose
between them by responsibility: a module owns a business domain; a plugin
adds a capability or adjusts behavior through explicit extension points.

## Where extensions live

`config/extensions.py` lists the roots, relative to the application:

```python
paths = ["app/modules", "app/plugins", "app/themes", "app/connectors"]
```

Every directory directly under a root that holds an `extension.toml` is one
extension. The engine never names these paths itself.

## Create one

```bash
python dev.py make module sales_pipeline     # app/modules/sales_pipeline/
python dev.py make screen sales_pipeline deals
python dev.py make plugin member_pricing     # app/plugins/member_pricing/
python dev.py make theme sunrise             # app/themes/sunrise/
python dev.py make connector payments        # app/connectors/payments/ (client, delivery log, no UI)

python dev.py extension install sales_pipeline
python dev.py extension activate sales_pipeline
```

A generated module is complete: it installs, activates and renders as it is.
`make screen` adds a thin controller, a namespaced view, the route and the
title key in `en`, `pt-BR` and `es`.

## Anatomy

```text
app/modules/sales_pipeline/
├── extension.toml          the manifest - the whole contract with the engine
├── provider.py             register(context): bindings, listeners, filters, proxy exposures
├── routes.py               register(router): the module's routes
├── controllers/            thin HTTP layer
├── services/               business rules
├── views/                  rendered as sales_pipeline::<path>
├── migrations/             run on install, forward-only
├── lang/catalog.json       keys prefixed with the slug, in en, pt-BR and es
└── assets/                 served at /extensions/sales_pipeline/<path>
```

### The manifest

```toml
slug = "ordering"                    # unique; also the view namespace and key prefix
kind = "module"                      # module | plugin | theme | connector
version = "1.0.0"
engine = ">=4.3,<5"                  # engine versions it runs on
name_key = "ordering.extension.name" # translation key of its name

[requires]
catalog = ">=1.0,<2"                 # other extensions it needs
```

A range is comma-separated clauses that must all hold: `>=`, `<=`, `>`, `<`,
`==`, `!=`. A manifest that is malformed, duplicates a slug, or ships what its
kind may not (a theme with `routes.py`) is refused at discovery with a code;
the other extensions are discovered anyway.

### The provider

Everything goes through the `ExtensionContext` the provider receives, never
through the global objects, so deactivation can undo it in the running process:

```python
from .services.catalog_service import CatalogService


def register(context):
    context.app.singleton(CatalogService, lambda c: CatalogService(c))
    context.expose("catalog", CatalogService, {"price_cents"})   # internal proxy
    context.listen("order.placed", reserve_stock, priority=5)    # events
    context.filter("catalog.price_cents", round_to_cents)        # filters
```

| Method | Does | On deactivation |
|---|---|---|
| `context.app.bind/singleton/scoped/instance(...)` | registers a service owned by this extension; existing keys are refused | binding and cached instances removed |
| `context.app.alias(abstract, alias)` | reserves an unused alias | removed |
| `context.expose(alias, service, methods)` | exposes methods on the internal proxy, owned by this extension | withdrawn |
| `context.listen(event, listener, priority=10)` | listens to an event; lower priority runs first | removed |
| `context.filter(name, callback, priority=10)` | transforms a value passed to `apply_filters(name, value, ...)` | removed |
| `context.on_unload(callable)` | registers your own undo step | called |

`context.app` is an ownership-aware container wrapper. Resolution and other
application operations delegate to the application; these five registration
methods record undo steps. A collision raises `EXTENSION_BINDING_CONFLICT`
and failed activation rolls back registrations already made. Do not bypass
the wrapper by obtaining the global container to register contributions.
Custom side effects need an explicit undo step. Existing references held by
running requests are not revoked when a binding is removed.

### Routes

```python
def register(router):
    router.get("/catalog/{sku}", [ProductController, "show"]).name("catalog.show")
```

The engine tags every route with the extension's slug. While the extension
cannot serve, its routes answer with a typed error instead of running.

A route another one already answers (same method and path) is refused at
activation with `EXTENSION_ROUTE_CONFLICT`, naming the method and path, and the
extension is marked failed. When an application route and an extension route
clash anyway - the extension was loaded first, at boot - the application's
route wins and the clash is logged as `route_conflict`; load order never decides.

## Extensions talk only through seams

An extension never imports another extension's code. The boundary gate
(`tools/check_engine_boundary.py`, rule `EXTENSION_CROSS_IMPORT`) fails the
build when one does. The seams are:

- **the internal proxy** for a synchronous answer - `Proxy.call("catalog",
  "price_cents", sku)` (see [internal-proxy.md](internal-proxy.md));
- **events** for reactions - `context.listen(...)` on one side,
  `app.make("events").dispatch(...)` on the other;
- **filters** to let others adjust a value - `apply_filters(name, value)` on
  one side, `context.filter(name, callback)` on the other.

## Lifecycle

```text
discovered -> installed -> active <-> inactive -> uninstalled
                              \-> failed
```

| Command | Does | Refused when |
|---|---|---|
| `extension install <slug>` | runs its migrations, seeds its translations | already installed; engine out of range; a dependency not installed; a catalog key without the slug prefix or missing a locale |
| `extension update <slug>` | applies pending migrations and missing translations from deployed code, records its version, preserves installed/inactive state | not installed/inactive; downgrade; changed kind; incompatible engine/dependencies/dependents |
| `extension activate <slug>` | loads it; every worker follows within `reconcile_interval` seconds | not installed; a dependency not active at a compatible version |
| `extension deactivate <slug>` | undoes its contributions, in the running process | an active extension depends on it |
| `extension uninstall <slug>` | marks it uninstalled; **its tables, rows and translations stay** | still active; an installed extension depends on it |
| `extension list` / `extension status <slug>` | state, health, circuit breaker, last error | - |

State lives in the `extensions` table, so the CLI, the management panel and
every worker agree.

The new ownership/update refusal messages are seeded by
`2026_10_06_000004_seed_extension_update_messages.py`. New generated projects
include it. Existing projects that upgrade only the installed engine package
must add a new application migration and apply it through their normal
forward-migration deployment process; engine package updates do not copy new
skeleton migrations into an existing project. The migration body is:

```python
from craft.extensions.messages import seed_messages
from craft.facades import DB


def up() -> None:
    seed_messages(DB)
```

This inserts missing keys in `en`, `pt-BR` and `es`, preserving edited rows.
Do not edit or rerun an already applied migration to seed new messages.

Status reports `version` from the manifest, `installed_version` from the
store and `update_required` when their version or kind differs. Activation,
boot and reconciliation refuse an unapplied version. State changes such as
deactivation never overwrite the recorded installed version.

### Updating an installed extension

`extension update` applies code already present on disk. It does not acquire
packages or reload imported Python modules. Use this sequence:

1. Deactivate active dependents first, then the extension. Wait for workers to
   reconcile; drain requests/jobs and stop the workers that use its code.
2. Deploy the new extension files. Keep the slug and kind; preserve previously
   applied migrations and add new forward migrations. Check configuration and
   any shared service/event/filter contracts.
3. In a fresh CLI process, run `python dev.py extension update <slug>`.
4. Restart application and background workers with the deployed code.
5. In a fresh CLI process, activate dependencies first, then the extension and
   its dependents. Verify status and the application's behavior.

The update validates compatibility and the catalog before applying migrations.
It rejects a lower version and incompatible installed dependents, including
inactive ones. Dependency ranges are checked against installed versions,
not merely files placed on disk. A same-version update is allowed to apply
pending migrations or newly added translation keys and is safe to repeat.
Restart after code changes even if the version string did not change.

An update does not reactivate the extension. The manager that applied it
refuses activation with `EXTENSION_RESTART_REQUIRED`; a worker that previously
imported a different version also requires restart. Do not rely on constructing
a new manager in the same Python process to reload extension code.

On failure, the installed version is unchanged. Already successful migrations
and inserted translations remain: there is no destructive rollback. Correct
the failure, rerun the update, and leave the extension stopped until verified.

`make screen` changes source files; it is not a live deployment command. For an
installed module, use this update procedure instead of reinstalling it.

## When an extension fails

Each extension runs behind its own error boundary:

| Failure | Effect |
|---|---|
| raises while loading | marked `failed`; the application boots without it |
| a listener raises | logged with the slug and skipped; the event's other listeners run |
| a filter raises | logged; the value passes through unchanged |
| a route raises | that request answers 500; nothing else is affected |
| `failure_threshold` unexpected failures in `failure_window` seconds | the circuit breaker opens: its routes answer 503 `EXTENSION_UNAVAILABLE`, its proxy targets raise `INTERNAL_TARGET_UNAVAILABLE` without running, its listeners are skipped |
| `cooldown` seconds later | one trial call goes through; success puts it back in service |

A typed domain error - an exception with a `code` and a status below 500, such
as "product not found" - is the extension working, and never counts as a
failure. The thresholds live in `config/extensions.py`.

The isolation is in-process. It contains what an extension raises; it does not
stop one that loops forever or exhausts memory. ADR 0004 records that limit.

## Views and themes

`View.render("catalog::products.show", data)` renders
`app/modules/catalog/views/products/show.forge.py`. A theme overrides any view
by path:

| View | Theme file that overrides it |
|---|---|
| `layouts.app` | `app/themes/<theme>/views/layouts/app.forge.py` |
| `catalog::products.show` | `app/themes/<theme>/views/catalog/products/show.forge.py` |

Select the theme with `VIEW_THEME=<slug>` (`config/view.py`), or per request
with a resolver the application owns - the engine never resolves a tenant:

```python
app.make("view").set_theme_resolver(lambda: current_brand_theme())
```

Install and activate the theme before selecting it. Several themes may be
active/available; the setting or resolver chooses one for rendering. Activation
alone does not change the selection.

Assets: `{{ asset('catalog::css/catalog.css') }}` renders
`/extensions/catalog/css/catalog.css`, served only while the extension serves.

## Translations

`lang/catalog.json` maps each locale to the extension's keys, all prefixed
with its slug:

```json
{
  "en": {"catalog.extension.name": "Catalog"},
  "pt-BR": {"catalog.extension.name": "Catálogo"},
  "es": {"catalog.extension.name": "Catálogo"}
}
```

Install writes the rows the translation store lacks; a row an operator edited
is never overwritten.

## Legacy plugins

`plugins/<slug>/plugin.py` with a `PLUGIN` dict and `register(app)` still
loads through `PluginManager` (see [plugins.md](plugins.md)). It is
deprecated: new capabilities are `plugin` extensions.
