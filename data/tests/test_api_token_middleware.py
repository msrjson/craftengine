"""`AuthenticateApiToken` over real HTTP requests.

This middleware used to be a placebo: it resolved a user when a bearer token
happened to match an account, and called the next handler regardless. A route
carrying the `api` alias — including every write route the CRUD builder
generates, and `routes/api.py`'s own "writes require a valid API token" —
therefore accepted anonymous callers. Nothing tested it at runtime, which is
why the gap survived; these tests exist so it cannot come back.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import uuid

import pytest
from starlette.testclient import TestClient

from bootstrap.app import asgi_app
from craft.facades import Route


@pytest.fixture(scope="module", autouse=True)
def api_routes(migrated_database):
    def whoami(request):
        user = request.user()
        return {"user": user.get_attribute("email") if user else None}

    Route.get("/test-api/guarded", whoami).middleware("api").name("test.api.guarded")
    Route.get("/test-api/open", whoami).name("test.api.open")
    yield


@pytest.fixture
def api_user(migrated_database):
    """A user with an address and a token unique to this test."""
    from tests.support.models import User

    suffix = uuid.uuid4().hex[:8]
    return User.force_create({
        "name": "Api",
        "email": f"api-{suffix}@craft.local",
        "password": "s3cret",
        "api_token": f"valid-token-{suffix}",
    })


@pytest.fixture
def client():
    return TestClient(asgi_app)


class TestItRejects:
    def test_a_request_with_no_token_is_refused(self, client, api_user):
        response = client.get("/test-api/guarded", headers={"Accept": "application/json"})
        assert response.status_code in (401, 403)

    def test_a_request_with_an_unknown_token_is_refused(self, client, api_user):
        response = client.get(
            "/test-api/guarded",
            headers={"Authorization": "Bearer not-a-real-token", "Accept": "application/json"},
        )
        assert response.status_code in (401, 403)

    def test_it_does_not_reveal_whether_the_token_merely_existed(self, client, api_user):
        """Different responses for "no token" and "wrong token" would confirm
        which tokens are real, one probe at a time."""
        missing = client.get("/test-api/guarded", headers={"Accept": "application/json"})
        wrong = client.get(
            "/test-api/guarded",
            headers={"Authorization": "Bearer nope", "Accept": "application/json"},
        )
        assert missing.status_code == wrong.status_code


class TestItAdmits:
    def test_a_valid_token_is_authenticated_and_resolves_the_user(self, client, api_user):
        response = client.get(
            "/test-api/guarded",
            headers={
                "Authorization": f"Bearer {api_user.get_attribute('api_token')}",
                "Accept": "application/json",
            },
        )
        assert response.status_code == 200
        assert response.json()["user"] == api_user.get_attribute("email")

    def test_an_unguarded_route_is_unaffected(self, client, api_user):
        """The middleware must gate only the routes that opt in — hardening it
        should not have turned every route into an authenticated one."""
        response = client.get("/test-api/open", headers={"Accept": "application/json"})
        assert response.status_code == 200
