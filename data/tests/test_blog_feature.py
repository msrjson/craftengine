"""Test ORM Sluggable and Publishable Mixins."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest
from craft.migrations import Schema
from craft.orm import Model

from engine.orm.publishable import PublishableMixin
from engine.orm.sluggable import SluggableMixin, slugify


class CategoryModel(Model, SluggableMixin):
    __table__ = "test_categories"
    fillable = ["name", "slug"]
    slug_source_column = "name"


class ArticleModel(Model, SluggableMixin, PublishableMixin):
    __table__ = "test_articles"
    fillable = ["title", "slug", "content", "status", "published_at"]
    slug_source_column = "title"


@pytest.fixture(autouse=True)
def setup_test_tables(migrated_database):
    if not Schema.has_table("test_categories"):
        Schema.create(
            "test_categories",
            lambda t: (
                t.increments("id"),
                t.string("name"),
                t.string("slug").nullable(),
                t.timestamps(),
            ),
        )
    if not Schema.has_table("test_articles"):
        Schema.create(
            "test_articles",
            lambda t: (
                t.increments("id"),
                t.string("title"),
                t.string("slug").nullable(),
                t.text("content").nullable(),
                t.string("status").default("draft"),
                t.datetime("published_at").nullable(),
                t.timestamps(),
            ),
        )


def test_slugify_helper():
    """Verify slugify function handles special characters, accents, and spacing."""
    assert slugify("Hello World") == "hello-world"
    assert slugify("Craft Engine: AI Accelerator 2026!") == "craft-engine-ai-accelerator-2026"
    assert slugify("Açção & Integração") == "accao-integracao"
    assert slugify("") == ""


def test_sluggable_mixin_generate_slug():
    """Verify SluggableMixin generates unique slugs."""
    cat1 = CategoryModel({"name": "AI & Engineering"})
    cat1.generate_slug()
    cat1.save()
    assert cat1.slug == "ai-engineering"

    # Duplicate title must get auto-increment suffix
    cat2 = CategoryModel({"name": "AI & Engineering"})
    cat2.generate_slug()
    cat2.save()
    assert cat2.slug == "ai-engineering-1"

    found = CategoryModel.find_by_slug("ai-engineering")
    assert found is not None
    assert found.id == cat1.id


def test_publishable_mixin_scopes():
    """Verify PublishableMixin handles status and query scopes."""
    article1 = ArticleModel(
        {
            "title": "First Craft Article",
            "content": "Craft Engine rules.",
            "status": "draft",
        }
    )
    article1.generate_slug()
    article1.save()

    assert not article1.is_published
    assert len(ArticleModel.published().get()) == 0
    assert len(ArticleModel.drafts().get()) == 1

    article1.publish()
    assert article1.is_published
    assert len(ArticleModel.published().get()) == 1
    assert len(ArticleModel.drafts().get()) == 0
