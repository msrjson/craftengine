"""The native MSR JSON manifest (https://msrjson.org) at /.well-known/msr.json.

The manifest is a trust artifact: registries and agents act on it without a
human checking. These cover that it is built only from what the project
declares, that an unresolvable required field refuses to publish instead of
guessing, and that the endpoint answers cross-origin as the protocol requires.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from pathlib import Path

import pytest
from starlette.testclient import TestClient

from bootstrap.app import app, asgi_app
from craft.support.msr import (
    MANIFEST_PATH,
    SCHEMA_URL,
    ManifestBuilder,
    ManifestIncompleteError,
    read_release_date,
    slugify,
)

COPY = {
    ("msr.entity.summary", "en"): "An application summary.",
    ("msr.entity.tagline", "en"): "An application tagline.",
    ("msr.entity.summary", "pt-BR"): "Um resumo da aplicação.",
}


def fake_translator(key: str, locale: str) -> str:
    return COPY.get((key, locale), key)


def settings(**overrides: object) -> dict:
    return {
        "URL": "https://shop.example.com",
        "NAME": "Example Shop",
        "TYPE": "saas",
        "DEPLOYMENT": ["cloud"],
        "LOCALES": ["en", "pt-BR", "es"],
        "VERSION": "1.4.0",
        "PUBLISHED_AT": "2026-09-01T00:00:00Z",
        **overrides,
    }


def build(**overrides: object) -> dict:
    return ManifestBuilder(settings(**overrides), Path("/nonexistent"), fake_translator).build()


class TestManifestBuilder:
    def test_builds_the_required_blocks_from_configuration(self):
        manifest = build()

        assert manifest["$schema"] == SCHEMA_URL
        assert manifest["protocol"]["author"] == "Antonio Santos"
        assert manifest["protocol"]["canonical_url"] == "https://shop.example.com/.well-known/msr.json"
        assert manifest["entity"]["slug"] == "example-shop"
        assert manifest["entity"]["domain"] == "shop.example.com"
        assert manifest["releases"]["latest"] == {"version": "1.4.0", "published_at": "2026-09-01T00:00:00Z"}

    def test_publishes_only_locales_that_have_a_summary(self):
        descriptions = build()["entity"]["descriptions"]

        assert set(descriptions) == {"en", "pt-BR"}
        assert descriptions["pt-BR"] == {"summary": "Um resumo da aplicação."}

    def test_omits_unknown_optional_fields_instead_of_guessing(self):
        manifest = build()

        assert "license" not in manifest["entity"]
        assert "vendor" not in manifest["entity"]
        assert "pricing" not in manifest["capabilities"]
        assert "trust" not in manifest

    def test_vendor_website_defaults_to_the_application_url(self):
        vendor = build(VENDOR={"name": "Example Ltd", "country_code": "BR"})["entity"]["vendor"]

        assert vendor == {"name": "Example Ltd", "country_code": "BR", "website": "https://shop.example.com"}

    def test_keeps_a_zero_starting_price(self):
        pricing = build(PRICING={"model": "free", "starting_price_cents": 0})["capabilities"]["pricing"]

        assert pricing == {"model": "free", "starting_price_cents": 0}

    @pytest.mark.parametrize("url", ["http://localhost:8000", "", "http://127.0.0.1"])
    def test_refuses_a_host_that_is_not_a_public_domain(self, url):
        with pytest.raises(ManifestIncompleteError) as error:
            build(URL=url)

        assert error.value.field == "entity.domain"

    def test_refuses_without_any_description(self):
        with pytest.raises(ManifestIncompleteError) as error:
            build(LOCALES=["es"])

        assert error.value.field == "entity.descriptions"

    def test_reads_version_and_date_from_the_project(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "shop"\nversion = "2.0.1"\n')
        (tmp_path / "CHANGELOG.md").write_text("## [Unreleased]\n\n## [2.0.1] r00003 — 2026-08-30\n")

        latest = ManifestBuilder(settings(VERSION="", PUBLISHED_AT=""), tmp_path, fake_translator).build()

        assert latest["releases"]["latest"] == {"version": "2.0.1", "published_at": "2026-08-30T00:00:00Z"}

    def test_an_undated_release_refuses_to_publish(self, tmp_path):
        (tmp_path / "CHANGELOG.md").write_text("## [Unreleased]\n")

        assert read_release_date(tmp_path, "2.0.1") is None
        with pytest.raises(ManifestIncompleteError):
            ManifestBuilder(settings(PUBLISHED_AT=""), tmp_path, fake_translator).build()

    def test_slug_is_lowercase_kebab_case(self):
        assert slugify("  Craft Engine / ERP 2 ") == "craft-engine-erp-2"


@pytest.fixture
def msr_config(migrated_database):
    """Publish the manifest for the duration of a test.

    Opt-in since 4.0.0: an application that never asked for it does not answer
    on the manifest path at all, so the endpoint tests have to turn it on and
    re-register the engine routes.
    """
    from bootstrap.app import kernel

    config = app.make("config")
    saved = {name: config.get(f"msr.{name}") for name in ("DOMAIN", "URL", "ENABLED")}
    config.set("msr.ENABLED", True)
    config.set("msr.DOMAIN", "shop.example.com")
    config.set("lang.en.msr.entity.summary", "An application summary.")
    kernel.register_engine_routes(refresh=True)
    yield config
    for name, value in saved.items():
        config.set(f"msr.{name}", value)
    config.set("lang.en.msr.entity.summary", None)
    kernel.register_engine_routes(refresh=True)


class TestManifestEndpoint:
    def test_serves_the_manifest_cross_origin(self, msr_config):
        response = TestClient(asgi_app).get(MANIFEST_PATH)

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        assert response.headers["access-control-allow-origin"] == "*"
        assert response.json()["entity"]["domain"] == "shop.example.com"

    def test_answers_404_when_the_domain_is_not_public(self, msr_config):
        msr_config.set("msr.DOMAIN", "")
        msr_config.set("msr.URL", "http://localhost:8000")

        assert TestClient(asgi_app).get(MANIFEST_PATH).status_code == 404
