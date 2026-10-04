# Internal proxy

Modules call each other through the internal proxy, in memory. External
traffic - browsers, API clients, webhooks - enters through the HTTP kernel and
its full middleware stack; a call from one module to another never does.

| Traffic | Path | Cost |
|---|---|---|
| External | HTTP kernel: ASGI, firewall, session, CSRF, middleware, routing | a full request |
| Internal | `proxy.call` / `proxy.dispatch`: container lookup, method call | one function call |

Measured with `tests/benchmark_internal_proxy.py` (real kernel under uvicorn,
one process, one database read per call):

| Same service method reached through | Mean per call |
|---|---:|
| direct method call | 9 us |
| `Proxy.call` / `Proxy.dispatch` | 12-16 us |
| HTTP over TCP, keep-alive | 817 us |
| the kernel in process (ASGI, no socket) | 1,990 us |

End to end, an external request whose module calls another module serves about
twice the requests per second through the proxy as through a loopback HTTP
call, at half the latency. A loopback request also holds two thread-pool
workers; with the default 40, 64 concurrent clients deadlock the pool (8 req/s,
10-second timeouts) while the proxy keeps serving about 1,400 req/s. Run it:

```bash
python tests/benchmark_internal_proxy.py --seconds 5 --clients 1 --clients 64
```

The proxy is routing infrastructure only. It holds no tenant, authorization or
business rule. Every target runs on the caller's own thread, so it shares the
caller's context - tenant, user, locale, request id - its pooled database
connection and any transaction the caller has open. Tenant isolation stays with its two barriers: the module's own code
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

- an alias another module already exposed - no module can take over another's;
- a private (`_name`) or empty method name;
- a method the class does not define, so a typo fails before the first call
  (checked when `expose` receives the class itself).

Calling an alias or a method that was not exposed raises `InternalProxyError`
with a machine `code`:

| Code | Meaning |
|---|---|
| `INTERNAL_TARGET_NOT_EXPOSED` | no module exposed this alias |
| `INTERNAL_METHOD_NOT_EXPOSED` | the alias exists, the method was not exposed |
| `INTERNAL_ASYNC_HANDLER_FROM_SYNC_CALL` | `call` on a target that is or returns an awaitable; use `dispatch` |
| `INTERNAL_DURABLE_EVENT` | `emit` of an event marked `durable = True` |
| `INTERNAL_ALIAS_ALREADY_EXPOSED` | `expose` of an alias that is already taken |
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

From async code, `dispatch` calls the target and awaits whatever it returns:

```python
invoice = await Proxy.dispatch("billing", "generate_invoice", order_id)
```

A synchronous target runs inline on the caller's thread, never on a worker
thread: on another thread it would borrow a second pooled connection, outside
the caller's transaction, that nothing returns. The engine runs async actions
on the request's own worker thread, so this does not block the server's event
loop.

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
