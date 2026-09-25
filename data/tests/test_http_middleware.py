"""Session, CSRF and authentication across real HTTP requests."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import uuid

import pytest
from starlette.testclient import TestClient

from bootstrap.app import app, asgi_app
from craft.facades import DB, Route
from craft.http.middleware import Authenticate


@pytest.fixture(scope="module", autouse=True)
def routes(migrated_database):
    """Register throwaway routes exercising the middleware stack."""

    def counter(request):
        session = request.session()
        count = int(session.get("count", 0)) + 1
        session.put("count", count)
        return {"count": count}

    def echo(request):
        return {"input": request.all()}

    def whoami(request):
        user = request.user()
        return {"user": user.get_attribute("email") if user else None}

    def token(request):
        return {"token": request.session().token()}

    def flash_write(request):
        request.session().flash("status", "saved")
        return {"ok": True}

    def flash_read(request):
        return {"status": request.session().get("status")}

    def do_login(request):
        auth = app.make("auth")
        ok = auth.attempt(
            {"email": request.input("email"), "password": request.input("password")}
        )
        return {"ok": ok}

    def do_logout(request):
        app.make("auth").logout()
        return {"ok": True}

    Route.get("/t/counter", counter).name("t.counter")
    Route.get("/t/token", token).name("t.token")
    Route.get("/t/whoami", whoami).name("t.whoami")
    Route.get("/t/flash-read", flash_read).name("t.flash.read")
    Route.post("/t/echo", echo).name("t.echo")
    Route.post("/t/flash-write", flash_write).name("t.flash.write")
    Route.post("/t/login", do_login).name("t.login")
    Route.post("/t/logout", do_logout).name("t.logout")
    Route.post("/api/t/echo", echo).name("t.api.echo")
    yield


@pytest.fixture
def client():
    return TestClient(asgi_app)


@pytest.fixture
def user(migrated_database):
    from tests.support.models import User

    email = f"mw-{uuid.uuid4().hex[:8]}@craft.local"
    return User.create(
        {"name": "MW", "email": email, "password": "s3cret", "is_admin": False}
    )


def csrf_for(client) -> str:
    return client.get("/t/token").json()["token"]


class TestSessionAcrossRequests:
    def test_a_session_cookie_is_issued(self, client):
        response = client.get("/t/counter")
        assert "craft_session" in response.cookies

    def test_values_persist_between_requests(self, client):
        assert client.get("/t/counter").json()["count"] == 1
        assert client.get("/t/counter").json()["count"] == 2
        assert client.get("/t/counter").json()["count"] == 3

    def test_separate_clients_get_separate_sessions(self, client):
        other = TestClient(asgi_app)
        client.get("/t/counter")
        client.get("/t/counter")
        assert other.get("/t/counter").json()["count"] == 1

    def test_the_cookie_is_http_only(self, client):
        response = client.get("/t/counter")
        assert "httponly" in response.headers["set-cookie"].lower()

    def test_flash_data_lives_exactly_one_request(self, client):
        token = csrf_for(client)
        client.post("/t/flash-write", data={"_token": token})
        assert client.get("/t/flash-read").json()["status"] == "saved"
        assert client.get("/t/flash-read").json()["status"] is None


class TestCsrf:
    def test_post_without_a_token_is_rejected(self, client):
        client.get("/t/token")  # establish a session
        assert client.post("/t/echo", data={"a": "1"}).status_code == 419

    def test_post_with_the_form_token_is_accepted(self, client):
        token = csrf_for(client)
        response = client.post("/t/echo", data={"a": "1", "_token": token})
        assert response.status_code == 200

    def test_a_matching_origin_header_is_accepted(self, client):
        """Origin-based CSRF (Slice 2): the app's own origin, present and correct.

        The origin is derived from `app.APP_URL`, the value the middleware
        compares against. It used to be written as `http://localhost:9000`,
        which matched only a developer whose local `.env` set that port: the
        configured default is 8000, so the test failed on every clean checkout,
        CI included.
        """
        from urllib.parse import urlsplit

        from craft.facades import Config

        configured = urlsplit(str(Config.get("app.APP_URL")))
        token = csrf_for(client)
        response = client.post(
            "/t/echo",
            data={"a": "1", "_token": token},
            headers={"origin": f"{configured.scheme}://{configured.netloc}"},
        )
        assert response.status_code == 200

    def test_a_cross_site_origin_header_is_rejected_even_with_a_valid_token(self, client):
        """A stolen-token scenario: the token is right, but the browser itself
        says the request came from somewhere else - rejected on that alone.
        """
        token = csrf_for(client)
        response = client.post(
            "/t/echo",
            data={"a": "1", "_token": token},
            headers={"origin": "https://evil.example.com"},
        )
        assert response.status_code == 403

    def test_a_mismatched_referer_is_rejected_when_origin_is_absent(self, client):
        token = csrf_for(client)
        response = client.post(
            "/t/echo",
            data={"a": "1", "_token": token},
            headers={"referer": "https://evil.example.com/attack-page"},
        )
        assert response.status_code == 403

    def test_no_origin_or_referer_header_does_not_fail_on_its_own(self, client):
        """Some legitimate clients omit both - the token remains the primary check."""
        token = csrf_for(client)
        response = client.post("/t/echo", data={"a": "1", "_token": token})
        assert response.status_code == 200


class TestSecurityHeaders:
    def test_baseline_headers_are_present(self, client):
        response = client.get("/t/counter")
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["x-frame-options"] == "DENY"
        assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"

    def test_headers_are_present_on_error_responses_too(self, client):
        client.get("/t/token")  # establish a session
        response = client.post("/t/echo", data={"a": "1"})  # missing CSRF token -> 419
        assert response.status_code == 419
        assert response.headers["x-content-type-options"] == "nosniff"

    def test_csp_prefix_match_picks_the_longest_matching_prefix(self):
        from craft.http.middleware import SecurityHeaders

        class _Config:
            @staticmethod
            def get(key, default=None):
                values = {
                    "security.csp.prefixes": {
                        "/admin": "default-src 'self'",
                        "/admin/reports": "default-src 'none'",
                    },
                    "security.csp.default": "default-src *",
                }
                return values.get(key, default)

        headers = SecurityHeaders()
        assert headers._csp_for_path(_Config(), "/admin/reports/q4") == "default-src 'none'"
        assert headers._csp_for_path(_Config(), "/admin/dashboard") == "default-src 'self'"
        assert headers._csp_for_path(_Config(), "/blog/post-1") == "default-src *"

    def test_csp_falls_back_to_default_with_no_prefix_match(self):
        from craft.http.middleware import SecurityHeaders

        class _Config:
            @staticmethod
            def get(key, default=None):
                values = {"security.csp.prefixes": {}, "security.csp.default": "default-src 'self'"}
                return values.get(key, default)

        assert SecurityHeaders()._csp_for_path(_Config(), "/anything") == "default-src 'self'"

    def test_csp_is_absent_with_no_policy_configured(self):
        from craft.http.middleware import SecurityHeaders

        class _Config:
            @staticmethod
            def get(key, default=None):
                return default

        assert SecurityHeaders()._csp_for_path(_Config(), "/anything") is None

    def test_csp_header_is_sent_when_configured(self, client, migrated_database):
        config = migrated_database.make("config")
        original = config.get("security.csp.default")
        config.set("security.csp.default", "default-src 'self'")
        try:
            response = client.get("/t/counter")
            assert response.headers["content-security-policy"] == "default-src 'self'"
            assert "content-security-policy-report-only" not in response.headers
        finally:
            config.set("security.csp.default", original)

    def test_report_only_mode_sends_the_report_only_header_instead(self, client, migrated_database):
        config = migrated_database.make("config")
        original_default = config.get("security.csp.default")
        original_report_only = config.get("security.csp.report_only")
        config.set("security.csp.default", "default-src 'self'")
        config.set("security.csp.report_only", True)
        try:
            response = client.get("/t/counter")
            assert response.headers["content-security-policy-report-only"] == "default-src 'self'"
            assert "content-security-policy" not in response.headers
        finally:
            config.set("security.csp.default", original_default)
            config.set("security.csp.report_only", original_report_only)

    def test_report_uri_is_appended_to_the_policy(self, client, migrated_database):
        config = migrated_database.make("config")
        original_default = config.get("security.csp.default")
        original_uri = config.get("security.csp.report_uri")
        config.set("security.csp.default", "default-src 'self'")
        config.set("security.csp.report_uri", "/csp-reports")
        try:
            response = client.get("/t/counter")
            assert "report-uri /csp-reports" in response.headers["content-security-policy"]
        finally:
            config.set("security.csp.default", original_default)
            config.set("security.csp.report_uri", original_uri)


class _FakeConfig:
    def __init__(self, values):
        self._values = values

    def get(self, key, default=None):
        return self._values.get(key, default)


class _FakeApp:
    def __init__(self, config):
        self._config = config
        self.base_path = "."

    def make(self, name):
        if name == "config":
            return self._config
        raise KeyError(name)


class TestAppKeyEnforcement:
    def test_empty_app_key_in_production_fails_loudly(self):
        from craft.http.session import make_store

        app = _FakeApp(_FakeConfig({"app.APP_KEY": "", "app.APP_ENV": "production"}))
        with pytest.raises(RuntimeError):
            make_store(app)

    def test_empty_app_key_outside_production_falls_back_to_ephemeral(self):
        from craft.http.session import make_store

        app = _FakeApp(_FakeConfig({"app.APP_KEY": "", "app.APP_ENV": "testing"}))
        # Must not raise — the ephemeral per-process key is fine outside prod.
        store = make_store(app)
        assert store is not None

    def test_post_with_the_header_token_is_accepted(self, client):
        token = csrf_for(client)
        response = client.post("/t/echo", data={"a": "1"}, headers={"X-CSRF-TOKEN": token})
        assert response.status_code == 200

    def test_a_wrong_token_is_rejected(self, client):
        csrf_for(client)
        response = client.post("/t/echo", data={"_token": "forged"})
        assert response.status_code == 419

    def test_another_sessions_token_is_rejected(self, client):
        stolen = csrf_for(TestClient(asgi_app))
        csrf_for(client)
        assert client.post("/t/echo", data={"_token": stolen}).status_code == 419

    def test_get_requests_are_never_checked(self, client):
        assert client.get("/t/counter").status_code == 200

    def test_api_routes_are_exempt(self, client):
        response = client.post("/api/t/echo", json={"a": "1"})
        assert response.status_code == 200


class TestRequestInput:
    def test_form_body_is_parsed(self, client):
        token = csrf_for(client)
        response = client.post("/t/echo", data={"name": "jane", "_token": token})
        assert response.json()["input"]["name"] == "jane"

    def test_json_body_is_parsed(self, client):
        response = client.post("/api/t/echo", json={"name": "jane", "age": 30})
        assert response.json()["input"] == {"name": "jane", "age": 30}

    def test_query_string_is_merged(self, client):
        response = client.post("/api/t/echo?source=web", json={"name": "jane"})
        assert response.json()["input"]["source"] == "web"

    def test_malformed_json_does_not_crash(self, client):
        response = client.post(
            "/api/t/echo", content=b"{not json", headers={"content-type": "application/json"}
        )
        assert response.status_code == 200
        assert response.json()["input"] == {}


class TestAuthenticationAcrossRequests:
    def test_a_guest_has_no_user(self, client):
        assert client.get("/t/whoami").json()["user"] is None

    def test_login_survives_the_next_request(self, client, user):
        token = csrf_for(client)
        assert client.post(
            "/t/login",
            data={"email": user.get_attribute("email"), "password": "s3cret", "_token": token},
        ).json()["ok"] is True

        # The real proof: a *separate* request still knows who we are.
        assert client.get("/t/whoami").json()["user"] == user.get_attribute("email")

    def test_wrong_password_does_not_authenticate(self, client, user):
        token = csrf_for(client)
        client.post(
            "/t/login",
            data={"email": user.get_attribute("email"), "password": "wrong", "_token": token},
        )
        assert client.get("/t/whoami").json()["user"] is None

    def test_logout_ends_the_session(self, client, user):
        token = csrf_for(client)
        client.post(
            "/t/login",
            data={"email": user.get_attribute("email"), "password": "s3cret", "_token": token},
        )
        assert client.get("/t/whoami").json()["user"] == user.get_attribute("email")

        client.post("/t/logout", data={"_token": csrf_for(client)})
        assert client.get("/t/whoami").json()["user"] is None

    def test_one_clients_login_does_not_leak_to_another(self, client, user):
        token = csrf_for(client)
        client.post(
            "/t/login",
            data={"email": user.get_attribute("email"), "password": "s3cret", "_token": token},
        )
        stranger = TestClient(asgi_app)
        assert stranger.get("/t/whoami").json()["user"] is None

    def test_a_deleted_user_does_not_stay_authenticated(self, client, user):
        """The session keeps only the user id; once no row answers to it, the
        next request is a guest's. The row is moved to an id no sequence ever
        issues (its negation) instead of being deleted, which is the same
        condition for the session without destroying a record (NR-02)."""
        token = csrf_for(client)
        client.post(
            "/t/login",
            data={"email": user.get_attribute("email"), "password": "s3cret", "_token": token},
        )
        assert client.get("/t/whoami").json()["user"] == user.get_attribute("email")

        DB.statement("UPDATE users SET id = -id WHERE id = ?", [user.get_attribute("id")])
        assert client.get("/t/whoami").json()["user"] is None

    def test_login_rotates_the_session_id(self, client, user):
        before = client.get("/t/token")
        cookie_before = before.cookies.get("craft_session")

        token = csrf_for(client)
        after = client.post(
            "/t/login",
            data={"email": user.get_attribute("email"), "password": "s3cret", "_token": token},
        )
        assert after.cookies.get("craft_session") != cookie_before


class TestAuthMiddlewareUnits:
    def test_session_key_is_what_the_manager_writes(self, migrated_database, user):
        auth = migrated_database.make("auth")
        from craft.http.session import Session

        session = Session()
        auth.set_session(session)
        auth.login(user)

        assert session.get(Authenticate.SESSION_KEY) == user.get_attribute("id")

        auth.logout()
        assert session.get(Authenticate.SESSION_KEY) is None

    def test_reset_clears_memory_without_ending_the_session(self, migrated_database, user):
        auth = migrated_database.make("auth")
        from craft.http.session import Session

        session = Session()
        auth.set_session(session)
        auth.login(user)
        auth.reset()

        assert auth.check() is False
        # reset() must not erase the key the middleware is about to read.
        assert session.get(Authenticate.SESSION_KEY) == user.get_attribute("id")
