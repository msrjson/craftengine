"""The kernel announces the end of a request; subsystems clean up after themselves.

The HTTP kernel serves external traffic and knows no subsystem by name. At
the end of every request it emits `RequestTerminated` on the worker thread
that served it, and each subsystem - the database returning its pooled
connection first among them - listens for it.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import re
import threading
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from bootstrap.app import app, asgi_app
from craft.facades import DB, Route
from engine.events.dispatcher import EventDispatcher
from engine.events.lifecycle import RequestTerminated

KERNEL_SOURCE = (Path(__file__).resolve().parent.parent / "engine" / "http" / "kernel.py").read_text()


@pytest.fixture(scope="module", autouse=True)
def routes(migrated_database):
    def touch_database(request):
        DB.select("SELECT 1")
        return {"thread": threading.current_thread().name}

    Route.get("/t/lifecycle", touch_database).name("t.lifecycle")
    Route.get("/t/module_lifecycle", touch_database).name("t.module_lifecycle").module("lifecycle_test_mod")

    def raising_action(request):
        raise RuntimeError("PROBE_RAISING_ACTION")

    Route.get("/t/raising_lifecycle", raising_action).name("t.raising_lifecycle")
    yield


def test_kernel_reaches_no_subsystem_by_name():
    reached = set(re.findall(r'make\("([a-z_.]+)"\)', KERNEL_SOURCE))
    assert reached.isdisjoint({"db", "auth", "session", "cache", "queue", "translator"})


def test_request_terminated_fires_once_on_the_serving_thread():
    seen = []
    app.make("events").listen(RequestTerminated, lambda event: seen.append(threading.current_thread().name))
    try:
        served_on = TestClient(asgi_app).get("/t/lifecycle").json()["thread"]
    finally:
        app.make("events").forget(RequestTerminated)
    assert seen == [served_on]


def test_a_failing_listener_does_not_skip_the_connection_release():
    def broken(_event):
        raise RuntimeError("PROBE_LISTENER_FAILURE")

    # A failing listener must not skip the database release, which runs last.
    app.make("events").forget(RequestTerminated)
    app.make("events").listen(RequestTerminated, broken)
    connection = app.make("db").write_connection
    try:
        client = TestClient(asgi_app)
        for _ in range(3):
            assert client.get("/t/lifecycle").status_code == 200
    finally:
        app.make("events").forget(RequestTerminated)
    assert connection.open_sessions <= 1


def test_notify_delivers_to_every_listener_despite_failures(caplog):
    dispatcher = EventDispatcher()
    delivered = []

    def broken(_event):
        raise RuntimeError("PROBE_FIRST_LISTENER_FAILURE")

    dispatcher.listen(RequestTerminated, [broken, lambda event: delivered.append(event)])
    event = RequestTerminated(request=None)
    dispatcher.notify(event)
    assert delivered == [event]
    assert "PROBE_FIRST_LISTENER_FAILURE" in caplog.text


def test_event_loop_thread_holds_no_connection_after_module_request_with_expired_cache():
    connection = app.make("db").write_connection
    app.make("module").forget_cached_state()
    connection.release()

    client = TestClient(asgi_app)
    response = client.get("/t/module_lifecycle")
    assert response.status_code == 200

    session = getattr(connection._thread_sessions, "session", None)
    assert session is None or session.pdo is None


def test_event_loop_thread_holds_no_connection_after_raising_action():
    connection = app.make("db").write_connection
    connection.release()

    client = TestClient(asgi_app)
    response = client.get("/t/raising_lifecycle")
    assert response.status_code == 500

    session = getattr(connection._thread_sessions, "session", None)
    assert session is None or session.pdo is None

