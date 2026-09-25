"""QueryBuilder: SQL compilation and execution."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest

from craft.orm.db import DatabaseManager
from craft.orm.query_builder import QueryBuilder


@pytest.fixture
def db():
    manager = DatabaseManager(config={"driver": "sqlite", "database": ":memory:"})
    manager.statement(
        "CREATE TABLE widgets (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, "
        "price REAL, active INTEGER, owner_id INTEGER, updated_at TEXT)"
    )
    for name, price, active, owner in [
        ("alpha", 10.0, 1, 1),
        ("beta", 20.0, 0, 1),
        ("gamma", 30.0, 1, 2),
        ("delta", 40.0, 1, 2),
    ]:
        manager.statement(
            "INSERT INTO widgets (name, price, active, owner_id) VALUES (?, ?, ?, ?)",
            [name, price, active, owner],
        )
    return manager


@pytest.fixture
def query(db):
    return lambda: QueryBuilder(table_name="widgets", db=db)


class TestCompilation:
    def test_bare_select(self, query):
        sql, params = query().to_sql()
        assert sql == "SELECT * FROM widgets"
        assert params == []

    def test_where_uses_a_placeholder(self, query):
        sql, params = query().where("name", "alpha").to_sql()
        assert sql.endswith("WHERE name = ?")
        assert params == ["alpha"]

    def test_explicit_operator(self, query):
        sql, params = query().where("price", ">", 15).to_sql()
        assert "price > ?" in sql
        assert params == [15]

    def test_or_where_uses_or(self, query):
        sql, _ = query().where("a", 1).or_where("b", 2).to_sql()
        assert " OR " in sql

    def test_where_in_expands_placeholders(self, query):
        sql, params = query().where_in("id", [1, 2, 3]).to_sql()
        assert "id IN (?, ?, ?)" in sql
        assert params == [1, 2, 3]

    def test_empty_where_in_matches_nothing(self, query):
        sql, _ = query().where_in("id", []).to_sql()
        assert "1 = 0" in sql

    def test_null_checks_take_no_parameters(self, query):
        sql, params = query().where_null("name").to_sql()
        assert "name IS NULL" in sql
        assert params == []

    def test_between(self, query):
        sql, params = query().where_between("price", 10, 30).to_sql()
        assert "price BETWEEN ? AND ?" in sql
        assert params == [10, 30]

    def test_ordering_limit_and_offset(self, query):
        sql, _ = query().order_by_desc("price").limit(5).offset(10).to_sql()
        assert "ORDER BY price DESC" in sql
        assert "LIMIT 5" in sql
        assert "OFFSET 10" in sql

    def test_join_and_select_columns(self, query):
        sql, _ = (
            query().select("widgets.*").join("users", "users.id", "=", "widgets.owner_id").to_sql()
        )
        assert "INNER JOIN users ON users.id = widgets.owner_id" in sql
        assert "SELECT widgets.*" in sql

    def test_group_by_and_having(self, query):
        sql, params = query().group_by("owner_id").having("COUNT(*)", ">", 1).to_sql()
        assert "GROUP BY owner_id" in sql
        assert "HAVING COUNT(*) > ?" in sql
        assert params == [1]

    def test_distinct(self, query):
        sql, _ = query().distinct().to_sql()
        assert sql.startswith("SELECT DISTINCT")

    def test_where_not_equal_none_compiles_to_is_not_null(self, query):
        sql, params = query().where("name", "!=", None).to_sql()
        assert "name IS NOT NULL" in sql
        assert params == []

    def test_where_equal_none_compiles_to_is_null(self, query):
        sql, params = query().where("name", None).to_sql()
        assert "name IS NULL" in sql
        assert params == []

    def test_where_none_with_inequality_operator_raises(self, query):
        with pytest.raises(ValueError):
            query().where("price", ">", None)

    def test_or_where_parenthesises_earlier_conditions(self, query):
        sql, _ = (
            query().where_null("deleted_at").where("a", 1).or_where("b", 2).to_sql()
        )
        assert "(deleted_at IS NULL AND a = ?) OR b = ?" in sql

    def test_and_only_chains_are_unchanged(self, query):
        sql, _ = query().where("a", 1).where("b", 2).to_sql()
        assert sql.endswith("WHERE a = ? AND b = ?")

    def test_invalid_identifier_is_rejected(self, query):
        with pytest.raises(ValueError):
            query().where("name; DROP TABLE widgets", 1)  # nr02: hostile identifier, refused before any SQL runs
        with pytest.raises(ValueError):
            query().order_by("price; --")

    def test_invalid_operator_is_rejected(self, query):
        builder = query()
        builder._wheres.append(
            {"boolean": "AND", "column": "name", "operator": "= 1 OR 1", "value": 1}
        )
        with pytest.raises(ValueError):
            builder.to_sql()


class TestExecution:
    def test_get_returns_every_row(self, query):
        assert len(query().get()) == 4

    def test_where_filters(self, query):
        assert len(query().where("active", 1).get()) == 3

    def test_first_returns_one_row(self, query):
        assert query().where("name", "alpha").first()["price"] == 10.0

    def test_first_returns_none_when_empty(self, query):
        assert query().where("name", "nope").first() is None

    def test_count(self, query):
        assert query().count() == 4
        assert query().where("owner_id", 2).count() == 2

    def test_aggregates(self, query):
        assert query().sum("price") == 100.0
        assert query().max("price") == 40.0
        assert query().min("price") == 10.0
        assert query().avg("price") == 25.0

    def test_aggregate_ignores_ordering(self, query):
        assert query().order_by_desc("price").count() == 4

    def test_exists(self, query):
        assert query().where("name", "alpha").exists() is True
        assert query().where("name", "nope").exists() is False

    def test_pluck(self, query):
        assert sorted(query().pluck("name")) == ["alpha", "beta", "delta", "gamma"]

    def test_insert_returns_the_new_id(self, query):
        new_id = query().insert({"name": "epsilon", "price": 50.0, "active": 1})
        assert new_id is not None
        assert query().where("id", new_id).first()["name"] == "epsilon"

    def test_update_returns_affected_rows(self, query):
        affected = query().where("owner_id", 2).update({"active": 0})
        assert affected == 2
        assert query().where("active", 1).count() == 1

    def test_model_update_stamps_updated_at(self, db):
        class Widget:
            __table__ = "widgets"
            primary_key = "id"

            @classmethod
            def get_table_name(cls):
                return "widgets"

            def __init__(self, attributes):
                self._attributes = attributes

            def get_attribute(self, key):
                return self._attributes.get(key)

            def __getitem__(self, key):
                return self._attributes[key]

        builder = QueryBuilder(model_class=Widget, db=db)
        builder.where("name", "alpha").update({"price": 11.0})
        row = QueryBuilder(table_name="widgets", db=db).where("name", "alpha").first()
        assert row["updated_at"] is not None

    def test_raw_table_update_does_not_inject_updated_at(self, query):
        # Raw builders (pivot tables etc.) must not get a phantom updated_at.
        query().where("name", "beta").update({"price": 21.0})
        assert query().where("name", "beta").first()["updated_at"] is None

    def test_delete_only_removes_matching_rows(self, query):
        query().where("active", 0).delete()  # nr02: private in-memory SQLite, not the shared database
        assert query().count() == 3

    def test_delete_without_where_clears_the_table(self, query):
        query().delete()  # nr02: private in-memory SQLite, not the shared database
        assert query().count() == 0


    def test_first_does_not_stick_a_limit_on_the_builder(self, query):
        builder = query()
        builder.first()
        assert builder._limit is None
        assert len(builder.get()) == 4

    def test_count_ignores_group_by(self, query):
        assert query().group_by("owner_id").count() == 4

    def test_find_honors_a_custom_primary_key(self, db):
        db.statement("CREATE TABLE codes (code TEXT PRIMARY KEY, label TEXT)")
        db.statement("INSERT INTO codes (code, label) VALUES ('x1', 'one')")

        class Code:
            primary_key = "code"

            @classmethod
            def get_table_name(cls):
                return "codes"

            def __init__(self, attributes):
                self._attributes = attributes

            def get_attribute(self, key):
                return self._attributes.get(key)

        found = QueryBuilder(model_class=Code, db=db).find("x1")
        assert found is not None
        assert found.get_attribute("label") == "one"


class TestPagination:
    def test_paginate_limits_the_page(self, query):
        page = query().order_by("id").paginate(per_page=2, page=1)
        assert len(page) == 2
        assert page[0]["name"] == "alpha"

    def test_paginate_offsets_later_pages(self, query):
        page = query().order_by("id").paginate(per_page=2, page=2)
        assert page[0]["name"] == "gamma"

    def test_pagination_metadata(self, query):
        page = query().paginate(per_page=3, page=1)
        assert page.pagination == {
            "total": 4,
            "per_page": 3,
            "current_page": 1,
            "last_page": 2,
        }

    def test_page_zero_is_clamped_to_one(self, query):
        page = query().order_by("id").paginate(per_page=2, page=0)
        assert page.pagination["current_page"] == 1
        assert page[0]["name"] == "alpha"
