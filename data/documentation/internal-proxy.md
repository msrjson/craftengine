# Internal proxy

Modules call each other through the internal proxy, in memory. External
traffic - browsers, API clients, webhooks - enters through the HTTP kernel and
its full middleware stack; a call from one module to another never does.

| Traffic | Path | Cost |
|---|---|---|
| External | HTTP kernel: ASGI, firewall, session, CSRF, middleware, routing | a full request |
| Internal | `proxy.call` / `proxy.dispatch`: container lookup, method call | one function call |

Measured in the test suite (`tests/test_internal_proxy.py`): about 5
microseconds per proxy call against about 2.6 milliseconds for the same call
made as a loopback HTTP request.

The proxy is routing infrastructure only. It holds no tenant, authorization or
business rule. The caller's context - tenant, database connection, user,
locale, request id - lives in context variables and travels with the call
unchanged. Tenant isolation stays with its two barriers: the module's own code
and the database's row-level security. The decision is recorded in ADR 0003
(`docs/adr/0003-engine-boundary-and-internal-proxy.md` in the repository).

## Exposing a service

Nothing is callable until a module exposes it. Declare it in the module's
service provider:

```python
from craft.providers import ServiceProvider

from app.Modules.Billing.BillingService import BillingService


class BillingServiceProvider(ServiceProvider):
    def register(self) -> None:
        self.app.bind(BillingService)

    def boot(self) -> None:
        self.app.make("proxy").expose("billing", BillingService, {"generate_invoice"})
```

`expose` refuses, at boot:

- a private (`_name`) or empty method name;
- a method the class does not define, so a typo fails before the first call.

Calling an alias or a method that was not exposed raises `InternalProxyError`
with a machine `code`:

| Code | Meaning |
|---|---|
| `INTERNAL_TARGET_NOT_EXPOSED` | no module exposed this alias |
| `INTERNAL_METHOD_NOT_EXPOSED` | the alias exists, the method was not exposed |
| `INTERNAL_ASYNC_HANDLER_FROM_SYNC_CALL` | `call` on a coroutine; use `dispatch` |
| `INTERNAL_DURABLE_EVENT` | `emit` of an event marked `durable = True` |
| `INTERNAL_EXPOSE_PRIVATE_OR_EMPTY_METHOD` | `expose` of a private or empty name |
| `INTERNAL_EXPOSE_UNKNOWN_METHOD` | `expose` of a method the class lacks |

## Calling another module

```python
from craft.facades import Proxy


class CheckoutController:
    def complete(self, request):
        # The order module asks billing for an invoice: no HTTP, no middleware.
        invoice = Proxy.call("billing", "generate_invoice", request.input("order_id"))
        return {"invoice_id": invoice.id}
```

From async code, `dispatch` awaits a coroutine target and runs a synchronous
one on a worker thread, carrying a copy of the caller's context:

```python
invoice = await Proxy.dispatch("billing", "generate_invoice", order_id)
```

If the awaiting caller is cancelled, `dispatch` waits for that worker thread
to finish before re-raising, so the request never ends - and returns its
pooled connection - while the thread still runs a transaction on it.

The proxy resolves the target through the container, so it is also available
by injection (`InternalProxy` in a constructor) or as `app.make("proxy")`.

## Events

`Proxy.emit(event)` delivers an in-memory event to its listeners. An event
class marked `durable = True` - money movements, anything that must survive a
crash - is refused: it belongs to a queued job or an outbox, not to memory.

## Rules

- A module never imports another module's controller; it calls an exposed
  service through the proxy, emits an event, or depends on a contract.
- A module never calls another module over HTTP inside the same application.
- The engine never imports the application. The boundary gate
  (`tools/check_engine_boundary.py`) enforces it in CI.
