# Extensions: modules, plugins and themes

An application grows by adding extensions, never by changing the engine. The
engine is the runtime; each extension is a self-contained unit it discovers,
starts, stops and isolates. When one extension fails, the others keep serving.
The decision and its limits are in `docs/adr/0004-extension-model.md`.

| Kind | What it is | It may ship |
|---|---|---|
| `module` | A business feature and its screens (contacts, billing, deals) | provider, routes, controllers, services, views, migrations, translations, assets |
| `plugin` | A cross-cutting capability (audit trail, pricing rules, a payment gateway) | the same as a module |
| `theme` | Presentation only | views that override others, assets, translations |

## Where extensions live

`config/extensions.py` lists the roots, relative to the application:

```python
paths = ["app/modules", "app/plugins", "app/themes"]
```

Every directory directly under a root that holds an `extension.toml` is one
extension. The engine never names these paths itself.

## Create one

```bash
python dev.py make module sales_pipeline     # app/modules/sales_pipeline/
python dev.py make screen sales_pipeline deals
python dev.py make plugin member_pricing     # app/plugins/member_pricing/
python dev.py make theme sunrise             # app/themes/sunrise/

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
kind = "module"                      # module | plugin | theme
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
| `context.expose(alias, service, methods)` | exposes methods on the internal proxy, owned by this extension | withdrawn |
| `context.listen(event, listener, priority=10)` | listens to an event; lower priority runs first | removed |
| `context.filter(name, callback, priority=10)` | transforms a value passed to `apply_filters(name, value, ...)` | removed |
| `context.on_unload(callable)` | registers your own undo step | called |

### Routes

```python
def register(router):
    router.get("/catalog/{sku}", [ProductController, "show"]).name("catalog.show")
```

The engine tags every route with the extension's slug. While the extension
cannot serve, its routes answer with a typed error instead of running.

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
| `extension activate <slug>` | loads it; every worker follows within `reconcile_interval` seconds | not installed; a dependency not active at a compatible version |
| `extension deactivate <slug>` | undoes its contributions, in the running process | an active extension depends on it |
| `extension uninstall <slug>` | marks it uninstalled; **its tables, rows and translations stay** | still active; an installed extension depends on it |
| `extension list` / `extension status <slug>` | state, health, circuit breaker, last error | - |

State lives in the `extensions` table, so the CLI, the management panel and
every worker agree.

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
