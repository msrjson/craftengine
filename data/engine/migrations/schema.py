"""Schema builder for Craft Framework migrations.

Provides a fluent `Blueprint` that compiles to dialect-specific
DDL for SQLite, PostgreSQL and MySQL.

Category: Core Framework (Migrations).
Relations:
  - Used inside `database/migrations/*` files' `up()`/`down()`; executes DDL
    through `engine/orm/connection.py`. Bound as `schema`, exposed via the
    `Schema` facade.
References:
  - Guide: `documentation/migrations.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

from typing import Any, Callable, List, Optional, Tuple


def _plural(word: str) -> str:
    if word.endswith("y") and not word.endswith(("ay", "ey", "iy", "oy", "uy")):
        return word[:-1] + "ies"
    if word.endswith(("s", "x", "z", "ch", "sh")):
        return word + "es"
    return word + "s"


def _assert_table(name: str) -> str:
    """Reject a table, column or policy name that could smuggle SQL into DDL.

    Schema objects are quoted, not bound — DDL takes no parameters — so the
    same allowlist the query builder applies to identifiers applies here.
    """
    from engine.orm.query_builder import _assert_identifier

    return _assert_identifier(name)


class _NoDefault:
    def __repr__(self) -> str:
        return "<no default>"


_NO_DEFAULT = _NoDefault()


class Column:
    """A fluent column definition."""

    def __init__(self, name: str, type_: str, length: Optional[Any] = None):
        self.name = name
        self.type = type_
        self.length = length
        self.is_nullable = False
        self.is_unique = False
        self.is_primary = False
        self.is_auto_increment = False
        self.default_value: Any = _NO_DEFAULT
        self.foreign: Optional[dict] = None
        self.index = False
        self.comment: Optional[str] = None
        #: Allowed values for an `enum()` column, enforced with a CHECK
        #: constraint. Kept separate from `comment`, which nothing compiles.
        self.allowed_values: Optional[List[str]] = None
        #: Source columns and weights for a generated `tsvector`.
        self.generated: Optional[dict] = None

    # -- fluent modifiers ------------------------------------------------------

    def nullable(self, value: bool = True) -> "Column":
        self.is_nullable = value
        return self

    def unique(self, value: bool = True) -> "Column":
        self.is_unique = value
        return self

    def default(self, value: Any) -> "Column":
        self.default_value = value
        return self

    def primary(self) -> "Column":
        self.is_primary = True
        return self

    def indexed(self) -> "Column":
        self.index = True
        return self

    def constrained(self, table: Optional[str] = None, column: str = "id") -> "Column":
        target = table or _plural(self.name[:-3] if self.name.endswith("_id") else self.name)
        self.foreign = {"table": target, "column": column, "on_delete": None, "on_update": None}
        return self

    def references(self, column: str) -> "Column":
        self.foreign = self.foreign or {"table": None, "column": column, "on_delete": None, "on_update": None}
        self.foreign["column"] = column
        return self

    def on(self, table: str) -> "Column":
        self.foreign = self.foreign or {"table": table, "column": "id", "on_delete": None, "on_update": None}
        self.foreign["table"] = table
        return self

    def cascade_on_delete(self) -> "Column":
        if self.foreign is None:
            self.constrained()
        self.foreign["on_delete"] = "CASCADE"
        return self

    def null_on_delete(self) -> "Column":
        if self.foreign is None:
            self.constrained()
        self.foreign["on_delete"] = "SET NULL"
        self.is_nullable = True
        return self

    def generated_from(
        self,
        sources: Any,
        language: str = "english",
    ) -> "Column":
        """Compute this `tsvector` from other columns, stored, on write.

            t.tsvector("search_document").generated_from(
                {"title": "A", "body": "B"}
            )

        Stored and generated rather than built in the query: a `to_tsvector()`
        call in a WHERE clause is recomputed for every candidate row and cannot
        use an index, which is the difference between a search that seeks and
        one that reads the table.

        `sources` is either a list of columns or a mapping of column to weight
        (`A` through `D`, heaviest first) — weights are what let a title match
        outrank a body match under `ts_rank_cd`.
        """
        from engine.orm.postgres.macros import LANGUAGES

        if language not in LANGUAGES:
            raise ValueError(f"Unknown text search language [{language}].")

        if not isinstance(sources, dict):
            sources = {name: None for name in sources}
        for name, weight in sources.items():
            _assert_table(name)
            if weight is not None and weight not in ("A", "B", "C", "D"):
                raise ValueError(
                    f"Text search weight must be A, B, C or D, got {weight!r}."
                )
        if not sources:
            raise ValueError("generated_from() needs at least one source column.")

        self.generated = {"sources": sources, "language": language}
        self.is_nullable = True
        return self

    def cascade_on_update(self) -> "Column":
        if self.foreign is None:
            self.constrained()
        self.foreign["on_update"] = "CASCADE"
        return self


class Blueprint:
    """Collects column definitions for a table."""

    def __init__(self, table: str):
        self.table = table
        self.columns: List[Column] = []
        self.indexes: List[dict] = []
        #: Row-level security declaration, set by `tenant_scoped()`.
        self.rls: Optional[dict] = None
        self.checks: List[dict] = []
        self.excludes: List[dict] = []
        #: Partitioning strategy, set by `partition_by_*()`.
        self.partition: Optional[dict] = None

    def _add(self, column: Column, **modifiers: Any) -> Column:
        """Append a column, applying any keyword-style modifiers.

        Both styles are supported and interchangeable:
            t.string("cpf").nullable()
            t.string("cpf", nullable=True)
        """
        if modifiers.get("nullable"):
            column.nullable()
        if modifiers.get("unique"):
            column.unique()
        if modifiers.get("index"):
            column.indexed()
        if modifiers.get("primary"):
            column.primary()
        if "default" in modifiers:
            column.default(modifiers["default"])
        self.columns.append(column)
        return column

    # -- column types ----------------------------------------------------------

    def id(self, name: str = "id", type: str = "big", **modifiers: Any) -> Column:
        kind = "increments" if str(type).lower() in ("int", "integer") else "big_increments"
        col = Column(name, kind)
        col.is_primary = True
        col.is_auto_increment = True
        return self._add(col, **modifiers)

    def big_increments(self, name: str = "id", **modifiers: Any) -> Column:
        col = Column(name, "big_increments")
        col.is_primary = True
        col.is_auto_increment = True
        return self._add(col, **modifiers)

    def increments(self, name: str = "id", **modifiers: Any) -> Column:
        col = Column(name, "increments")
        col.is_primary = True
        col.is_auto_increment = True
        return self._add(col, **modifiers)

    def string(self, name: str, length: int = 255, **modifiers: Any) -> Column:
        return self._add(Column(name, "string", length), **modifiers)

    def char(self, name: str, length: int = 255, **modifiers: Any) -> Column:
        return self._add(Column(name, "char", length), **modifiers)

    def text(self, name: str, **modifiers: Any) -> Column:
        return self._add(Column(name, "text"), **modifiers)

    def long_text(self, name: str, **modifiers: Any) -> Column:
        return self._add(Column(name, "long_text"), **modifiers)

    def integer(self, name: str, **modifiers: Any) -> Column:
        return self._add(Column(name, "integer"), **modifiers)

    def big_integer(self, name: str, **modifiers: Any) -> Column:
        return self._add(Column(name, "big_integer"), **modifiers)

    def small_integer(self, name: str, **modifiers: Any) -> Column:
        return self._add(Column(name, "small_integer"), **modifiers)

    def float(self, name: str, **modifiers: Any) -> Column:
        return self._add(Column(name, "float"), **modifiers)

    def decimal(self, name: str, precision: int = 12, scale: int = 2, **modifiers: Any) -> Column:
        return self._add(Column(name, "decimal", (precision, scale)), **modifiers)

    def boolean(self, name: str, **modifiers: Any) -> Column:
        return self._add(Column(name, "boolean"), **modifiers)

    def date(self, name: str, **modifiers: Any) -> Column:
        return self._add(Column(name, "date"), **modifiers)

    def datetime(self, name: str, **modifiers: Any) -> Column:
        return self._add(Column(name, "datetime"), **modifiers)

    def timestamp(self, name: str, **modifiers: Any) -> Column:
        return self._add(Column(name, "datetime"), **modifiers)

    def time(self, name: str, **modifiers: Any) -> Column:
        return self._add(Column(name, "time"), **modifiers)

    def json(self, name: str, **modifiers: Any) -> Column:
        return self._add(Column(name, "json"), **modifiers)

    # -- PostgreSQL types ------------------------------------------------------
    #
    # Each degrades to the closest thing the other drivers have, so a migration
    # written for PostgreSQL still builds a working development database. The
    # *queries* against these columns do not degrade — the macros in
    # `engine/orm/postgres/` refuse rather than emulate, because a filter that
    # silently means something else is worse than one that will not run.

    def jsonb(self, name: str, **modifiers: Any) -> Column:
        """Binary JSON — indexable, and the only JSON worth storing here."""
        return self._add(Column(name, "json"), **modifiers)

    def timestamptz(self, name: str, **modifiers: Any) -> Column:
        return self._add(Column(name, "timestamptz"), **modifiers)

    def array(self, name: str, of: str = "text", **modifiers: Any) -> Column:
        return self._add(Column(name, "array", of), **modifiers)

    def tsrange(self, name: str, **modifiers: Any) -> Column:
        return self._add(Column(name, "tsrange"), **modifiers)

    def tstzrange(self, name: str, **modifiers: Any) -> Column:
        return self._add(Column(name, "tstzrange"), **modifiers)

    def daterange(self, name: str, **modifiers: Any) -> Column:
        return self._add(Column(name, "daterange"), **modifiers)

    def int4range(self, name: str, **modifiers: Any) -> Column:
        return self._add(Column(name, "int4range"), **modifiers)

    def tsvector(self, name: str, **modifiers: Any) -> Column:
        """A search document column. Pair it with `generated_from()`."""
        return self._add(Column(name, "tsvector").nullable(), **modifiers)

    def vector(self, name: str, dimensions: int, **modifiers: Any) -> Column:
        """An embedding column. Needs the `vector` extension."""
        return self._add(Column(name, "vector", int(dimensions)), **modifiers)

    def inet(self, name: str, **modifiers: Any) -> Column:
        return self._add(Column(name, "inet"), **modifiers)

    def citext(self, name: str, **modifiers: Any) -> Column:
        """Case-insensitive text — for emails and slugs. Needs `citext`."""
        return self._add(Column(name, "citext"), **modifiers)

    def uuid(self, name: str = "uuid", **modifiers: Any) -> Column:
        return self._add(Column(name, "uuid"), **modifiers)

    def uuid_key(self, name: str = "uuid") -> Column:
        """A unique, indexed UUID alongside the numeric primary key.

        The integer `id` stays the key for joins and foreign keys — narrow and
        fast — while the UUID is what you expose in URLs and APIs. Sequential
        ids in a public URL leak how many records exist and invite enumeration.

        Models fill this in automatically; see `Model.uses_uuid`.
        """
        return self._add(Column(name, "uuid").unique())

    def uuid_primary(self, name: str = "id", default: Optional[str] = None) -> Column:
        """Use a UUID as the primary key itself, with no integer id.

        Set `key_type = "uuid"` on the model so it generates the value, or pass
        a database-side default:

            t.uuid_primary(default="uuidv7()")           # PostgreSQL 18+
            t.uuid_primary(default="gen_random_uuid()")  # any version

        Prefer `uuidv7()` where the server has it. `gen_random_uuid()` is
        version 4 — uniformly random, so every insert lands on a different
        B-tree leaf and the index write set is effectively the whole index. A v7
        carries a 48-bit millisecond prefix, so inserts append to one side of the
        index instead of scattering across it: identical opacity in a URL,
        materially cheaper to maintain.

        Below PostgreSQL 18 there is no `uuidv7()` to call as a DEFAULT.
        `Model.new_uuid()` generates the same thing in Python, which is what the
        ORM fills in for `key_type = "uuid"` models.
        """
        column = Column(name, "uuid").primary()
        if default:
            from engine.orm.expression import Raw

            column.default(Raw(default))
        return self._add(column)

    def binary(self, name: str, **modifiers: Any) -> Column:
        return self._add(Column(name, "binary"), **modifiers)

    def enum(self, name: str, values: List[str], **modifiers: Any) -> Column:
        """A string column restricted to `values` by a CHECK constraint.

        The restriction used to live in `Column.comment` as the text
        `"enum:a,b"`, which no grammar ever read — so the column was a plain
        `VARCHAR(255)` and accepted anything. A CHECK constraint is portable
        across SQLite, PostgreSQL and MySQL 8+, which is the whole supported
        set.
        """
        if not values:
            raise ValueError("enum() needs at least one allowed value")

        col = Column(name, "string", 255)
        col.allowed_values = list(values)
        return self._add(col, **modifiers)

    def foreign_id(self, name: str, **modifiers: Any) -> Column:
        return self._add(Column(name, "big_integer"), **modifiers)

    def timestamps(self) -> None:
        self._add(Column("created_at", "datetime").nullable())
        self._add(Column("updated_at", "datetime").nullable())

    def soft_deletes(self, name: str = "deleted_at") -> Column:
        return self._add(Column(name, "datetime").nullable())

    def remember_token(self) -> Column:
        return self._add(Column("remember_token", "string", 100).nullable())

    def unique_index(self, columns: List[str], name: Optional[str] = None, **options: Any) -> None:
        self.index_on(columns, name, unique=True, **options)

    def index_on(
        self,
        columns: List[Any],
        name: Optional[str] = None,
        *,
        unique: bool = False,
        where: Optional[str] = None,
        method: Optional[str] = None,
        ops: Optional[str] = None,
        concurrently: bool = False,
        with_options: Optional[dict] = None,
    ) -> None:
        """Composite, partial, expression and opclass indexes, in one signature.

        `where` is the significant addition. A partial index over only the rows
        that are actually queried is the difference between a queue claim that
        scans and one that seeks, and it keeps the index small enough to stay
        resident.

        `concurrently` builds without an exclusive lock, which PostgreSQL
        refuses to do inside a transaction block — the migration declaring it
        must set `transactional = False` at module level.
        """
        self.indexes.append({
            "columns": list(columns),
            "name": name,
            "unique": unique,
            "where": where,
            "method": method,
            "ops": ops,
            "concurrently": concurrently,
            "with": with_options,
        })

    def gin_index(self, column: str, ops: Optional[str] = None, **options: Any) -> None:
        """GIN — for JSONB containment, arrays and full-text search.

        `ops="jsonb_path_ops"` indexes value paths only: roughly a third the
        size and faster, at the cost of supporting `@>` alone. Take it when
        containment is all you query.
        """
        self.index_on([column], method="gin", ops=ops, **options)

    def gist_index(self, column: str, ops: Optional[str] = None, **options: Any) -> None:
        """GiST — for ranges, geometry, and trigram distance ordering."""
        self.index_on([column], method="gist", ops=ops, **options)

    def hnsw_index(
        self,
        column: str,
        ops: str = "vector_cosine_ops",
        m: int = 16,
        ef_construction: int = 64,
        **options: Any,
    ) -> None:
        """HNSW — approximate nearest neighbour over a `vector` column.

        Higher build cost than IVFFlat and far better recall for the latency,
        with no retraining as rows are added. The defaults suit embeddings in
        the 1000–2000 dimension range; raise `m` for higher recall at the cost
        of index size.
        """
        self.index_on(
            [column], method="hnsw", ops=ops,
            with_options={"m": int(m), "ef_construction": int(ef_construction)},
            **options,
        )

    # -- constraints -----------------------------------------------------------

    def check(self, expression: Any, name: Optional[str] = None) -> None:
        """A CHECK constraint.

        Takes a `Raw` so the predicate is visibly migration-authored — it is
        interpolated, and nothing that came from a request may reach it.
        """
        from engine.orm.expression import Raw

        if not isinstance(expression, Raw):
            raise TypeError(
                "check() takes a Raw() expression, so it is clear at the call "
                "site that the predicate is written here and not assembled "
                "from input."
            )
        self.checks.append({"expression": expression, "name": name})

    def exclude_with(
        self,
        *pairs: tuple,
        using: str = "gist",
        name: Optional[str] = None,
    ) -> None:
        """An exclusion constraint — the double-booking guard.

            t.exclude_with(("room_id", "="), ("period", "&&"))

        No two rows may agree on `room_id` *and* overlap on `period`. Needs the
        `btree_gist` extension for the equality half: GiST has no native
        operator class for a plain integer, and the constraint fails to create
        without it.
        """
        for column, operator in pairs:
            _assert_table(column)
            if operator not in ("=", "&&", "<>"):
                raise ValueError(
                    f"Invalid exclusion operator [{operator}]. Use '=', '&&' or '<>'."
                )
        if not pairs:
            raise ValueError("exclude_with() needs at least one column/operator pair.")
        self.excludes.append({"pairs": pairs, "using": using, "name": name})

    # -- partitioning ----------------------------------------------------------

    def partition_by_range(self, *columns: str) -> None:
        """Declare the table range-partitioned on `columns`.

        Every unique constraint — the primary key included — must contain the
        partition key, because uniqueness cannot be enforced across partitions.
        The grammar folds the key into the primary key and says so, rather than
        letting `CREATE TABLE` fail with a message about index columns.
        """
        self.partition = {
            "strategy": "RANGE",
            "columns": [_assert_table(c) for c in columns],
        }

    def partition_by_list(self, column: str) -> None:
        self.partition = {"strategy": "LIST", "columns": [_assert_table(column)]}

    def partition_by_hash(self, column: str) -> None:
        self.partition = {"strategy": "HASH", "columns": [_assert_table(column)]}

    # -- multi-tenancy ---------------------------------------------------------

    def tenant_scoped(
        self,
        column: str = "tenant_id",
        *,
        references: Optional[str] = "tenants",
        nullable: bool = False,
    ) -> Column:
        """Everything one table needs to be isolated per tenant, in one call.

        Adds the column, indexes it, enables *and* forces row-level security,
        and creates the isolation policy. Writing those four separately is how
        a table ends up with three of them — which looks isolated and is not.

        Forcing matters: policies do not apply to the table's owner, and
        migrations run as the owner. Without FORCE, an application connecting
        as that same role sees every tenant's rows and every policy is
        decoration. Run the application as a separate, non-owning role as well;
        FORCE is the second lock, not the only one.
        """
        col = Column(column, "uuid")
        if nullable:
            col.nullable()
        self._add(col)
        # Leads its own index: the policy predicate is `tenant_id = …`, so every
        # scan starts there and a tenant-leading index is what keeps it a seek.
        self.index_on([column], name=f"idx_{self.table}_{column}")
        if references:
            col.foreign = {
                "table": references, "column": "id",
                "on_delete": "CASCADE", "on_update": None,
            }
        self.rls = {
            "column": column,
            "force": True,
            "policy": f"{self.table}_tenant_isolation",
        }
        return col


class Grammar:
    """Compiles a Blueprint into dialect-specific SQL."""

    TYPES = {
        "sqlite": {
            "increments": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "big_increments": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "string": "VARCHAR({length})",
            "char": "CHAR({length})",
            "text": "TEXT",
            "long_text": "TEXT",
            "integer": "INTEGER",
            "big_integer": "INTEGER",
            "small_integer": "INTEGER",
            "float": "REAL",
            "decimal": "NUMERIC({precision}, {scale})",
            "boolean": "BOOLEAN",
            "date": "DATE",
            "datetime": "DATETIME",
            "time": "TIME",
            "json": "TEXT",
            "uuid": "VARCHAR(36)",
            "binary": "BLOB",
            # PostgreSQL types, degraded to what SQLite can store. The casts in
            # `engine/orm/casts.py` make the round trip identical either way.
            "timestamptz": "DATETIME",
            "array": "TEXT",
            "tsrange": "TEXT",
            "tstzrange": "TEXT",
            "daterange": "TEXT",
            "int4range": "TEXT",
            "tsvector": "TEXT",
            "vector": "TEXT",
            "inet": "VARCHAR(45)",
            "citext": "TEXT COLLATE NOCASE",
        },
        "postgresql": {
            "increments": "SERIAL PRIMARY KEY",
            "big_increments": "BIGSERIAL PRIMARY KEY",
            "string": "VARCHAR({length})",
            "char": "CHAR({length})",
            "text": "TEXT",
            "long_text": "TEXT",
            "integer": "INTEGER",
            "big_integer": "BIGINT",
            "small_integer": "SMALLINT",
            "float": "DOUBLE PRECISION",
            "decimal": "NUMERIC({precision}, {scale})",
            "boolean": "BOOLEAN",
            "date": "DATE",
            "datetime": "TIMESTAMP",
            "time": "TIME",
            "json": "JSONB",
            "uuid": "UUID",
            "binary": "BYTEA",
            "timestamptz": "TIMESTAMPTZ",
            "array": "{length}[]",
            "tsrange": "TSRANGE",
            "tstzrange": "TSTZRANGE",
            "daterange": "DATERANGE",
            "int4range": "INT4RANGE",
            "tsvector": "TSVECTOR",
            "vector": "VECTOR({length})",
            "inet": "INET",
            "citext": "CITEXT",
        },
        "mysql": {
            "increments": "INT UNSIGNED AUTO_INCREMENT PRIMARY KEY",
            "big_increments": "BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY",
            "string": "VARCHAR({length})",
            "char": "CHAR({length})",
            "text": "TEXT",
            "long_text": "LONGTEXT",
            "integer": "INT",
            "big_integer": "BIGINT",
            "small_integer": "SMALLINT",
            "float": "DOUBLE",
            "decimal": "DECIMAL({precision}, {scale})",
            "boolean": "TINYINT(1)",
            "date": "DATE",
            "datetime": "DATETIME",
            "time": "TIME",
            "json": "JSON",
            "uuid": "CHAR(36)",
            "binary": "BLOB",
            "timestamptz": "DATETIME",
            "array": "JSON",
            "tsrange": "VARCHAR(64)",
            "tstzrange": "VARCHAR(64)",
            "daterange": "VARCHAR(64)",
            "int4range": "VARCHAR(64)",
            "tsvector": "TEXT",
            "vector": "JSON",
            "inet": "VARCHAR(45)",
            "citext": "VARCHAR(255)",
        },
    }

    def __init__(self, driver: str = "sqlite"):
        self.driver = driver if driver in self.TYPES else "sqlite"

    def wrap(self, identifier: str) -> str:
        if self.driver == "mysql":
            return f"`{identifier}`"
        return f'"{identifier}"'

    def type_of(self, column: Column) -> str:
        template = self.TYPES[self.driver][column.type]
        if column.type == "decimal":
            precision, scale = column.length or (12, 2)
            return template.format(precision=precision, scale=scale)
        if "{length}" in template:
            return template.format(length=column.length or 255)
        return template

    def format_default(self, value: Any) -> str:
        from engine.orm.expression import Raw

        if isinstance(value, Raw):
            # A function call, not a string: `DEFAULT gen_random_uuid()` has to
            # reach the database unquoted, and the wrapper is what says so at
            # the call site instead of the grammar guessing from brackets.
            return value.sql
        if value is None:
            return "NULL"
        if isinstance(value, bool):
            if self.driver == "postgresql":
                return "TRUE" if value else "FALSE"
            return "1" if value else "0"
        if isinstance(value, (int, float)):
            return str(value)
        escaped = str(value).replace("'", "''")
        return f"'{escaped}'"

    def compile_column(self, column: Column, in_partitioned_table: bool = False) -> str:
        parts = [self.wrap(column.name)]

        if in_partitioned_table and column.is_auto_increment:
            # `BIGSERIAL PRIMARY KEY` carries the key inline, which a
            # partitioned table cannot accept — the key has to be a table-level
            # constraint including the partition column. The sequence is kept.
            parts.append("BIGSERIAL" if column.type == "big_increments" else "SERIAL")
            return " ".join(parts)

        parts.append(self.type_of(column))

        if column.is_auto_increment:
            return " ".join(parts)

        if column.generated is not None and self.driver == "postgresql":
            parts.append(f"GENERATED ALWAYS AS ({self.compile_tsvector(column)}) STORED")
            return " ".join(parts)

        if not column.is_nullable:
            parts.append("NOT NULL")
        if column.default_value is not _NO_DEFAULT:
            parts.append(f"DEFAULT {self.format_default(column.default_value)}")
        if column.is_primary and not in_partitioned_table:
            parts.append("PRIMARY KEY")
        if column.is_unique:
            parts.append("UNIQUE")
        if column.allowed_values:
            allowed = ", ".join(
                "'" + str(v).replace("'", "''") + "'" for v in column.allowed_values
            )
            parts.append(f"CHECK ({self.wrap(column.name)} IN ({allowed}))")
        return " ".join(parts)

    def compile_tsvector(self, column: Column) -> str:
        """The `to_tsvector(...)` expression a generated search column stores.

        `coalesce(col, '')` on every source, because concatenating a NULL makes
        the whole document NULL — one missing subtitle and the row falls out of
        every search result with nothing to show for it.
        """
        language = column.generated["language"]
        parts = []
        for name, weight in column.generated["sources"].items():
            vector = f"to_tsvector('{language}', coalesce({self.wrap(name)}, ''))"
            parts.append(f"setweight({vector}, '{weight}')" if weight else vector)
        return " || ".join(parts)

    def compile_create(self, blueprint: Blueprint) -> List[str]:
        partitioned = bool(blueprint.partition) and self.driver == "postgresql"
        keys = self._partition_keys(blueprint) if partitioned else []

        definitions = [
            self.compile_column(c, in_partitioned_table=partitioned)
            for c in blueprint.columns
        ]

        if keys:
            # A partitioned table cannot enforce uniqueness across partitions,
            # so every unique constraint has to contain the partition key. The
            # primary key is folded here rather than left to fail at CREATE
            # TABLE with a message about index columns.
            definitions.append(
                "PRIMARY KEY (" + ", ".join(self.wrap(k) for k in keys) + ")"
            )

        for column in blueprint.columns:
            if column.foreign and column.foreign.get("table"):
                clause = (
                    f"FOREIGN KEY ({self.wrap(column.name)}) REFERENCES "
                    f"{self.wrap(column.foreign['table'])} ({self.wrap(column.foreign['column'])})"
                )
                if column.foreign.get("on_delete"):
                    clause += f" ON DELETE {column.foreign['on_delete']}"
                if column.foreign.get("on_update"):
                    clause += f" ON UPDATE {column.foreign['on_update']}"
                definitions.append(clause)

        definitions.extend(self.compile_constraints(blueprint))

        body = ",\n    ".join(definitions)
        create = f"CREATE TABLE IF NOT EXISTS {self.wrap(blueprint.table)} (\n    {body}\n)"
        if partitioned:
            strategy = blueprint.partition["strategy"]
            columns = ", ".join(self.wrap(c) for c in blueprint.partition["columns"])
            create += f" PARTITION BY {strategy} ({columns})"

        statements = [create]
        statements.extend(self.compile_indexes(blueprint))
        statements.extend(self.compile_rls(blueprint))
        return statements

    @staticmethod
    def _partition_keys(blueprint: Blueprint) -> List[str]:
        """Primary key columns for a partitioned table: the key, plus the parts."""
        primary = [c.name for c in blueprint.columns if c.is_primary or c.is_auto_increment]
        if not primary:
            return []
        keys = list(primary)
        for column in blueprint.partition["columns"]:
            if column not in keys:
                keys.append(column)
        return keys

    def compile_partition(
        self,
        parent: str,
        name: str,
        *,
        values_from: Any = None,
        values_to: Any = None,
        values_in: Optional[List[Any]] = None,
        default: bool = False,
    ) -> str:
        """`CREATE TABLE … PARTITION OF …` for one range, list or default part."""
        head = (
            f"CREATE TABLE IF NOT EXISTS {self.wrap(_assert_table(name))} "
            f"PARTITION OF {self.wrap(_assert_table(parent))}"
        )
        if default:
            # The backstop. Rows landing here mean the maintenance task that
            # creates partitions ahead of time has stopped running — worth an
            # alert, and far better than the insert being rejected outright.
            return f"{head} DEFAULT"
        if values_in is not None:
            rendered = ", ".join(self.format_default(v) for v in values_in)
            return f"{head} FOR VALUES IN ({rendered})"
        return (
            f"{head} FOR VALUES FROM ({self.format_default(values_from)}) "
            f"TO ({self.format_default(values_to)})"
        )

    #: How a policy reads the bound tenant. `current_setting(name, true)` returns
    #: NULL when the variable was never set, and `NULLIF(…, '')` covers the
    #: cleared-on-checkin case — so an unbound session compares against NULL and
    #: matches nothing. Fail-closed in both directions, which is the whole point.
    TENANT_PREDICATE = (
        "{column} = NULLIF(current_setting('{guc}', true), '')::uuid"
    )

    def compile_rls(self, blueprint: Blueprint) -> List[str]:
        """Enable, force and police row-level security for a blueprint.

        A no-op on drivers without it: `Blueprint.tenant_scoped()` still adds
        the column and the index, and the `TenantScoped` mixin still scopes
        queries in Python, so a suite on SQLite behaves consistently — it just
        does not have the guarantee, which is why `ScopeTenant` refuses to serve
        tenant traffic there.
        """
        if not blueprint.rls or self.driver != "postgresql":
            return []

        from engine.orm.connection import Connection

        table = self.wrap(blueprint.table)
        predicate = self.TENANT_PREDICATE.format(
            column=self.wrap(blueprint.rls["column"]), guc=Connection.TENANT_GUC
        )
        statements = [f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"]
        if blueprint.rls.get("force", True):
            statements.append(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

        # USING filters what is readable; WITH CHECK filters what is writable.
        # Both, or a tenant can INSERT a row it will never be able to read back.
        statements.append(
            f"CREATE POLICY {self.wrap(blueprint.rls['policy'])} ON {table} "
            f"USING ({predicate}) WITH CHECK ({predicate})"
        )
        return statements

    def compile_indexes(self, blueprint: Blueprint) -> List[str]:
        """`CREATE INDEX` statements for a blueprint's columns and indexes.

        Shared by create and alter: `compile_add_columns` used to emit only the
        `ADD COLUMN`, so `.indexed()`, `unique_index()` and `index()` were
        accepted and silently discarded on an existing table — the migration
        looked right and the index never existed.
        """
        statements: List[str] = []

        for column in blueprint.columns:
            if column.index and not column.is_unique:
                name = f"idx_{blueprint.table}_{column.name}"
                statements.append(
                    f"CREATE INDEX IF NOT EXISTS {self.wrap(name)} "
                    f"ON {self.wrap(blueprint.table)} ({self.wrap(column.name)})"
                )

        for index in blueprint.indexes:
            statements.append(self.compile_index(blueprint, index))

        return statements

    def compile_index(self, blueprint: Blueprint, index: dict) -> str:
        """One index, including the PostgreSQL-only parts where they apply.

        Method, operator class and storage options are dropped on drivers that
        have no equivalent — the index is still built, just plainly. `WHERE` is
        kept everywhere, because SQLite has partial indexes too and dropping it
        would build a *different*, larger index than the migration asked for.
        """
        from engine.orm.expression import Expr

        columns = index["columns"]
        rendered = []
        for column in columns:
            if isinstance(column, Expr):
                rendered.append(f"({column.sql})")
            else:
                target = self.wrap(_assert_table(column))
                if index.get("ops") and self.driver == "postgresql":
                    target = f"{target} {_assert_table(index['ops'])}"
                rendered.append(target)

        name = index["name"] or (
            ("uniq_" if index["unique"] else "idx_")
            + blueprint.table + "_"
            + "_".join(
                c.sql if isinstance(c, Expr) else c for c in columns
            ).replace(" ", "_")[:48]
        )

        parts = ["CREATE"]
        if index["unique"]:
            parts.append("UNIQUE")
        parts.append("INDEX")
        if index.get("concurrently") and self.driver == "postgresql":
            # Builds without an exclusive lock — and cannot run inside a
            # transaction, so the migration must declare `transactional = False`.
            parts.append("CONCURRENTLY")
        parts.append("IF NOT EXISTS")
        parts.append(self.wrap(_assert_table(name)))
        parts.append(f"ON {self.wrap(blueprint.table)}")

        if index.get("method") and self.driver == "postgresql":
            parts.append(f"USING {_assert_table(index['method'])}")

        parts.append("(" + ", ".join(rendered) + ")")

        options = index.get("with")
        if options and self.driver == "postgresql":
            rendered_options = ", ".join(
                f"{_assert_table(key)} = {int(value)}" for key, value in options.items()
            )
            parts.append(f"WITH ({rendered_options})")

        if index.get("where"):
            parts.append(f"WHERE {index['where']}")

        return " ".join(parts)

    def compile_constraints(self, blueprint: Blueprint) -> List[str]:
        """Inline CHECK and EXCLUDE clauses for a CREATE TABLE body."""
        clauses: List[str] = []

        for check in blueprint.checks:
            prefix = (
                f"CONSTRAINT {self.wrap(_assert_table(check['name']))} "
                if check["name"] else ""
            )
            clauses.append(f"{prefix}CHECK ({check['expression'].sql})")

        if self.driver != "postgresql":
            # An exclusion constraint has no equivalent elsewhere. Emitting
            # nothing is the honest option — silently substituting a UNIQUE
            # would enforce a different rule under the same name.
            return clauses

        for exclude in blueprint.excludes:
            prefix = (
                f"CONSTRAINT {self.wrap(_assert_table(exclude['name']))} "
                if exclude["name"] else ""
            )
            pairs = ", ".join(
                f"{self.wrap(column)} WITH {operator}"
                for column, operator in exclude["pairs"]
            )
            clauses.append(
                f"{prefix}EXCLUDE USING {_assert_table(exclude['using'])} ({pairs})"
            )

        return clauses

    def compile_drop(self, table: str) -> str:
        cascade = " CASCADE" if self.driver == "postgresql" else ""
        return f"DROP TABLE IF EXISTS {self.wrap(table)}{cascade}"

    def compile_add_columns(self, blueprint: Blueprint) -> List[str]:
        statements = [
            f"ALTER TABLE {self.wrap(blueprint.table)} ADD COLUMN {self.compile_column(c)}"
            for c in blueprint.columns
        ]
        # Indexes come after the columns exist, and as separate statements —
        # which is also the only way to add a UNIQUE constraint on SQLite,
        # where `ALTER TABLE ADD COLUMN ... UNIQUE` is rejected outright.
        statements.extend(self.compile_indexes(blueprint))
        # Policies too: `tenant_scoped()` on an existing table has to be able to
        # add the isolation, not just the column.
        statements.extend(self.compile_rls(blueprint))
        return statements

    def compile_drop_column(self, table: str, column: str) -> str:
        return f"ALTER TABLE {self.wrap(table)} DROP COLUMN {self.wrap(column)}"

    def compile_rename(self, table: str, new_name: str) -> str:
        return f"ALTER TABLE {self.wrap(table)} RENAME TO {self.wrap(new_name)}"


class SchemaBuilder:
    """Runs schema operations against the resolved database connection."""

    def __init__(self, db: Any = None):
        self._db = db

    @property
    def db(self) -> Any:
        if self._db is not None:
            return self._db
        from engine.container.application import Container

        return Container.getInstance().make("db")

    def grammar(self) -> Grammar:
        return Grammar(getattr(self.db, "driver", "sqlite"))

    def create_table(self, table: str, callback: Callable[[Blueprint], Any]) -> None:
        blueprint = Blueprint(table)
        callback(blueprint)
        for statement in self.grammar().compile_create(blueprint):
            self.db.statement(statement)

    def create(self, table: str, callback: Callable[[Blueprint], Any]) -> None:
        """Alias of :meth:`create_table`."""
        self.create_table(table, callback)

    def table(self, table: str, callback: Callable[[Blueprint], Any]) -> None:
        """Add columns to an existing table."""
        blueprint = Blueprint(table)
        callback(blueprint)
        for statement in self.grammar().compile_add_columns(blueprint):
            self.db.statement(statement)

    def raw(self, sql: str) -> None:
        """Execute DDL the blueprint cannot express, one statement at a time.

        The escape hatch for dialect-specific schema objects — triggers,
        functions, policies, opclass indexes — while the DSL grows to cover
        them. Statements are split on `;` at the end of a line so a multi-line
        block reads naturally in a migration; `$$ ... $$` function bodies are
        left intact because the split only fires on a semicolon that ends a
        line outside one.

        Migration source only. It takes no bindings, so nothing that came from
        a request may ever reach it.
        """
        for statement in self._split_statements(sql):
            self.db.statement(statement)

    @staticmethod
    def _split_statements(sql: str) -> List[str]:
        statements: List[str] = []
        buffer: List[str] = []
        in_body = False
        for line in sql.splitlines():
            # A `$$` toggles in and out of a function body, where semicolons
            # belong to the body rather than to the DDL around it.
            if line.count("$$") % 2 == 1:
                in_body = not in_body
            buffer.append(line)
            if not in_body and line.rstrip().endswith(";"):
                statements.append("\n".join(buffer).strip().rstrip(";"))
                buffer = []
        tail = "\n".join(buffer).strip().rstrip(";")
        if tail:
            statements.append(tail)
        return [s for s in statements if s.strip()]

    def drop_table(self, table: str) -> None:
        self.db.statement(self.grammar().compile_drop(table))

    def drop_if_exists(self, table: str) -> None:
        self.drop_table(table)

    def drop(self, table: str) -> None:
        self.drop_table(table)

    def drop_column(self, table: str, column: str) -> None:
        self.db.statement(self.grammar().compile_drop_column(table, column))

    def rename(self, table: str, new_name: str) -> None:
        self.db.statement(self.grammar().compile_rename(table, new_name))

    # -- converging: alter an existing column in place --------------------------

    def rename_column(self, table: str, from_name: str, to_name: str) -> None:
        """Rename an existing column. PostgreSQL and SQLite (3.25+) both support
        this natively — unlike type/nullability/default, no rebuild is needed.
        """
        table, from_name, to_name = _assert_table(table), _assert_table(from_name), _assert_table(to_name)
        wrap = self.grammar().wrap
        self.db.statement(f"ALTER TABLE {wrap(table)} RENAME COLUMN {wrap(from_name)} TO {wrap(to_name)}")

    def change_column(
        self,
        table: str,
        name: str,
        *,
        type: Optional[str] = None,
        length: Optional[Any] = None,
        nullable: Optional[bool] = None,
        default: Any = _NO_DEFAULT,
    ) -> None:
        """Alter an existing column's type, nullability, and/or default.

        PostgreSQL only (`alter_column` capability) — SQLite's `ALTER TABLE`
        can rename or drop a column but cannot change type, nullability or
        default without rebuilding the table (copy to a new one, drop the
        old, rename), which this does not attempt: a schema migration that
        silently rewrites an entire table's data on the least-supervised
        driver is a bigger risk than refusing outright and naming the reason.

        Args:
            table: The table to alter.
            name: The column to alter.
            type: New column type (one of the `Blueprint` type names, e.g.
                `"string"`, `"integer"`) — unchanged if omitted.
            length: Length/precision for `type`, when it needs one.
            nullable: `True` to allow NULL, `False` to forbid it — unchanged
                if omitted.
            default: New default value, or `None` to drop the default
                entirely — unchanged if omitted (the parameter's own
                default, `_NO_DEFAULT`, is the "don't touch it" sentinel,
                distinct from passing `None` to mean "no default").

        Raises:
            UnsupportedFeatureError: The driver is not PostgreSQL.
        """
        self.db.dialect.require(
            "alter_column", "is what alters an existing column's type, nullability or default"
        )
        table, name = _assert_table(table), _assert_table(name)
        wrap = self.grammar().wrap
        grammar = self.grammar()

        if type is not None:
            column = Column(name, type, length)
            sql_type = grammar.type_of(column)
            self.db.statement(
                f"ALTER TABLE {wrap(table)} ALTER COLUMN {wrap(name)} TYPE {sql_type} "
                f"USING {wrap(name)}::{sql_type}"
            )
        if nullable is not None:
            clause = "DROP NOT NULL" if nullable else "SET NOT NULL"
            self.db.statement(f"ALTER TABLE {wrap(table)} ALTER COLUMN {wrap(name)} {clause}")
        if default is not _NO_DEFAULT:
            if default is None:
                self.db.statement(f"ALTER TABLE {wrap(table)} ALTER COLUMN {wrap(name)} DROP DEFAULT")
            else:
                self.db.statement(
                    f"ALTER TABLE {wrap(table)} ALTER COLUMN {wrap(name)} "
                    f"SET DEFAULT {grammar.format_default(default)}"
                )

    def add_constraint_if_missing(self, table: str, constraint_name: str, definition: str) -> None:
        """Add a named constraint only if it does not already exist.

        A migration re-run after a partial failure (the process died between
        two `Schema.raw()` statements, say) must not raise on the constraint
        that already made it in — `ADD CONSTRAINT IF NOT EXISTS` is not valid
        PostgreSQL syntax (unlike `CREATE INDEX IF NOT EXISTS`), so this
        checks the catalog first instead.

        Args:
            table: The table the constraint belongs to.
            constraint_name: The constraint's name, used both to check for
                its existence and in the `ADD CONSTRAINT` clause.
            definition: The constraint body, e.g. `"CHECK (amount_cents >= 0)"`
                or `"UNIQUE (tenant_id, slug)"` — everything after the name.
        """
        self.db.dialect.require("alter_column", "is what an idempotent constraint add needs to check the catalog")
        table, constraint_name = _assert_table(table), _assert_table(constraint_name)
        exists = self.db.select_one(
            "SELECT 1 FROM information_schema.table_constraints "
            "WHERE table_name = ? AND constraint_name = ?",
            [table, constraint_name],
        )
        if exists:
            return
        wrap = self.grammar().wrap
        self.db.statement(
            f"ALTER TABLE {wrap(table)} ADD CONSTRAINT {wrap(constraint_name)} {definition}"
        )

    # -- extensions ------------------------------------------------------------

    #: Extensions the framework knows how to use, and what for. An arbitrary
    #: name is refused: `CREATE EXTENSION` takes an identifier rather than a
    #: parameter, and installing one is a privileged act that should be a
    #: deliberate decision rather than a string a caller passed in.
    KNOWN_EXTENSIONS = {
        "pgcrypto": "gen_random_uuid(), digest() and column-level encryption",
        "pg_trgm": "trigram similarity and GiST/GIN fuzzy indexes",
        "btree_gist": "equality columns inside a GiST exclusion constraint",
        "vector": "vector columns and HNSW/IVFFlat indexes",
        "citext": "case-insensitive text, for email and slug columns",
        "unaccent": "diacritic-insensitive full-text search",
    }

    def extension(self, name: str, schema: str = "public") -> None:
        """Install an extension. A no-op where extensions do not exist."""
        if name not in self.KNOWN_EXTENSIONS:
            raise ValueError(
                f"Unknown extension [{name}]. Known: "
                f"{', '.join(sorted(self.KNOWN_EXTENSIONS))}."
            )
        _assert_table(schema)
        if not self.db.dialect.supports("extensions"):
            return
        self.db.statement(
            f'CREATE EXTENSION IF NOT EXISTS "{name}" WITH SCHEMA "{schema}"'
        )
        # The dialect caches which extensions exist, and one more does now.
        for connection in (
            getattr(self.db, "_write", None), getattr(self.db, "_read", None)
        ):
            if connection is not None:
                connection.forget_dialect()

    def installed_extensions(self) -> List[str]:
        if not self.db.dialect.supports("extensions"):
            return []
        rows = self.db.statement("SELECT extname FROM pg_extension", read=True).fetchall()
        return sorted(row["extname"] for row in rows)

    # -- partitioning ----------------------------------------------------------

    def partition(
        self,
        parent: str,
        name: str,
        *,
        values_from: Any = None,
        values_to: Any = None,
        values_in: Optional[List[Any]] = None,
        default: bool = False,
    ) -> None:
        """Attach one partition to a partitioned table.

            Schema.partition("events", "events_2026_08",
                             values_from="2026-08-01", values_to="2026-09-01")

        Range bounds are half-open: `FROM` is inclusive, `TO` is exclusive, so
        consecutive months neither overlap nor leave a gap.
        """
        if not self.db.dialect.supports("partitioning"):
            raise RuntimeError(
                f"The {getattr(self.db, 'driver', '?')!r} driver has no "
                f"declarative partitioning."
            )
        self.db.statement(self.grammar().compile_partition(
            parent, name, values_from=values_from, values_to=values_to,
            values_in=values_in, default=default,
        ))

    def ensure_partitions(
        self,
        table: str,
        *,
        ahead: int = 3,
        interval: str = "month",
        prefix: Optional[str] = None,
    ) -> List[str]:
        """Create the next `ahead` monthly partitions, idempotently.

        Put this on the scheduler the same day the partitioned table ships. A
        range-partitioned table with no partition covering `now()` **rejects
        inserts** — the maintenance task is not an optimisation, it is what
        keeps the table writable.
        """
        if interval != "month":
            raise ValueError("ensure_partitions() currently covers monthly ranges.")
        _assert_table(table)

        from datetime import date

        created: List[str] = []
        today = date.today().replace(day=1)
        for step in range(ahead + 1):
            month = today.month + step
            year, month = today.year + (month - 1) // 12, (month - 1) % 12 + 1
            start = date(year, month, 1)
            end = date(year + (month == 12), month % 12 + 1, 1)
            name = f"{prefix or table}_{start:%Y_%m}"
            self.partition(
                table, name,
                values_from=start.isoformat(), values_to=end.isoformat(),
            )
            created.append(name)
        return created

    # -- row-level security ----------------------------------------------------

    # Identifiers are validated *before* the dialect is consulted throughout
    # this section. A name that could break out of its quotes is a programming
    # error on every driver, and a check that only fires on PostgreSQL is a
    # check that a SQLite-first test-suite never runs.

    def enable_row_level_security(self, table: str, force: bool = True) -> None:
        """Turn RLS on for an existing table. A no-op where it does not exist."""
        wrapped = self.grammar().wrap(_assert_table(table))
        if not self.db.dialect.supports("rls"):
            return
        self.db.statement(f"ALTER TABLE {wrapped} ENABLE ROW LEVEL SECURITY")
        if force:
            self.db.statement(f"ALTER TABLE {wrapped} FORCE ROW LEVEL SECURITY")

    def disable_row_level_security(self, table: str) -> None:
        wrapped = self.grammar().wrap(_assert_table(table))
        if not self.db.dialect.supports("rls"):
            return
        self.db.statement(f"ALTER TABLE {wrapped} NO FORCE ROW LEVEL SECURITY")
        self.db.statement(f"ALTER TABLE {wrapped} DISABLE ROW LEVEL SECURITY")

    def create_tenant_policy(
        self,
        table: str,
        column: str = "tenant_id",
        name: Optional[str] = None,
    ) -> None:
        """Add the isolation policy to a table that already has the column."""
        blueprint = Blueprint(_assert_table(table))
        blueprint.rls = {
            "column": _assert_table(column),
            "force": True,
            "policy": _assert_table(name or f"{table}_tenant_isolation"),
        }
        if not self.db.dialect.supports("rls"):
            return
        for statement in self.grammar().compile_rls(blueprint):
            self.db.statement(statement)

    def drop_policy(self, table: str, name: str) -> None:
        grammar = self.grammar()
        policy = grammar.wrap(_assert_table(name))
        wrapped = grammar.wrap(_assert_table(table))
        if not self.db.dialect.supports("rls"):
            return
        self.db.statement(f"DROP POLICY IF EXISTS {policy} ON {wrapped}")

    def has_table(self, table: str) -> bool:
        return self.db.table_exists(table)

    def has_column(self, table: str, column: str) -> bool:
        return column in self.column_listing(table)

    def column_listing(self, table: str) -> List[str]:
        driver = getattr(self.db, "driver", "sqlite")
        if driver == "sqlite":
            rows = self.db.statement(f'PRAGMA table_info("{table}")').fetchall()
            return [row["name"] for row in rows]
        if driver == "postgresql":
            sql = (
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = ? AND table_schema = ANY (current_schemas(false))"
            )
        else:
            sql = (
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = ? AND table_schema = DATABASE()"
            )
        rows = self.db.statement(sql, [table]).fetchall()
        return [row["column_name"] for row in rows]

    def table_listing(self) -> List[str]:
        """Every base table in the current schema, ordered by name."""
        driver = getattr(self.db, "driver", "sqlite")
        if driver == "sqlite":
            rows = self.db.statement(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
            return sorted(row["name"] for row in rows)
        if driver == "postgresql":
            sql = (
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = ANY (current_schemas(false)) "
                "AND table_type = 'BASE TABLE'"
            )
        else:
            sql = (
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = DATABASE() AND table_type = 'BASE TABLE'"
            )
        rows = self.db.statement(sql).fetchall()
        return sorted(row["table_name"] for row in rows)

    def foreign_keys(self, table: str) -> List[Tuple[str, str, str]]:
        """The table's foreign keys as `(child_column, parent_table, parent_column)`.

        A key with no explicit parent column - a SQLite reference to the
        parent's primary key - is reported against `id`, the framework's own
        convention for a primary key.
        """
        name = _assert_table(table)
        driver = getattr(self.db, "driver", "sqlite")
        if driver == "sqlite":
            rows = self.db.statement(f'PRAGMA foreign_key_list("{name}")').fetchall()
            return [(row["from"], row["table"], row.get("to") or "id") for row in rows]
        if driver == "postgresql":
            sql = (
                "SELECT kcu.column_name AS child_column, "
                "       ccu.table_name AS parent_table, "
                "       ccu.column_name AS parent_column "
                "FROM information_schema.table_constraints tc "
                "JOIN information_schema.key_column_usage kcu "
                "  ON tc.constraint_name = kcu.constraint_name "
                " AND tc.table_schema = kcu.table_schema "
                "JOIN information_schema.constraint_column_usage ccu "
                "  ON ccu.constraint_name = tc.constraint_name "
                " AND ccu.table_schema = tc.table_schema "
                "WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name = ? "
                "ORDER BY kcu.column_name"
            )
            rows = self.db.statement(sql, [name]).fetchall()
            return [
                (row["child_column"], row["parent_table"], row["parent_column"])
                for row in rows
            ]
        return []


# Module-level facade used by migration files: `from craft.migrations import Schema`
Schema = SchemaBuilder()
