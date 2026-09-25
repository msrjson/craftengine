"""SetLocale: resolving and remembering the visitor's language."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest
from starlette.testclient import TestClient

from bootstrap.app import app, asgi_app
from craft.facades import Route
from craft.http.middleware import SetLocale


@pytest.fixture(scope="module", autouse=True)
def routes(migrated_database):
    def show_locale(request):
        # Read what the request actually resolved to, not the process-wide
        # config — that distinction is the point of the middleware.
        from craft.support.translation import get_current_locale

        return {"locale": get_current_locale()}

    Route.get("/t/locale", show_locale).name("t.locale")
    yield


@pytest.fixture
def client():
    return TestClient(asgi_app)


@pytest.fixture(autouse=True)
def restore_locale(migrated_database):
    config = migrated_database.make("config")
    original = config.get("app.APP_LOCALE")
    yield
    config.set("app.APP_LOCALE", original)


class TestQueryParameter:
    def test_lang_sets_the_locale(self, client):
        assert client.get("/t/locale?lang=pt-BR").json()["locale"] == "pt-BR"

    def test_casing_is_normalised(self, client):
        assert client.get("/t/locale?lang=PT-br").json()["locale"] == "pt-BR"

    def test_an_unsupported_locale_is_ignored(self, client):
        client.get("/t/locale?lang=en")
        assert client.get("/t/locale?lang=kl").json()["locale"] == "en"

    @pytest.mark.parametrize("tag", ["en", "pt-BR", "es"])
    def test_every_offered_locale_is_accepted(self, client, tag):
        assert client.get(f"/t/locale?lang={tag}").json()["locale"] == tag


class TestPersistence:
    def test_the_choice_survives_the_next_request(self, client):
        client.get("/t/locale?lang=es")
        # The whole point of the switcher: no ?lang= on the next navigation.
        assert client.get("/t/locale").json()["locale"] == "es"

    def test_switching_again_replaces_it(self, client):
        client.get("/t/locale?lang=es")
        client.get("/t/locale?lang=pt-BR")
        assert client.get("/t/locale").json()["locale"] == "pt-BR"

    def test_one_visitors_choice_does_not_affect_another(self, client):
        client.get("/t/locale?lang=es")
        stranger = TestClient(asgi_app)
        assert stranger.get("/t/locale").json()["locale"] != "es"


class TestAcceptLanguage:
    def test_the_header_is_honoured(self, client):
        response = client.get("/t/locale", headers={"Accept-Language": "es-ES,es;q=0.9"})
        assert response.json()["locale"] == "es"

    def test_a_sibling_variant_is_served_when_the_tag_is_not_offered(self, client):
        # Neither pt-PT nor pt is offered; pt-BR is the closest Portuguese.
        response = client.get("/t/locale", headers={"Accept-Language": "pt-PT,pt;q=0.9"})
        assert response.json()["locale"] == "pt-BR"

    def test_a_regional_tag_falls_back_to_its_base(self):
        assert SetLocale._match("es-MX", ["en", "es"]) == "es"

    def test_an_exact_regional_match_wins(self, client):
        response = client.get("/t/locale", headers={"Accept-Language": "pt-BR,pt;q=0.9"})
        assert response.json()["locale"] == "pt-BR"

    def test_an_unsupported_header_leaves_the_default(self, client):
        client.get("/t/locale?lang=en")
        response = client.get("/t/locale", headers={"Accept-Language": "kl-GL"})
        assert response.json()["locale"] == "en"

    def test_the_query_parameter_beats_the_header(self, client):
        response = client.get(
            "/t/locale?lang=pt", headers={"Accept-Language": "es-ES,es;q=0.9"}
        )
        assert response.json()["locale"] == "pt-BR"


class TestUnit:
    def test_supported_comes_from_config(self, migrated_database):
        assert SetLocale(migrated_database).supported() == ["en", "pt-BR", "es"]

    def test_supported_can_be_overridden(self):
        assert SetLocale(supported=["en", "fr"]).supported() == ["en", "fr"]
