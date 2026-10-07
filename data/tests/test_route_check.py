"""`route:check` reports broken routes; a name two routes share is flagged."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from typer.testing import CliRunner

import engine.cli.app as cli_module
from engine.cli.app import cli
from engine.http.router import Router
from engine.support.doctor import check_route_actions


class _Kernel:
    """A stub kernel that knows a set of middleware aliases."""

    def __init__(self, known):
        self._known = set(known)

    def resolve_route_middleware(self, entries):
        for entry in entries:
            if isinstance(entry, str) and entry not in self._known:
                raise KeyError(entry)
        return list(entries)


class _App:
    def __init__(self, router, kernel=None):
        self._router = router
        self._kernel = kernel

    def make(self, key):
        if key == "kernel":
            if self._kernel is None:
                raise KeyError("kernel")
            return self._kernel
        return self._router


class _Controller:
    def index(self):
        return None


def _invoke(monkeypatch, router, kernel=None):
    monkeypatch.setattr(cli_module, "get_app", lambda: _App(router, kernel))
    return CliRunner().invoke(cli, ["route", "check"])


def test_duplicate_route_names_are_reported():
    router = Router()
    router.get("/a", lambda request: None).name("dup")
    router.get("/b", lambda request: None).name("dup")

    findings = list(check_route_actions(_App(router)))

    assert "ROUTE_NAME_DUPLICATE" in [finding.code for finding in findings]


def test_a_clean_router_reports_nothing():
    router = Router()
    router.get("/a", lambda request: None).name("a")
    router.get("/b", lambda request: None).name("b")

    assert list(check_route_actions(_App(router))) == []


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


def test_a_bad_middleware_alias_is_reported_and_fails_the_command(monkeypatch):
    router = Router()
    router.get("/a", [_Controller, "index"]).middleware("authh").name("a")

    result = _invoke(monkeypatch, router, _Kernel({"auth"}))

    assert result.exit_code == 1
    assert "ROUTE_MIDDLEWARE_INVALID" in result.output


def test_a_known_middleware_alias_passes(monkeypatch):
    router = Router()
    router.get("/a", [_Controller, "index"]).middleware("auth").name("a")

    result = _invoke(monkeypatch, router, _Kernel({"auth"}))

    assert result.exit_code == 0, result.output
