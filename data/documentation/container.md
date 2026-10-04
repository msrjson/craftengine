# Service Container

The container resolves dependencies, holds the application's singletons, and
autowires constructors from type annotations.

## Binding

```python
# `app` is the Application built in bootstrap/app.py
app.bind("mailer", lambda c: Mailer(c.make("config")))   # new instance each time
app.singleton("mailer", lambda c: Mailer())              # built once, reused
app.instance("mailer", existing_mailer)                  # register an object
app.alias("mailer", "mail")                              # second name
```

Resolve with `make`:

```python
mailer = app.make("mailer")
```

An unbound string raises `KeyError` — the container never silently returns
`None`.

## Autowiring

A class with annotated constructor parameters is built without registration:

```python
class Engine: ...
class Wheels: ...

class Car:
    def __init__(self, engine: Engine, wheels: Wheels):
        self.engine = engine
        self.wheels = wheels

car = app.make(Car)          # Engine and Wheels resolved automatically
```

Override any parameter explicitly:

```python
app.make(Car, {"engine": my_engine})
```

If a parameter cannot be resolved and has a default, the default is used.
Otherwise resolution raises rather than passing `None`.

## The global instance

Facades, models and helpers reach the container through
`Container.getInstance()`. The booted application claims that slot.

```python
from craft.container.application import Application, Container

app = Application(base_path)             # claims the global if no app holds it
Application(base_path, bind_as_global=False)   # never claims it
Application(base_path, bind_as_global=True)    # always claims it
```

The default (`None`) claims the global unless another `Application` already
holds it. A bare fallback `Container` is always displaced.

> Constructing a container does **not** claim the global. It used to, which
> meant building a second one anywhere — a test fixture, a worker, a tenant
> scope — silently repointed every `getInstance()` call in the process.

Swap it temporarily with guaranteed restoration:

```python
with Container.scoped_instance(tenant_app):
    ...   # facades and models resolve from tenant_app
```

Not to be confused with `scoped()`, which registers a request-scoped binding.

## What the framework binds

| Key | Object |
|---|---|
| `app` | The `Application` itself |
| `config` | `ConfigRepository` |
| `db` | `DatabaseManager` |
| `schema` | `SchemaBuilder` |
| `migrator` | `Migrator` |
| `router` | `Router` |
| `view` | `Forge` |
| `auth` | `AuthManager` |
| `gate` | `GateManager` |
| `hash` | `Hash` |
| `events` | `EventDispatcher` |
| `proxy` | `InternalProxy` - in-memory module-to-module calls ([guide](internal-proxy.md)) |
| `queue` | `QueueManager` |
| `cache` | `CacheManager` |
| `log` | `logging.Logger` |
| `exception_handler` | `ExceptionHandler` |
| `module`, `plugin`, `setting`, `schedule` | Framework subsystems |
| `pqc`, `captcha` | Security utilities |

## Service providers

Providers register bindings and then boot them. `register()` runs for every
provider first, so `boot()` can rely on anything being bound.

```python
# app/Providers/AppServiceProvider.py
from craft.providers import ServiceProvider


class AppServiceProvider(ServiceProvider):
    def register(self):
        self.app.singleton("mailer", lambda c: Mailer())

    def boot(self):
        self.app.make("view").share("app_name", self.app.make("config").get("app.APP_NAME"))
```

Register it in `bootstrap/app.py`:

```python
app.register_provider(AppServiceProvider)
```

A provider registered after `app.boot()` boots immediately.

## Facades

Facades are a static front for a container binding:

```python
from craft.facades import DB, Auth, Cache, Config, Route, View

DB.statement("SELECT 1")
Auth.check()
Cache.get("key")
```

The facades that ship with the framework: `Route`, `DB`, `Config`, `Auth`,
`Event`, `Queue`, `Log`, `Cache`, `Hash`, `Migrator`, `Gate`, `View`, `Schema`,
`Module`, `Plugin`, `Setting`, `PQC`, `Captcha`, and `Schedule`. There is no
`App` facade — reach the application through the `app` built in
`bootstrap/app.py`, or `Container.getInstance()`.

Each resolves its accessor from the container on every call, so swapping the
binding in a test swaps what the facade talks to.

Facades never fabricate dunder or private attributes — `DummyFacade.__wrapped__`
raises `AttributeError` instead of resolving the container. That matters more
than it sounds: introspection (pytest collection, `inspect`, `copy`) probes
those names, and answering them resolved the container before the app booted.

Write your own by naming the binding:

```python
from craft.facades.base import Facade


class Mail(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "mailer"
```
