"""Unit tests for Server-Side DataGrid Engine."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from engine.http.datagrid import (
    OPERATORS_BY_KIND,
    GridColumn,
    GridQuery,
)


class DummyRequest:
    """Mock Starlette Request for query parameters."""

    def __init__(self, query_params: dict):
        self.query_params = query_params


def test_grid_column_initialization_and_operators():
    """Verify GridColumn properties and permitted operators per family."""
    col_text = GridColumn("title", "Title", kind="text")
    col_money = GridColumn("amount", "Amount", kind="money")

    assert col_text.family == "text"
    assert "contains" in col_text.to_dict()["operators"]
    assert col_money.family == "number"
    assert col_money.aggregate == "sum"
    assert "between" in col_money.to_dict()["operators"]


def test_grid_query_compilation_with_allowed_filters():
    """Verify GridQuery compiles valid WHERE clauses and discards undeclared filters."""
    columns = [
        GridColumn("title", "Title", kind="text"),
        GridColumn("status", "Status", kind="select"),
        GridColumn("amount", "Amount", kind="money"),
    ]

    req = DummyRequest(
        {
            "fc": ["title", "status", "malicious_col"],
            "fo": ["contains", "eq", "eq"],
            "fv": ["Craft", "active", "drop table"],  # nr02: hostile filter value, passed as a bound parameter
        }
    )

    query = GridQuery(columns, req, dialect="postgres")
    where_sql, params = query.where()

    # Malicious column was discarded (allowlist enforcement)
    assert len(query.filters) == 2
    assert "malicious_col" not in where_sql
    assert '"title"::text ILIKE ?' in where_sql
    assert '"status" = ?' in where_sql
    assert params == ["%Craft%", "active"]


def test_grid_query_sorting_and_grouping():
    """Verify order_by and group_column resolution."""
    columns = [
        GridColumn("created_at", "Created At", kind="date", sortable=True),
        GridColumn("category", "Category", kind="select", groupable=True),
    ]

    req = DummyRequest(
        {
            "sort": "created_at",
            "dir": "desc",
            "group": "category",
        }
    )

    query = GridQuery(columns, req)
    order_sql, sort_col, direction = query.order_by()

    assert sort_col == "created_at"
    assert direction == "DESC"
    assert '"category" ASC NULLS LAST' in order_sql
    assert '"created_at" DESC NULLS LAST, id DESC' in order_sql


def test_grid_query_empty_filter_safety():
    """Verify empty filter query produces empty WHERE fragment."""
    columns = [GridColumn("name", "Name")]
    req = DummyRequest({})
    query = GridQuery(columns, req)

    where_sql, params = query.where()
    assert where_sql == ""
    assert params == []
