"""A FormRequest in an action's signature is injected already validated."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest
from starlette.testclient import TestClient

from bootstrap.app import asgi_app
from craft.facades import Route
from craft.validation.form_request import FormRequest


class StoreWidgetRequest(FormRequest):
    def rules(self):
        return {"name": ["required", "string", "max:20"]}


class ForbiddenRequest(FormRequest):
    def authorize(self):
        return False


class WidgetController:
    def store(self, form: StoreWidgetRequest):
        return {"stored": form.validated()}

    def store_named_request(self, request: StoreWidgetRequest):
        return {"stored": request.validated(), "kind": type(request).__name__}

    def forbidden(self, form: ForbiddenRequest):
        return {"reached": True}


@pytest.fixture(scope="module", autouse=True)
def routes(migrated_database):
    Route.post("/api/t/form-injection", [WidgetController, "store"]).name("t.form.store")
    Route.post("/api/t/form-injection/named", [WidgetController, "store_named_request"]).name("t.form.named")
    Route.post("/api/t/form-injection/forbidden", [WidgetController, "forbidden"]).name("t.form.forbidden")
    yield


@pytest.fixture
def client():
    return TestClient(asgi_app, headers={"Accept": "application/json"})


def _post(client, path, data):
    # Under /api/, which CSRF exempts; CSRF on web forms is covered elsewhere.
    return client.post(path, json=data)


class TestInjection:
    def test_valid_input_reaches_the_action_validated(self, client):
        response = _post(client, "/api/t/form-injection", {"name": "bolt", "extra": "dropped"})
        assert response.status_code == 200
        assert response.json() == {"stored": {"name": "bolt"}}

    def test_invalid_input_never_reaches_the_action(self, client):
        response = _post(client, "/api/t/form-injection", {"name": ""})
        assert response.status_code == 422

    def test_a_parameter_named_request_gets_the_form(self, client):
        response = _post(client, "/api/t/form-injection/named", {"name": "nut"})
        assert response.json()["kind"] == "StoreWidgetRequest"

    def test_an_unauthorized_form_is_refused(self, client):
        response = _post(client, "/api/t/form-injection/forbidden", {})
        assert response.status_code == 403


class TestValidatedIsCached:
    def test_authorize_runs_once(self):
        calls = []

        class Counting(FormRequest):
            def authorize(self):
                calls.append(1)
                return True

        form = Counting({"a": 1})
        form.validated()
        form.validated()
        assert len(calls) == 1
