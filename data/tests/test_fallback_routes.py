"""A fallback route answers last, whatever order it was registered in."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest
from starlette.testclient import TestClient

from bootstrap.app import asgi_app
from craft.facades import Route


@pytest.fixture(scope="module", autouse=True)
def fallback_routes(migrated_database):
    def specific(request):
        return {"route": "specific"}

    def catch_all(request):
        return {"route": "fallback"}

    # Deliberately registered before the specific route: by registration order
    # the catch-all would shadow it, and the kernel must place it last anyway.
    Route.fallback("/t-fallback/{path:path}", catch_all).name("t.fallback.all")
    Route.get("/t-fallback/specific", specific).name("t.fallback.specific")
    yield


@pytest.fixture
def client():
    return TestClient(asgi_app)


def test_a_specific_route_wins_over_a_fallback_registered_first(client):
    response = client.get("/t-fallback/specific")
    assert response.status_code == 200
    assert response.json() == {"route": "specific"}


def test_the_fallback_answers_what_nothing_else_claimed(client):
    response = client.get("/t-fallback/something/else")
    assert response.status_code == 200
    assert response.json() == {"route": "fallback"}


def test_the_fallback_is_marked_as_such(migrated_database):
    router = migrated_database.make("router")
    entry = next(r for r in router.routes if r._name == "t.fallback.all")
    assert entry.is_fallback is True
    assert entry.describe()["fallback"] is True
