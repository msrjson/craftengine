"""What a route action returns becomes a response, or a clear error."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest
from starlette.testclient import TestClient

from bootstrap.app import asgi_app
from craft.facades import Route


class _Row:
    def __init__(self, name):
        self.name = name

    def to_dict(self):
        return {"name": self.name}


class ResultController:
    def forgot_return(self, request):
        {"never": "returned"}

    def one_model(self, request):
        return _Row("single")

    def many_models(self, request):
        return [_Row("a"), _Row("b")]

    def index(self, request):
        return {"ok": True}


@pytest.fixture(scope="module", autouse=True)
def routes(migrated_database):
    Route.get("/api/t/results/none", [ResultController, "forgot_return"]).name("t.results.none")
    Route.get("/api/t/results/model", [ResultController, "one_model"]).name("t.results.model")
    Route.get("/api/t/results/models", [ResultController, "many_models"]).name("t.results.models")
    Route.get("/api/t/results/typo", [ResultController, "indx"]).name("t.results.typo")
    yield


@pytest.fixture
def client(migrated_database):
    """A JSON client with debug on: the developer's view of a failure, message included."""
    config = migrated_database.make("config")
    previous = config.get("app.APP_DEBUG")
    config.set("app.APP_DEBUG", True)
    yield TestClient(asgi_app, raise_server_exceptions=False, headers={"Accept": "application/json"})
    config.set("app.APP_DEBUG", previous)


def test_a_missing_return_is_an_error_not_a_page_reading_none(client):
    response = client.get("/api/t/results/none")
    assert response.status_code == 500
    assert "ROUTE_ACTION_RETURNED_NONE" in response.json()["message"]
    assert "None" != response.text


def test_a_model_is_sent_as_json(client):
    assert client.get("/api/t/results/model").json() == {"name": "single"}


def test_a_list_of_models_is_sent_as_json(client):
    assert client.get("/api/t/results/models").json() == [{"name": "a"}, {"name": "b"}]


def test_a_misspelled_action_names_the_closest_method(client):
    response = client.get("/api/t/results/typo")
    assert response.status_code == 500
    assert "Closest: index." in response.json()["message"]
