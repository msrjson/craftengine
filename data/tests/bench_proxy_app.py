"""The ASGI app the internal-proxy benchmark serves, with its routes registered.

Kept in its own module so the multi-worker mode can hand uvicorn an import
string (`tests.bench_proxy_app:application`): each worker imports this module
and registers the routes on the real kernel, instead of inheriting the parent
process's in-memory registration (which a forked worker never sees).

The environment (database, APP_DEBUG) must already be set by the caller before
this module is imported — `benchmark_internal_proxy.py` does that at its top.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import http.client
import json
import os
import threading
from typing import Any

from bootstrap.app import app, asgi_app
from craft.facades import DB, Route

REQUEST_TIMEOUT_SECONDS = 10.0

_loopback = threading.local()


class BillingService:
    """Module B: one small database read, then a plain result."""

    def generate_invoice(self, order_id: int) -> dict:
        DB.select("SELECT 1")
        return {"order_id": order_id, "amount_cents": 12900, "currency": "BRL"}


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


#: A worker launched by the benchmark registers the routes for the port it was told.
_BENCH_PORT = int(os.environ.get("CRAFT_PROXY_BENCH_PORT", "0"))
if _BENCH_PORT:
    register_routes(_BENCH_PORT)

application = asgi_app

__all__ = ["application", "app", "asgi_app", "BillingService", "register_routes"]
