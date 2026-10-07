"""`route:check` reports broken routes; a name two routes share is flagged."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from typer.testing import CliRunner

import engine.cli.app as cli_module
from bootstrap import app as bootstrap_app
from engine.cli.app import cli
from engine.http.router import Router
from engine.support.doctor import check_routes


class _App:
    def __init__(self, router):
        self._router = router

    def make(self, key):
        return self._router


class _Kernel:
    def resolve_route_middleware(self, entries):
        return entries


class _Controller:
    def index(self):
        return None


def _invoke(monkeypatch, router):
    monkeypatch.setattr(cli_module, "get_app", lambda: _App(router))
    monkeypatch.setattr(bootstrap_app, "kernel", _Kernel())
    return CliRunner().invoke(cli, ["route", "check"])


def test_duplicate_route_names_are_reported():
    router = Router()
    router.get("/a", lambda request: None).name("dup")
    router.get("/b", lambda request: None).name("dup")

    findings = list(check_routes(_App(router), _Kernel()))

    assert "ROUTE_NAME_DUPLICATE" in [finding.code for finding in findings]


def test_a_clean_router_reports_nothing():
    router = Router()
    router.get("/a", lambda request: None).name("a")
    router.get("/b", lambda request: None).name("b")

    assert list(check_routes(_App(router), _Kernel())) == []


def test_the_command_passes_on_a_clean_router(monkeypatch):
    router = Router()
    router.get("/a", [_Controller, "index"]).name("a")

    result = _invoke(monkeypatch, router)

    assert result.exit_code == 0, result.output


def test_the_command_fails_on_a_broken_action(monkeypatch):
    router = Router()
    router.get("/a", [_Controller, "missing"]).name("a")

    result = _invoke(monkeypatch, router)

    assert result.exit_code == 1
    assert "ROUTE_ACTION_NOT_FOUND" in result.output
