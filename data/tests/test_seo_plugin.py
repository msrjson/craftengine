"""Tests for the cookieless SEO plugin (`plugins/seo/`)."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import os

from engine.plugins.manager import PluginManager
from plugins.seo import Seo


class TestSlugify:
    def test_accents_are_folded_and_words_hyphenated(self):
        assert Seo.slugify("Ação e Reação") == "acao-e-reacao"

    def test_punctuation_is_dropped(self):
        assert Seo.slugify("Craft Engine: the 1st!") == "craft-engine-the-1st"


class TestMetadata:
    def test_meta_description_is_trimmed_on_a_word_boundary(self):
        body = "palavra " * 40
        description = Seo.meta_description(body, limit=20)
        assert len(description) <= 21
        assert description.endswith("…") and not description.endswith(" …")

    def test_canonical_is_absolute_against_the_base(self):
        assert Seo.canonical("/docs", "https://example.com") == "https://example.com/docs"

    def test_canonical_keeps_an_absolute_url(self):
        assert Seo.canonical("https://other.test/x", "https://example.com") == "https://other.test/x"

    def test_head_carries_description_robots_and_canonical(self):
        head = Seo.head("Título", "corpo da página", url="/p", base="https://example.com")
        assert head["description"] == "corpo da página"
        assert head["robots"] == "index, follow"
        assert head["canonical"] == "https://example.com/p"

    def test_a_private_page_is_noindex(self):
        assert Seo.robots(index=False) == "noindex, follow"


class TestAudit:
    def test_a_short_title_and_thin_body_are_flagged_by_key(self):
        audit = Seo.audit("Curto", "poucas palavras")
        assert "seo.suggestion.title_too_short" in audit.suggestions
        assert "seo.suggestion.content_thin" in audit.suggestions
        assert audit.slug == "curto"

    def test_a_long_title_is_flagged(self):
        audit = Seo.audit("t" * 80, "corpo")
        assert "seo.suggestion.title_too_long" in audit.suggestions


class TestPluginWiring:
    def test_the_plugin_is_discoverable_on_disk(self):
        slugs = {descriptor["slug"] for descriptor in PluginManager().discover(os.getcwd())}
        assert "seo" in slugs

    def test_register_binds_the_service_in_the_container(self):
        from bootstrap.app import app
        from plugins.seo.plugin import register

        register(app)
        assert isinstance(app.make("seo"), Seo)
