"""Authentication URLs must match the starter's documented route contract."""

from starlette.testclient import TestClient

from bootstrap.app import app, asgi_app


def test_signin_redirects_to_the_named_login_route(migrated_database) -> None:
    """A mistaken navigation link reaches the canonical login form."""
    router = app.make("router")
    client = TestClient(asgi_app)
    response = client.get("/signin", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == router.url_for("login") == "/login"


def test_login_submission_remains_on_the_protected_post_route(migrated_database) -> None:
    """The alias does not create another credential submission endpoint."""
    routes = app.make("router").routes
    login_post = next(route for route in routes if route.uri == "/login" and "POST" in route.methods)
    signin = next(route for route in routes if route.uri == "/signin")

    assert login_post._name == "login.attempt"
    assert "throttle" in login_post.middleware_list
    assert signin.methods == ["GET", "HEAD"]
