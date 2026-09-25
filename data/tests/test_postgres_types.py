"""Tests for attribute casting and the PostgreSQL query macros.

Phase 5 of the PostgreSQL-native data layer. The macros compile to SQL on every
driver's grammar but only *run* where the capability exists, so most assertions
here are on the compiled statement and its bindings — which is also where the
security property lives: the operator is a literal, the identifier is checked,
the value is a binding.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import json

import pytest

from craft.migrations.schema import Blueprint, Grammar
from craft.orm.casts import (
    ArrayCast,
    JsonbCast,
    RangeCast,
    VectorCast,
    resolve_cast,
    vector_literal,
)
from craft.orm.dialect import PostgresDialect, SqliteDialect, UnsupportedFeatureError
from craft.orm.expression import Raw
from craft.orm.model import Model
from craft.orm.query_builder import QueryBuilder


class _Db:
    """Minimal database stand-in that only has to answer capability questions."""

    def __init__(self, dialect=None, driver="postgresql"):
        self.dialect = dialect or PostgresDialect()
        self.driver = driver


def builder(table="documents", dialect=None):
    return QueryBuilder(table_name=table, db=_Db(dialect))


# -- casts ---------------------------------------------------------------------


def test_jsonb_round_trips_on_both_drivers():
    cast = JsonbCast()
    value = {"plan": "pro", "seats": 12}

    # SQLite stores text and hands text back.
    stored = cast.dehydrate(value, "sqlite")
    assert isinstance(stored, str)
    assert cast.hydrate(stored, "sqlite") == value

    # psycopg2 decodes on the way out, so hydrate must be a no-op there.
    assert cast.hydrate(value, "postgresql") == value


def test_jsonb_hydrate_keeps_a_value_it_cannot_parse():
    # Better than replacing a readable value with None.
    assert JsonbCast().hydrate("not json", "sqlite") == "not json"


def test_array_round_trips_and_types_its_elements():
    cast = ArrayCast("int")
    stored = cast.dehydrate([1, 2, 3], "sqlite")
    assert cast.hydrate(stored, "sqlite") == [1, 2, 3]

    # psycopg2 adapts a list natively, so nothing is encoded.
    assert cast.dehydrate([1, 2], "postgresql") == [1, 2]


def test_range_renders_half_open():
    """Adjacent ranges must neither overlap nor leave a gap."""
    rendered = RangeCast("tsrange").dehydrate(("2026-08-20", "2026-08-21"), "postgresql")
    assert rendered == "[2026-08-20,2026-08-21)"


def test_an_unbounded_range_end_is_empty_not_none():
    assert RangeCast("int4range").dehydrate((1, None), "postgresql") == "[1,)"


def test_an_unknown_range_type_is_refused():
    with pytest.raises(ValueError):
        RangeCast("wobblerange")


def test_vector_round_trips_through_its_literal():
    assert vector_literal([0.5, -1.0]) == "[0.5,-1.0]"
    assert VectorCast().hydrate("[0.5,-1.0]", "postgresql") == [0.5, -1.0]


def test_an_unknown_cast_raises_instead_of_being_ignored():
    with pytest.raises(ValueError, match="Unknown cast"):
        resolve_cast("jsonbb")


def test_a_model_hydrates_and_dehydrates_its_casts():
    class Account(Model):
        __table__ = "accounts"
        casts = {"meta": "jsonb", "tags": "array:str"}

    account = Account({"meta": '{"plan":"pro"}', "tags": '["a","b"]'})
    assert account.get_attribute("meta") == {"plan": "pro"}
    assert account.get_attribute("tags") == ["a", "b"]

    written = Account._dehydrate(dict(account._attributes))
    # Encoded for whichever driver is active: text on SQLite, psycopg2's Json
    # adapter on PostgreSQL — which is the point of dehydrating at all.
    encoded = written["meta"]
    decoded = json.loads(encoded) if isinstance(encoded, str) else encoded.adapted
    assert decoded == {"plan": "pro"}

    # The model keeps the Python value — dehydration is for the write only.
    assert account.get_attribute("meta") == {"plan": "pro"}


# -- JSONB macros --------------------------------------------------------------


def test_json_contains_binds_the_document():
    sql, params = builder("accounts").where_json_contains("meta", {"plan": "pro"}).to_sql()

    assert "meta @> ?::jsonb" in sql
    assert json.loads(params[0]) == {"plan": "pro"}


def test_json_has_key_avoids_the_question_mark_operator():
    """`meta ? 'k'` collides with every driver's placeholder style."""
    sql, params = builder("accounts").where_json_has_key("meta", "plan").to_sql()

    assert "jsonb_exists(meta, ?)" in sql
    assert params == ["plan"]


def test_json_key_binds_the_path_as_an_array():
    sql, params = (
        builder("accounts").where_json_key("meta", "usage.seats", ">", "10").to_sql()
    )

    assert "meta #>> ? > ?" in sql
    assert params == [["usage", "seats"], "10"]


def test_json_key_refuses_an_operator_outside_the_allowlist():
    with pytest.raises(ValueError, match="Invalid SQL operator"):
        builder("accounts").where_json_key("meta", "plan", "; DROP TABLE users --", "x")  # nr02: hostile payload compiled to SQL, never executed


def test_json_path_binds_the_expression():
    sql, params = builder("orders").where_json_path("lines", "$[*] ? (@.qty > 100)").to_sql()

    assert "jsonb_path_exists(lines, ?::jsonpath)" in sql
    assert params == ["$[*] ? (@.qty > 100)"]


def test_a_macro_still_refuses_a_hostile_column_name():
    """The allowlists the macros go around are the ones they still obey."""
    with pytest.raises(ValueError, match="Invalid SQL identifier"):
        builder("accounts").where_json_contains("meta; DROP TABLE users --", {})  # nr02: hostile payload compiled to SQL, never executed


# -- arrays and ranges ---------------------------------------------------------


def test_array_contains_and_overlaps_use_the_right_operators():
    sql, params = builder("posts").where_array_contains("tags", ["a", "b"]).to_sql()
    assert "tags @> ?" in sql and params == [["a", "b"]]

    sql, params = builder("posts").where_array_overlaps("tags", ["a"]).to_sql()
    assert "tags && ?" in sql and params == [["a"]]


def test_array_has_uses_any():
    sql, params = builder("posts").where_array_has("tags", "python").to_sql()
    assert "? = ANY(tags)" in sql
    assert params == ["python"]


def test_range_overlaps_is_half_open():
    sql, params = (
        builder("bookings")
        .where_range_overlaps("period", "2026-08-20", "2026-08-21")
        .to_sql()
    )

    # `'[)'` is what makes a booking ending at 14:00 not clash with one
    # starting at 14:00.
    assert "period && tsrange(?, ?, '[)')" in sql
    assert params == ["2026-08-20", "2026-08-21"]


def test_range_contains_casts_to_the_element_type():
    sql, _ = builder("bookings").where_range_contains("span", 5, kind="int4range").to_sql()
    assert "span @> ?::int" in sql


# -- full-text search ----------------------------------------------------------


def test_search_defaults_to_websearch_syntax():
    """A search box must survive whatever a person types into it."""
    sql, params = builder("articles").where_search("doc", 'queue "skip locked"').to_sql()

    assert "doc @@ websearch_to_tsquery('english', ?)" in sql
    assert params == ['queue "skip locked"']


def test_search_language_comes_from_a_fixed_set():
    """A regconfig cannot be bound, so it must not come from a caller."""
    with pytest.raises(ValueError, match="Unknown text search language"):
        builder("articles").where_search("doc", "x", language="'; DROP TABLE users --")  # nr02: hostile payload compiled to SQL, never executed


def test_an_unknown_search_mode_is_refused():
    with pytest.raises(ValueError, match="Unknown search mode"):
        builder("articles").where_search("doc", "x", mode="magic")


def test_relevance_ranks_by_cover_density_and_projects_the_score():
    sql, params = builder("articles").order_by_relevance("doc", "queue").to_sql()

    assert "ts_rank_cd(doc, websearch_to_tsquery('english', ?)) AS relevance" in sql
    assert "ORDER BY ts_rank_cd(doc, websearch_to_tsquery('english', ?)) DESC" in sql
    # Bound twice, once per clause, in clause order.
    assert params == ["queue", "queue"]


# -- trigram -------------------------------------------------------------------


def test_similar_uses_an_explicit_threshold_not_the_session_setting():
    sql, params = builder("users").where_similar("name", "jonh doe", 0.25).to_sql()

    assert "similarity(name, ?) > ?" in sql
    assert params == ["jonh doe", 0.25]


def test_distance_orders_ascending():
    sql, _ = builder("users").order_by_distance("name", "jon").to_sql()
    assert "ORDER BY name <-> ? ASC" in sql


# -- vectors -------------------------------------------------------------------


def test_vector_search_compiles_to_the_distance_operator():
    query = builder("documents").order_by_vector_similarity("embedding", [1.0, 0.0])
    sql, params = query.to_sql()

    assert "embedding <=> ?::vector AS distance" in sql
    # Ascending distance is descending similarity, and the default is
    # most-similar-first.
    assert "ORDER BY embedding <=> ?::vector ASC" in sql
    assert params == ["[1.0,0.0]", "[1.0,0.0]"]


def test_a_similarity_floor_becomes_a_distance_ceiling():
    sql, params = (
        builder("documents")
        .where_vector_similar("embedding", [1.0, 0.0], min_similarity=0.7)
        .to_sql()
    )

    assert "(embedding <=> ?::vector) < ?" in sql
    assert params[1] == pytest.approx(0.3)


def test_an_unknown_metric_is_refused():
    with pytest.raises(ValueError, match="Unknown vector metric"):
        builder("documents").where_vector_similar("embedding", [1.0], metric="euclidish")


def test_vector_search_falls_back_to_python_without_pgvector():
    """The fallback exists for SQLite; it must not emit pgvector syntax."""
    query = builder("documents", dialect=SqliteDialect())
    query.order_by_vector_similarity("embedding", [1.0, 0.0])
    sql, _ = query.to_sql()

    assert "<=>" not in sql
    assert query._vector_orders


# -- capability gating ---------------------------------------------------------


@pytest.mark.parametrize("call", [
    lambda qb: qb.where_json_contains("meta", {}),
    lambda qb: qb.where_array_overlaps("tags", ["a"]),
    lambda qb: qb.where_range_overlaps("period", 1, 2),
    lambda qb: qb.where_search("doc", "x"),
    lambda qb: qb.where_similar("name", "x"),
])
def test_a_macro_refuses_a_driver_that_cannot_run_it(call):
    with pytest.raises(UnsupportedFeatureError):
        call(builder("t", dialect=SqliteDialect()))


# -- schema --------------------------------------------------------------------


def test_the_postgres_column_types_compile():
    blueprint = Blueprint("documents")
    blueprint.jsonb("payload")
    blueprint.array("tags", of="text")
    blueprint.tsrange("period")
    blueprint.vector("embedding", 1536)
    blueprint.timestamptz("occurred_at")
    blueprint.citext("email")

    sql = "\n".join(Grammar("postgresql").compile_create(blueprint))
    assert '"payload" JSONB' in sql
    assert '"tags" text[]' in sql
    assert '"period" TSRANGE' in sql
    assert '"embedding" VECTOR(1536)' in sql
    assert '"occurred_at" TIMESTAMPTZ' in sql
    assert '"email" CITEXT' in sql


def test_the_same_blueprint_still_builds_on_sqlite():
    """A migration written for PostgreSQL must not break development."""
    blueprint = Blueprint("documents")
    blueprint.jsonb("payload")
    blueprint.vector("embedding", 3)

    sql = "\n".join(Grammar("sqlite").compile_create(blueprint))
    assert '"payload" TEXT' in sql
    assert '"embedding" TEXT' in sql


def test_a_generated_tsvector_is_stored_weighted_and_null_safe():
    blueprint = Blueprint("articles")
    blueprint.string("title")
    blueprint.text("body")
    blueprint.tsvector("doc").generated_from({"title": "A", "body": "B"})

    sql = "\n".join(Grammar("postgresql").compile_create(blueprint))
    assert "GENERATED ALWAYS AS (" in sql and "STORED" in sql
    assert "setweight(to_tsvector('english', coalesce(\"title\", '')), 'A')" in sql
    # Without coalesce, one NULL source makes the whole document NULL and the
    # row disappears from every search.
    assert "coalesce(\"body\", '')" in sql


def test_a_bad_search_weight_is_refused():
    blueprint = Blueprint("articles")
    with pytest.raises(ValueError, match="weight"):
        blueprint.tsvector("doc").generated_from({"title": "Z"})


def test_a_raw_default_is_emitted_unquoted():
    blueprint = Blueprint("events")
    blueprint.uuid("id").primary().default(Raw("gen_random_uuid()"))

    sql = "\n".join(Grammar("postgresql").compile_create(blueprint))
    assert "DEFAULT gen_random_uuid()" in sql
    assert "'gen_random_uuid()'" not in sql
