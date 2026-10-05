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
10-second timeouts) while the proxy keeps serving about 1,400 req/s. The full
results are in [Benchmark: before and after](#benchmark-before-and-after).

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
| `INTERNAL_TARGET_UNAVAILABLE` | the owning extension cannot serve right now (circuit open) |

### Exposures owned by an extension

An extension exposes through its context, which makes it the owner
(`documentation/extensions.md`):

```python
def register(context):
    context.expose("billing", BillingService, {"generate_invoice"})
```

An owned alias follows its extension's health and lifecycle:

| Situation | Effect |
|---|---|
| the extension is deactivated | the alias is withdrawn: `INTERNAL_TARGET_NOT_EXPOSED` |
| its circuit breaker is open | the call is refused without running the target: `INTERNAL_TARGET_UNAVAILABLE` |
| the target raises an unexpected exception | it reaches the caller unchanged and counts toward the owner's breaker |
| the target raises a typed domain error (status below 500) | it reaches the caller unchanged and is not counted |

`expose(alias, service, methods, owner="slug")` and `unexpose(alias)` are the
underlying calls; `set_gate(gate)` installs what decides whether an owner may
run (the extension manager does it at boot).

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

- A module never imports another module's code; it calls an exposed service
  through the proxy, emits an event, or depends on a contract. Between
  extensions the boundary gate enforces it (`EXTENSION_CROSS_IMPORT`).
- A module never calls another module over HTTP inside the same application.
- The engine never imports the application. The boundary gate
  (`tools/check_engine_boundary.py`) enforces it in CI.

## Benchmark: before and after

Before the internal proxy, one module reached another with a loopback HTTP
request through the kernel. After it, the module calls the service through the
proxy, on the same thread and inside the same transaction. Both were measured
on the real kernel under uvicorn, against the same service method, which
performs one database read.

Measured on 2026-10-04 at commit `480dd2b`, in the `framework` container:
Python 3.14.7, uvicorn 0.53.0, 8 CPUs, one process, 40 thread-pool workers, a
throwaway SQLite file, keep-alive connections, five seconds per load scenario.
The raw report is [`assets/proxy-benchmark.json`](assets/proxy-benchmark.json).

### Cost of one call

![Mean cost of one call between modules, log scale: direct call 9.2 us, Proxy.dispatch 11.9 us, Proxy.call 16.1 us, HTTP over TCP 816.6 us, kernel in process 1,990.5 us](assets/proxy-benchmark-call.svg)

| Path | Calls/s | Mean | p50 | p95 | p99 |
|---|---:|---:|---:|---:|---:|
| Direct method call | 105,926 | 9.2 us | 8.1 us | 14.5 us | 20.3 us |
| `Proxy.dispatch` | 82,585 | 11.9 us | 11.7 us | 12.3 us | 19.2 us |
| `Proxy.call` | 61,201 | 16.1 us | 14.8 us | 25.7 us | 30.9 us |
| HTTP over TCP, keep-alive | 1,224 | 816.6 us | 767.4 us | 1,197.9 us | 1,543.0 us |
| Kernel in process (ASGI, no socket) | 502 | 1,990.5 us | 1,878.8 us | 2,473.2 us | 3,234.5 us |

The proxy adds a few microseconds over a direct call; the same call over HTTP
costs about 50 times more. The gap between `call` and `dispatch` is measurement
order, not a property of either: both run the target inline.

### Requests end to end

An external request reaches module A through the full kernel; module A then
reaches module B through the proxy (after) or a loopback HTTP request (before).

![Requests per second by concurrent clients: the proxy holds about 1,300 to 1,500 req/s from 1 to 64 clients; loopback HTTP holds about 660 to 750 req/s up to 32 clients and drops to 8 req/s at 64](assets/proxy-benchmark-rps.svg)

![p95 latency by concurrent clients, log scale: the proxy rises from 0.9 ms to 58 ms; loopback HTTP from 1.9 ms to 56 ms at 32 clients and 10 s at 64](assets/proxy-benchmark-p95.svg)

| Clients | Before: req/s | After: req/s | Before: p95 | After: p95 | Before: failures | After: failures |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 663 | 1,308 | 1.88 ms | 0.93 ms | 0 | 0 |
| 8 | 746 | 1,395 | 15.36 ms | 8.89 ms | 1 | 0 |
| 32 | 740 | 1,513 | 56.15 ms | 29.11 ms | 15 | 0 |
| 64 | 8 | 1,426 | 9,983 ms | 58.36 ms | 89 | 0 |

At 64 clients the loopback pattern deadlocks: each loopback request holds two of
the 40 workers, so every worker ends up waiting on an inner request that needs a
worker. The proxy holds one worker per request.

### The test suite, before and after

| | Before (v4.1.0, published) | After (2026-10-04, commit `4b9d3a6`) |
|---|---:|---:|
| Passed on PostgreSQL 18.6 | 1,758 | 1,834 |
| Passed on SQLite | 1,696 | 1,772 |
| Tests | 1,762 | 1,838 |
| Test files | 106 | 111 |
| Failures | 0 | 0 |

### Reproduce it

```bash
python tests/benchmark_internal_proxy.py --json proxy-benchmark.json
python tools/render_benchmark_charts.py proxy-benchmark.json
```

Absolute numbers move with hardware, database and worker count. The ratios and
the deadlock at twice the pool size come from the architecture.

