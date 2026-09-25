"""Tests for Vector & Semantic Search in Craft ORM and QueryBuilder."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import json
import uuid

import pytest
from craft.facades import DB, Schema
from craft.orm.model import Model


class Article(Model):
    __table__ = "articles"
    fillable = ["title", "content", "embedding", "published"]


@pytest.fixture
def articles_table(migrated_database, monkeypatch):
    """Three seeded articles in a table of this test's own.

    NR-02: the table is never dropped. A fresh name per test keeps each test's
    count of three exact; the model is pointed at it for the test's duration.
    """
    table = f"articles_{uuid.uuid4().hex[:8]}"
    monkeypatch.setattr(Article, "__table__", table)
    Schema.create_table(table, lambda t: (
        t.id(),
        t.string("title"),
        t.text("content"),
        t.text("embedding"),
        t.boolean("published").default(True),
        t.timestamps(),
    ))

    # Seed 3 articles with mock 4-dimension normalized embeddings:
    # 1. Tech article vector: [1.0, 0.0, 0.0, 0.0]
    # 2. Science article vector: [0.8, 0.6, 0.0, 0.0] (sim with Tech: 0.8)
    # 3. Cooking article vector: [0.0, 0.0, 1.0, 0.0] (sim with Tech: 0.0)
    Article.create({
        "title": "Quantum Computing Tech",
        "content": "Superconductors and qubits.",
        "embedding": json.dumps([1.0, 0.0, 0.0, 0.0]),
        "published": True,
    })
    Article.create({
        "title": "Astrophysics and Stars",
        "content": "Galaxies and light years.",
        "embedding": json.dumps([0.8, 0.6, 0.0, 0.0]),
        "published": True,
    })
    Article.create({
        "title": "Italian Pasta Recipe",
        "content": "Flour, eggs, and olive oil.",
        "embedding": json.dumps([0.0, 0.0, 1.0, 0.0]),
        "published": False,
    })

    return table


class TestVectorSearch:
    def test_where_vector_similar_filters_correctly(self, articles_table):
        # Query near Tech vector: [1.0, 0.0, 0.0, 0.0]
        # min_similarity = 0.75 should match Tech (1.0) and Science (0.8), but NOT Cooking (0.0)
        query_vec = [1.0, 0.0, 0.0, 0.0]
        results = Article.where_vector_similar("embedding", query_vec, min_similarity=0.75).get()

        assert len(results) == 2
        titles = [r.title for r in results]
        assert "Quantum Computing Tech" in titles
        assert "Astrophysics and Stars" in titles
        assert "Italian Pasta Recipe" not in titles

    def test_order_by_vector_similarity(self, articles_table):
        query_vec = [1.0, 0.0, 0.0, 0.0]
        results = Article.order_by_vector_similarity("embedding", query_vec).get()

        assert len(results) == 3
        # Most similar first:
        assert results[0].title == "Quantum Computing Tech"
        assert results[0].similarity_score == pytest.approx(1.0)

        assert results[1].title == "Astrophysics and Stars"
        assert results[1].similarity_score == pytest.approx(0.8)

        assert results[2].title == "Italian Pasta Recipe"
        assert results[2].similarity_score == pytest.approx(0.0)

    def test_combined_vector_and_standard_sql_filters(self, articles_table):
        # Filter only published articles similar to [0.0, 0.0, 1.0, 0.0]
        # Pasta recipe has vector [0.0, 0.0, 1.0, 0.0] but published=False
        query_vec = [0.0, 0.0, 1.0, 0.0]
        results = Article.where("published", True) \
            .where_vector_similar("embedding", query_vec, min_similarity=0.5) \
            .get()

        assert len(results) == 0
