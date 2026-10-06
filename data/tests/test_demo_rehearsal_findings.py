"""Defects the CRM demo rehearsal found in v4.4.1 candidates, pinned so they stay fixed.

The demo installs the framework like any project and walks it as a person
would; each case below failed there before it was fixed here.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from types import SimpleNamespace

import pytest

from engine.http.response import redirect
from engine.validation.validator import Validator


class TestRegexRule:
    """`regex:` used to split its pattern on commas, so `[.,]` raised a 500."""

    @pytest.mark.parametrize("value", ["1500", "1500,90", "1500.9"])
    def test_a_pattern_with_a_comma_validates(self, value):
        assert Validator({"amount": value}, {"amount": ["regex:^[0-9]+([.,][0-9]{1,2})?$"]}).passes()

    def test_a_value_outside_the_pattern_fails(self):
        assert Validator({"amount": "15,999"}, {"amount": ["regex:^[0-9]+([.,][0-9]{1,2})?$"]}).fails()


def _request(referer: str, host: str = "crm.example") -> SimpleNamespace:
    return SimpleNamespace(headers={"referer": referer, "host": host})


class TestRedirectBack:
    """`redirect.back()` followed any Referer: an open redirect."""

    @pytest.mark.parametrize("referer", ["https://evil.example/phish", "//evil.example/x", "javascript:alert(1)", "http://crm.example.evil.example/"])
    def test_a_foreign_referer_falls_back(self, referer):
        assert redirect.back(_request(referer), fallback="/home").headers["location"] == "/home"

    @pytest.mark.parametrize(("referer", "expected"), [
        ("/companies/create", "/companies/create"),
        ("https://crm.example/companies/create?x=1", "https://crm.example/companies/create?x=1"),
    ])
    def test_a_same_site_referer_is_followed(self, referer, expected):
        assert redirect.back(_request(referer)).headers["location"] == expected


class TestCsrfRefusalsAreTyped:
    """CSRF refusals answered a hardcoded English sentence; now a code and a key."""

    @pytest.fixture
    def client(self, migrated_database):
        import uuid

        from starlette.testclient import TestClient

        from bootstrap.app import app, asgi_app

        path = "/ext-test/csrf-" + uuid.uuid4().hex[:8]
        app.make("router").post(path, lambda: "accepted")
        return TestClient(asgi_app), path

    def test_a_missing_token_is_419_with_a_key(self, client):
        test_client, path = client
        response = test_client.post(path, headers={"accept": "application/json"})
        assert response.status_code == 419
        assert (response.json()["code"], response.json()["message_key"]) == ("CSRF_TOKEN_MISMATCH", "security.csrf.token_mismatch")

    def test_a_foreign_origin_is_403_with_a_key(self, client):
        test_client, path = client
        response = test_client.post(path, headers={"accept": "application/json", "origin": "https://evil.example"})
        assert response.status_code == 403
        assert (response.json()["code"], response.json()["message_key"]) == ("CSRF_ORIGIN_REJECTED", "security.csrf.origin_rejected")

    @pytest.mark.parametrize("key", ["security.csrf.origin_rejected", "security.csrf.token_mismatch", "extension.error.extension_route_conflict"])
    def test_the_new_keys_exist_in_every_locale(self, migrated_database, key):
        from craft.facades import DB

        assert {row["locale"] for row in DB.table("translations").where("key", key).get()} == {"en", "pt-BR", "es"}


class TestRedirectBackBehindAProxy:
    """Behind a reverse proxy the Host header is internal while APP_URL is the
    public address the browser used; the CSRF check trusts APP_URL, so
    `redirect.back()` must trust it too, or a valid form error lands on `/`."""

    def test_a_referer_on_app_url_is_followed_whatever_the_host_header(self, monkeypatch):
        from engine.http import response

        monkeypatch.setattr(response, "_app_url_host", lambda: "crm.example")
        back = redirect.back(_request("https://crm.example/companies/create", host="app:9000"), fallback="/")
        assert back.headers["location"] == "https://crm.example/companies/create"

    def test_another_site_still_falls_back(self, monkeypatch):
        from engine.http import response

        monkeypatch.setattr(response, "_app_url_host", lambda: "crm.example")
        assert redirect.back(_request("https://evil.example/x", host="app:9000"), fallback="/").headers["location"] == "/"
