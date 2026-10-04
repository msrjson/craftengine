"""Benchmark: module-to-module calls through the internal proxy versus HTTP.

Boots the real Craft kernel under uvicorn on a loopback TCP port, against a
throwaway SQLite file, and measures three things:

1. **Cost per call** - the same service method reached as a direct call,
   through `Proxy.call`, through `Proxy.dispatch`, through the kernel in
   process (ASGI, no socket) and through real HTTP over TCP (keep-alive).
2. **Requests end to end** - an external request to module A, which needs
   module B: once through the proxy, once through a loopback HTTP call (the
   pattern the proxy replaces), at several concurrency levels.
3. **Saturation** - a loopback request holds two thread-pool workers (its own
   and the inner request's), so it runs out of workers at half the
   concurrency; a proxy request holds one.

Not collected by pytest (the file name does not start with `test_`). Run it
inside the application container:

    docker exec framework sh -lc 'cd /app && python tests/benchmark_internal_proxy.py'
    docker exec framework sh -lc 'cd /app && python tests/benchmark_internal_proxy.py --seconds 3 --clients 1 --clients 64 --json /tmp/proxy.json'
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import argparse
import asyncio
import http.client
import json
import os
import platform
import socket
import statistics
import sys
import tempfile
import threading
import time
from typing import Any, Callable

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

_DATABASE = os.path.join(tempfile.mkdtemp(prefix="craft-proxy-bench-"), "bench.sqlite")
os.environ.update({"DB_CONNECTION": "sqlite", "DB_DATABASE": _DATABASE, "APP_DEBUG": "false"})

import uvicorn  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

from bootstrap.app import app, asgi_app  # noqa: E402
from craft.facades import DB, Route  # noqa: E402
from craft.migrations.migrator import Migrator  # noqa: E402

REQUEST_TIMEOUT_SECONDS = 10.0


class BillingService:
    """Module B: one small database read, then a plain result."""

    def generate_invoice(self, order_id: int) -> dict:
        DB.select("SELECT 1")
        return {"order_id": order_id, "amount_cents": 12900, "currency": "BRL"}


# -- the server ---------------------------------------------------------------


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def start_server(port: int) -> uvicorn.Server:
    """Serve the real kernel on 127.0.0.1:`port` from a background thread."""
    config = uvicorn.Config(asgi_app, host="127.0.0.1", port=port, log_level="error", access_log=False)
    server = uvicorn.Server(config)
    threading.Thread(target=server.run, daemon=True).start()
    deadline = time.monotonic() + 15
    while not server.started:
        if time.monotonic() > deadline:
            raise RuntimeError("BENCH_SERVER_DID_NOT_START")
        time.sleep(0.05)
    return server


_loopback = threading.local()


def _loopback_get(port: int, path: str) -> dict:
    """Module A reaching module B over HTTP, on a per-thread keep-alive connection."""
    if getattr(_loopback, "connection", None) is None:
        _loopback.connection = http.client.HTTPConnection("127.0.0.1", port, timeout=REQUEST_TIMEOUT_SECONDS)
    try:
        _loopback.connection.request("GET", path)
        return json.loads(_loopback.connection.getresponse().read())
    except (OSError, http.client.HTTPException, ValueError):
        _loopback.connection = None
        raise


def register_routes(port: int) -> None:
    """Expose module B and add module A's two ways of reaching it."""
    app.bind(BillingService)
    proxy = app.make("proxy")
    if "bench.billing" not in proxy.exposed():
        proxy.expose("bench.billing", BillingService, {"generate_invoice"})

    def billing(request: Any) -> dict:
        return app.make(BillingService).generate_invoice(int(request.query_params.get("order_id", 1)))

    def checkout_proxy(request: Any) -> dict:
        return proxy.call("bench.billing", "generate_invoice", 7)

    def checkout_loopback(request: Any) -> dict:
        return _loopback_get(port, "/bench/billing?order_id=7")

    Route.get("/bench/billing", billing).name("bench.billing")
    Route.get("/bench/checkout-proxy", checkout_proxy).name("bench.checkout.proxy")
    Route.get("/bench/checkout-loopback", checkout_loopback).name("bench.checkout.loopback")


# -- statistics ---------------------------------------------------------------


def summarize(latencies_ns: list[int], seconds: float, failures: int = 0) -> dict:
    """Per-call latency percentiles in microseconds, plus throughput."""
    ordered = sorted(latencies_ns)
    if not ordered:
        return {"calls": 0, "failures": failures, "per_second": 0.0}

    def percentile(share: float) -> float:
        return ordered[min(len(ordered) - 1, int(len(ordered) * share))] / 1000

    return {
        "calls": len(ordered),
        "failures": failures,
        "per_second": round(len(ordered) / seconds, 1) if seconds else 0.0,
        "mean_us": round(statistics.fmean(ordered) / 1000, 2),
        "p50_us": round(percentile(0.50), 2),
        "p95_us": round(percentile(0.95), 2),
        "p99_us": round(percentile(0.99), 2),
    }


def time_calls(work: Callable[[], Any], repeat: int) -> dict:
    """Run `work` `repeat` times on this thread and time each call."""
    latencies = []
    started = time.perf_counter()
    for _ in range(repeat):
        begin = time.perf_counter_ns()
        work()
        latencies.append(time.perf_counter_ns() - begin)
    return summarize(latencies, time.perf_counter() - started)


def time_dispatch(repeat: int) -> dict:
    """Time `Proxy.dispatch` from inside one running event loop."""
    proxy = app.make("proxy")

    async def run() -> dict:
        latencies = []
        started = time.perf_counter()
        for _ in range(repeat):
            begin = time.perf_counter_ns()
            await proxy.dispatch("bench.billing", "generate_invoice", 7)
            latencies.append(time.perf_counter_ns() - begin)
        return summarize(latencies, time.perf_counter() - started)

    return asyncio.run(run())


# -- 1. cost per call -----------------------------------------------------------


def per_call_costs(port: int, scale: int) -> dict:
    """The same invoice, reached five ways."""
    service = app.make(BillingService)
    proxy = app.make("proxy")
    in_process = TestClient(asgi_app)
    over_tcp = http.client.HTTPConnection("127.0.0.1", port, timeout=REQUEST_TIMEOUT_SECONDS)

    def tcp_get() -> None:
        over_tcp.request("GET", "/bench/billing?order_id=7")
        over_tcp.getresponse().read()

    return {
        "direct_method_call": time_calls(lambda: service.generate_invoice(7), 20 * scale),
        "proxy_call": time_calls(lambda: proxy.call("bench.billing", "generate_invoice", 7), 20 * scale),
        "proxy_dispatch": time_dispatch(20 * scale),
        "kernel_in_process_asgi": time_calls(lambda: in_process.get("/bench/billing?order_id=7"), scale // 2),
        "http_over_tcp_keepalive": time_calls(tcp_get, scale),
    }


# -- 2 and 3. requests end to end -------------------------------------------------


def _client(port: int, path: str, deadline: float, latencies: list, failures: list) -> None:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=REQUEST_TIMEOUT_SECONDS)
    while time.monotonic() < deadline:
        begin = time.perf_counter_ns()
        try:
            connection.request("GET", path)
            response = connection.getresponse()
            response.read()
        except (OSError, http.client.HTTPException):
            failures.append(1)
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=REQUEST_TIMEOUT_SECONDS)
            continue
        if response.status != 200:
            failures.append(response.status)
            continue
        latencies.append(time.perf_counter_ns() - begin)


def load(port: int, path: str, clients: int, seconds: float) -> dict:
    """`clients` keep-alive clients hammer `path` for `seconds`."""
    latencies: list[int] = []
    failures: list[int] = []
    deadline = time.monotonic() + seconds
    threads = [
        threading.Thread(target=_client, args=(port, path, deadline, latencies, failures))
        for _ in range(clients)
    ]
    started = time.perf_counter()
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return {"clients": clients, **summarize(latencies, time.perf_counter() - started, len(failures))}


def end_to_end(port: int, levels: list[int], seconds: float) -> list[dict]:
    """External request to module A, which reaches module B by proxy or by HTTP."""
    rows = []
    for clients in levels:
        for route in ("proxy", "loopback"):
            row = load(port, f"/bench/checkout-{route}", clients, seconds)
            rows.append({"route": route, **row})
            print_request_row(rows[-1])
    return rows


# -- report -----------------------------------------------------------------------


def print_call_costs(costs: dict) -> None:
    baseline = costs["direct_method_call"]["mean_us"] or 1
    print("\n1. Cost per call (same invoice, five paths)")
    print(f"{'path':<26}{'calls/s':>12}{'mean us':>10}{'p50 us':>10}{'p95 us':>10}{'p99 us':>10}{'x direct':>10}")
    for name, row in costs.items():
        ratio = row["mean_us"] / baseline
        print(
            f"{name:<26}{row['per_second']:>12,.0f}{row['mean_us']:>10.1f}{row['p50_us']:>10.1f}"
            f"{row['p95_us']:>10.1f}{row['p99_us']:>10.1f}{ratio:>10.1f}"
        )


def print_request_row(row: dict) -> None:
    if row["calls"] == 0:
        print(f"{row['route']:<10}{row['clients']:>8}{'0':>10}{'-':>10}{'-':>10}{'-':>10}{row['failures']:>9}")
        return
    print(
        f"{row['route']:<10}{row['clients']:>8}{row['per_second']:>10,.0f}{row['p50_us'] / 1000:>10.2f}"
        f"{row['p95_us'] / 1000:>10.2f}{row['p99_us'] / 1000:>10.2f}{row['failures']:>9}"
    )


def environment() -> dict:
    """What the numbers were measured on."""
    import anyio
    import anyio.to_thread

    async def thread_pool_tokens() -> float:
        return anyio.to_thread.current_default_thread_limiter().total_tokens

    return {
        "python": platform.python_version(),
        "machine": platform.machine(),
        "cpus": os.cpu_count(),
        "uvicorn": uvicorn.__version__,
        "thread_pool_tokens": anyio.run(thread_pool_tokens),
        "database": "sqlite file (throwaway)",
    }


def main(argv: list[str] | None = None) -> dict:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seconds", type=float, default=5.0, help="duration of each load scenario")
    parser.add_argument("--clients", type=int, action="append", help="concurrency level; repeat to sweep")
    parser.add_argument("--scale", type=int, default=1000, help="iterations multiplier for per-call costs")
    parser.add_argument("--json", help="write the results to this file")
    args = parser.parse_args(argv)

    Migrator(app).run()
    port = _free_port()
    register_routes(port)
    server = start_server(port)
    try:
        costs = per_call_costs(port, args.scale)
        print_call_costs(costs)
        print("\n2. Requests end to end: module A -> module B (latency in ms)")
        print(f"{'route':<10}{'clients':>8}{'req/s':>10}{'p50':>10}{'p95':>10}{'p99':>10}{'failures':>9}")
        requests = end_to_end(port, args.clients or [1, 8, 32, 64], args.seconds)
    finally:
        server.should_exit = True
    result = {"environment": environment(), "per_call": costs, "end_to_end": requests}
    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2)
    return result


if __name__ == "__main__":
    main()
