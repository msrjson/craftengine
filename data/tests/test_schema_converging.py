"""The converging schema builder: alter an existing column's type,
nullability and default in place, rename a column, and add a constraint
idempotently. PostgreSQL only — SQLite cannot alter a column in place
without rebuilding the table, so it refuses rather than attempting it.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import uuid

import pytest

from craft.migrations.schema import SchemaBuilder
from craft.orm.dialect import UnsupportedFeatureError


@pytest.fixture
def widgets() -> str:
    """A table name no other test or session uses.

    NR-02: the table is never dropped. Each test alters its table, so each
    gets a fresh one under a name of its own.
    """
    return f"converging_widgets_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def widgets_table(migrated_database, is_postgres, widgets):
    schema = SchemaBuilder(migrated_database.make("db"))
    schema.create_table(widgets, lambda t: (
        t.id(type="integer"),
        t.string("name", 50),
        t.integer("quantity").nullable(),
    ))
    return schema


def _column_info(migrated_database, table, column):
    row = migrated_database.make("db").select_one(
        "SELECT data_type, is_nullable, column_default FROM information_schema.columns "
        "WHERE table_name = ? AND column_name = ?",
        [table, column],
    )
    return dict(row) if row else None


class TestChangeColumnType:
    def test_widens_an_integer_column_to_bigint(self, widgets_table, widgets, migrated_database, is_postgres):
        if not is_postgres:
            pytest.skip("PostgreSQL only")
        widgets_table.change_column(widgets, "quantity", type="big_integer")
        info = _column_info(migrated_database, widgets, "quantity")
        assert info["data_type"] == "bigint"

    def test_raises_on_sqlite(self, widgets_table, widgets, migrated_database, is_postgres):
        if is_postgres:
            pytest.skip("this is the SQLite-refusal test")
        with pytest.raises(UnsupportedFeatureError):
            widgets_table.change_column(widgets, "quantity", type="big_integer")


class TestChangeColumnNullability:
    def test_makes_a_nullable_column_not_null(self, widgets_table, widgets, migrated_database, is_postgres):
        if not is_postgres:
            pytest.skip("PostgreSQL only")
        migrated_database.make("db").table(widgets).insert({"name": "w1", "quantity": 1})
        widgets_table.change_column(widgets, "quantity", nullable=False)
        info = _column_info(migrated_database, widgets, "quantity")
        assert info["is_nullable"] == "NO"

    def test_makes_a_not_null_column_nullable_again(self, widgets_table, widgets, migrated_database, is_postgres):
        if not is_postgres:
            pytest.skip("PostgreSQL only")
        widgets_table.change_column(widgets, "name", nullable=False)
        widgets_table.change_column(widgets, "name", nullable=True)
        info = _column_info(migrated_database, widgets, "name")
        assert info["is_nullable"] == "YES"


class TestChangeColumnDefault:
    def test_sets_a_default(self, widgets_table, widgets, migrated_database, is_postgres):
        if not is_postgres:
            pytest.skip("PostgreSQL only")
        widgets_table.change_column(widgets, "quantity", default=0)
        info = _column_info(migrated_database, widgets, "quantity")
        assert info["column_default"] is not None
        assert "0" in info["column_default"]

    def test_drops_a_default_with_none(self, widgets_table, widgets, migrated_database, is_postgres):
        if not is_postgres:
            pytest.skip("PostgreSQL only")
        widgets_table.change_column(widgets, "quantity", default=0)
        widgets_table.change_column(widgets, "quantity", default=None)
        info = _column_info(migrated_database, widgets, "quantity")
        assert info["column_default"] is None


class TestRenameColumn:
    def test_renames_a_column(self, widgets_table, widgets, migrated_database, is_postgres):
        widgets_table.rename_column(widgets, "name", "label")
        columns = widgets_table.column_listing(widgets)
        assert "label" in columns
        assert "name" not in columns


class TestAddConstraintIfMissing:
    def test_adds_a_missing_constraint(self, widgets_table, widgets, migrated_database, is_postgres):
        if not is_postgres:
            pytest.skip("PostgreSQL only")
        widgets_table.add_constraint_if_missing(
            widgets, f"ck_{widgets}_quantity_non_negative",
            "CHECK (quantity >= 0)",
        )
        db = migrated_database.make("db")
        db.table(widgets).insert({"name": "w1", "quantity": 1})
        with pytest.raises(Exception):
            db.table(widgets).insert({"name": "w2", "quantity": -1})

    def test_a_second_call_is_a_no_op_not_an_error(self, widgets_table, widgets, migrated_database, is_postgres):
        if not is_postgres:
            pytest.skip("PostgreSQL only")
        widgets_table.add_constraint_if_missing(
            widgets, f"ck_{widgets}_quantity_non_negative_2",
            "CHECK (quantity >= 0)",
        )
        # Must not raise the second time.
        widgets_table.add_constraint_if_missing(
            widgets, f"ck_{widgets}_quantity_non_negative_2",
            "CHECK (quantity >= 0)",
        )
