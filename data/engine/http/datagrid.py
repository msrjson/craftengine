"""Server-side DataGrid engine: filter compiler, sorting, and aggregate subtotals.

Category: Core Framework (HTTP).
Relations:
  - Consumed by resource controllers, custom listing handlers, and report generators.
  - Generates parameterized SQL WHERE fragments and aggregation queries.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

#: Maximum filters accepted in a single request to protect connection pool.
MAX_FILTERS = 12

#: Maximum values accepted in an `in` or `not_in` clause.
MAX_IN_VALUES = 200

#: Operators that require no value.
VALUELESS = ("empty", "not_empty")

#: Operators that require a range (two values).
RANGED = ("between",)

#: Column types treated as text.
TEXT_KINDS = (
    "text",
    "textarea",
    "select",
    "document",
    "email",
    "ie",
    "rg",
    "phone",
    "cep",
    "uuid",
)

NUMERIC_KINDS = ("number", "money")

DATE_KINDS = ("date", "datetime")

#: Allowed operators mapped to SQL templates.
OPERATORS = {
    "eq": "{column} = ?",
    "ne": "{column} <> ?",
    "contains": "{column}::text ILIKE ? ESCAPE '\\'",
    "not_contains": "{column}::text NOT ILIKE ? ESCAPE '\\'",
    "starts": "{column}::text ILIKE ? ESCAPE '\\'",
    "ends": "{column}::text ILIKE ? ESCAPE '\\'",
    "gt": "{column} > ?",
    "gte": "{column} >= ?",
    "lt": "{column} < ?",
    "lte": "{column} <= ?",
    "between": "{column} BETWEEN ? AND ?",
    "in": "{column}::text IN ({placeholders})",
    "not_in": "{column}::text NOT IN ({placeholders})",
    "empty": "({column} IS NULL OR {column}::text = '')",
    "not_empty": "({column} IS NOT NULL AND {column}::text <> '')",
}

#: SQLite-compatible operator templates.
SQLITE_OPERATORS = {
    "eq": "{column} = ?",
    "ne": "{column} <> ?",
    "contains": "CAST({column} AS TEXT) LIKE ? ESCAPE '\\'",
    "not_contains": "CAST({column} AS TEXT) NOT LIKE ? ESCAPE '\\'",
    "starts": "CAST({column} AS TEXT) LIKE ? ESCAPE '\\'",
    "ends": "CAST({column} AS TEXT) LIKE ? ESCAPE '\\'",
    "gt": "{column} > ?",
    "gte": "{column} >= ?",
    "lt": "{column} < ?",
    "lte": "{column} <= ?",
    "between": "{column} BETWEEN ? AND ?",
    "in": "CAST({column} AS TEXT) IN ({placeholders})",
    "not_in": "CAST({column} AS TEXT) NOT IN ({placeholders})",
    "empty": "({column} IS NULL OR CAST({column} AS TEXT) = '')",
    "not_empty": "({column} IS NOT NULL AND CAST({column} AS TEXT) <> '')",
}

#: Operators allowed per column type family.
OPERATORS_BY_KIND = {
    "text": (
        "contains",
        "not_contains",
        "eq",
        "ne",
        "starts",
        "ends",
        "in",
        "not_in",
        "empty",
        "not_empty",
    ),
    "number": ("eq", "ne", "gt", "gte", "lt", "lte", "between", "empty", "not_empty"),
    "date": ("eq", "ne", "gt", "gte", "lt", "lte", "between", "empty", "not_empty"),
    "bool": ("eq", "ne"),
    "select": ("eq", "ne", "in", "not_in", "empty", "not_empty"),
}

_TRUE_WORDS = ("1", "true", "t", "yes", "y", "on")

_ORDER_GROUP = "{column} ASC NULLS LAST"
_ORDER_COLUMN = "{column} {direction} NULLS LAST, id DESC"

_SUM_PROJECTION = ', COALESCE(SUM({column}), 0) AS "sum_{name}"'

_GROUP_QUERY = (
    "SELECT {column} AS value, count(*) AS n{sums} FROM {source}{where} "
    "GROUP BY {column} ORDER BY {column} ASC NULLS LAST LIMIT {limit}"
)

_TOTALS_QUERY = "SELECT count(*) AS n{sums} FROM {source}{where}"


def _quoted(column: GridColumn) -> str:
    """Return quoted column or custom expression."""
    return column.expression or f'"{column.name}"'


def _family(kind: str) -> str:
    """Return operator family for a given column kind."""
    if kind in NUMERIC_KINDS:
        return "number"
    if kind in DATE_KINDS:
        return "date"
    if kind == "bool":
        return "bool"
    if kind == "select":
        return "select"
    return "text"


def _like_pattern(operator: str, value: str) -> str:
    """Return escaped LIKE/ILIKE pattern for wildcards."""
    safe = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    if operator == "starts":
        return f"{safe}%"
    if operator == "ends":
        return f"%{safe}"
    return f"%{safe}%"


def _boolean(value: str) -> bool:
    """Coerce string into boolean."""
    return str(value).strip().lower() in _TRUE_WORDS


def _split_list(value: str) -> List[str]:
    """Split comma or newline-separated values for IN clauses."""
    parts = str(value or "").replace("\n", ",").replace(";", ",").split(",")
    return [p.strip() for p in parts if p.strip()][:MAX_IN_VALUES]


class GridColumn:
    """Definition of a listing column for filtering, sorting, and subtotals."""

    def __init__(
        self,
        name: str,
        label: str,
        kind: str = "text",
        sortable: bool = True,
        filterable: bool = True,
        groupable: bool = False,
        aggregate: str = "",
        expression: str = "",
    ) -> None:
        self.name = name
        self.label = label
        self.kind = kind
        self.expression = expression
        self.sortable = sortable
        self.filterable = filterable
        self.groupable = groupable or kind in ("select", "bool")
        self.aggregate = aggregate or ("sum" if kind == "money" else "")

    @property
    def family(self) -> str:
        return _family(self.kind)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "label": self.label,
            "kind": self.kind,
            "family": self.family,
            "sortable": self.sortable,
            "filterable": self.filterable,
            "groupable": self.groupable,
            "aggregate": self.aggregate,
            "operators": list(OPERATORS_BY_KIND[self.family]),
        }


class GridFilter:
    """A single parsed filter clause with column, operator, and bound parameters."""

    def __init__(
        self,
        column: GridColumn,
        operator: str,
        values: Sequence[Any],
        dialect: str = "postgres",
    ) -> None:
        self.column = column
        self.operator = operator
        self.values = list(values)
        self.dialect = dialect

    def to_sql(self) -> Tuple[str, List[Any]]:
        quoted = _quoted(self.column)
        table = SQLITE_OPERATORS if self.dialect == "sqlite" else OPERATORS
        template = table[self.operator]
        if self.operator in ("in", "not_in"):
            placeholders = ", ".join("?" for _ in self.values)
            return template.format(column=quoted, placeholders=placeholders), list(self.values)
        return template.format(column=quoted), list(self.values)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "column": self.column.name,
            "operator": self.operator,
            "values": [str(v) for v in self.values],
        }


def _coerce(column: GridColumn, raw: str) -> Optional[Any]:
    text = str(raw or "").strip()
    if not text:
        return None
    if column.family == "bool":
        return _boolean(text)
    if column.family == "number":
        return _parse_number(text)
    if column.family == "date":
        return _parse_date(text)
    return text


def _parse_number(text: str) -> Optional[float]:
    cleaned = text.replace("$", "").replace("R$", "").replace(" ", "").replace("%", "")
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_date(text: str) -> Optional[str]:
    cleaned = text.strip()[:10]
    if "/" in cleaned:
        parts = cleaned.split("/")
        if len(parts) != 3 or not all(p.isdigit() for p in parts):
            return None
        day, month, year = parts
        return f"{year.zfill(4)}-{month.zfill(2)}-{day.zfill(2)}"
    parts = cleaned.split("-")
    if len(parts) == 3 and all(p.isdigit() for p in parts):
        return cleaned
    return None


def _values_for(column: GridColumn, operator: str, first: str, second: str) -> Optional[List[Any]]:
    if operator in VALUELESS:
        return []
    if operator in ("in", "not_in"):
        items = _split_list(first)
        return items or None
    primary = _coerce(column, first)
    if primary is None:
        return None
    if operator in RANGED:
        secondary = _coerce(column, second)
        return None if secondary is None else [primary, secondary]
    if column.family == "text" and operator in ("contains", "not_contains", "starts", "ends"):
        return [_like_pattern(operator, str(primary))]
    return [primary]


class GridQuery:
    """Filter, sort, and grouping compiler for a request against declared columns."""

    def __init__(
        self,
        columns: Sequence[GridColumn],
        request: Any,
        default_order: str = "id DESC",
        dialect: str = "postgres",
    ) -> None:
        self._columns = {c.name: c for c in columns}
        self._request = request
        self._default_order = default_order
        self.dialect = dialect
        self.filters = self._parse_filters()
        self.logic = "OR" if self._param("flogic").lower() == "or" else "AND"

    def _param(self, name: str, default: str = "") -> str:
        params = getattr(self._request, "query_params", {})
        return str(params.get(name, default) or "")

    def _list(self, name: str) -> List[str]:
        params = getattr(self._request, "query_params", {})
        getter = getattr(params, "getlist", None)
        if callable(getter):
            return [str(v) for v in getter(name)]
        value = params.get(name)
        if isinstance(value, (list, tuple)):
            return [str(v) for v in value]
        return [str(value)] if value else []

    def _parse_filters(self) -> List[GridFilter]:
        names = self._list("fc")
        operators = self._list("fo")
        values = self._list("fv")
        seconds = self._list("fv2")
        clauses: List[GridFilter] = []
        for index, name in enumerate(names[:MAX_FILTERS]):
            clause = self._clause(
                name,
                _at(operators, index),
                _at(values, index),
                _at(seconds, index),
            )
            if clause is not None:
                clauses.append(clause)
        return clauses

    def _clause(self, name: str, operator: str, first: str, second: str) -> Optional[GridFilter]:
        column = self._columns.get(name)
        if column is None or not column.filterable:
            return None
        if operator not in OPERATORS or operator not in OPERATORS_BY_KIND[column.family]:
            return None
        values = _values_for(column, operator, first, second)
        if values is None:
            return None
        return GridFilter(column, operator, values, dialect=self.dialect)

    def where(self) -> Tuple[str, List[Any]]:
        """Return the parenthesized WHERE SQL fragment and its bound parameters."""
        if not self.filters:
            return "", []
        fragments: List[str] = []
        params: List[Any] = []
        for clause in self.filters:
            sql, values = clause.to_sql()
            fragments.append(sql)
            params.extend(values)
        joiner = f" {self.logic} "
        return "(" + joiner.join(fragments) + ")", params

    def order_by(self) -> Tuple[str, str, str]:
        """Return (sql, sort_column, direction) for the ordering requested."""
        column = self._param("sort")
        direction = "ASC" if self._param("dir").lower() == "asc" else "DESC"
        declared = self._columns.get(column)
        pieces: List[str] = []
        group = self.group_column()
        if group is not None:
            pieces.append(_ORDER_GROUP.format(column=_quoted(group)))
        if declared is not None and declared.sortable:
            pieces.append(_ORDER_COLUMN.format(column=_quoted(declared), direction=direction))
            return ", ".join(pieces), declared.name, direction
        pieces.append(self._default_order)
        return ", ".join(pieces), "", direction

    def group_column(self) -> Optional[GridColumn]:
        """Return the column to group by, if declared groupable."""
        column = self._columns.get(self._param("group"))
        return column if column is not None and column.groupable else None

    def aggregated_columns(self) -> List[GridColumn]:
        """Return columns configured for subtotal aggregation."""
        return [c for c in self._columns.values() if c.aggregate == "sum"]

    def to_dict(self) -> Dict[str, Any]:
        """Return the serialized grid state."""
        _, sort_column, direction = self.order_by()
        group = self.group_column()
        return {
            "filters": [f.to_dict() for f in self.filters],
            "logic": self.logic,
            "sort": sort_column,
            "dir": direction.lower(),
            "group": group.name if group else "",
        }


def _at(values: Sequence[str], index: int) -> str:
    return str(values[index]) if index < len(values) else ""


def table_source(table: str) -> str:
    """Return quoted table source for FROM clause."""
    return f'"{table}"'


def _sum_selection(columns: Sequence[GridColumn]) -> str:
    return "".join(_SUM_PROJECTION.format(column=_quoted(c), name=c.name) for c in columns)


def aggregate_rows(
    db: Any,
    source: str,
    where_sql: str,
    params: Sequence[Any],
    columns: Sequence[GridColumn],
    group: Optional[GridColumn] = None,
) -> Dict[str, Any]:
    """Compute count and column sums of the filtered set in the database."""
    summed = [c for c in columns if c.aggregate == "sum"]
    totals = _totals(db, source, where_sql, params, summed)
    if group is None:
        return {"total": totals["sums"], "count": totals["count"], "groups": []}
    return {
        "total": totals["sums"],
        "count": totals["count"],
        "groups": _groups(db, source, where_sql, params, summed, group),
    }


def _totals(
    db: Any,
    source: str,
    where_sql: str,
    params: Sequence[Any],
    columns: Sequence[GridColumn],
) -> Dict[str, Any]:
    where_clause = f" WHERE {where_sql}" if where_sql.strip() else ""
    row = db.statement(
        _TOTALS_QUERY.format(sums=_sum_selection(columns), source=source, where=where_clause),
        list(params),
        read=True,
    ).fetchone()
    values = dict(row) if row else {}
    return {
        "count": int(values.get("n") or 0),
        "sums": {c.name: float(values.get(f"sum_{c.name}") or 0) for c in columns},
    }


MAX_GROUPS = 500


def _groups(
    db: Any,
    source: str,
    where_sql: str,
    params: Sequence[Any],
    columns: Sequence[GridColumn],
    group: GridColumn,
) -> List[Dict[str, Any]]:
    where_clause = f" WHERE {where_sql}" if where_sql.strip() else ""
    rows = db.statement(
        _GROUP_QUERY.format(
            column=_quoted(group),
            sums=_sum_selection(columns),
            source=source,
            where=where_clause,
            limit=MAX_GROUPS,
        ),
        list(params),
        read=True,
    ).fetchall()
    return [
        {
            "value": "" if row["value"] is None else str(row["value"]),
            "count": int(row["n"] or 0),
            "sums": {c.name: float(row[f"sum_{c.name}"] or 0) for c in columns},
        }
        for row in rows
    ]


__all__ = [
    "GridColumn",
    "GridFilter",
    "GridQuery",
    "table_source",
    "aggregate_rows",
    "OPERATORS",
    "OPERATORS_BY_KIND",
    "MAX_FILTERS",
]
