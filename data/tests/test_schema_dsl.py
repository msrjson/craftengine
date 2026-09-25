"""Tests for the migration DSL: indexes, constraints, partitioning, extensions.

Phase 6 of the PostgreSQL-native data layer. Most assertions are on compiled
DDL, because that is the contract — a migration is a description of a schema,
and what matters is that the description reaches the database intact.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest

from craft.migrations.schema import Blueprint, Grammar, SchemaBuilder
from craft.orm.expression import Expr, Raw


def compile_pg(build) -> str:
    blueprint = Blueprint("things")
    build(blueprint)
    return "\n".join(Grammar("postgresql").compile_create(blueprint))


# -- indexes -------------------------------------------------------------------


def test_a_partial_index_keeps_its_predicate():
    """The whole point: index only the rows that are actually queried."""
    sql = compile_pg(lambda t: (
        t.id(type="integer"),
        t.string("queue"),
        t.datetime("reserved_at").nullable(),
        t.index_on(["queue", "id"], name="jobs_claim_idx", where="reserved_at IS NULL"),
    ))

    assert 'CREATE INDEX IF NOT EXISTS "jobs_claim_idx" ON "things" ("queue", "id") ' \
           'WHERE reserved_at IS NULL' in sql


def test_a_partial_index_survives_on_sqlite_too():
    """SQLite has partial indexes; dropping the WHERE would build a different one."""
    blueprint = Blueprint("things")
    blueprint.string("queue")
    blueprint.index_on(["queue"], name="p", where="reserved_at IS NULL")

    assert "WHERE reserved_at IS NULL" in "\n".join(
        Grammar("sqlite").compile_create(blueprint)
    )


def test_an_expression_index_is_built_from_an_expr():
    sql = compile_pg(lambda t: (
        t.string("email"),
        t.index_on([Expr('lower("email")')], name="users_email_lower", unique=True),
    ))

    # Doubly parenthesised on purpose: the outer pair is the column list, the
    # inner pair is what PostgreSQL requires around an index expression.
    assert 'CREATE UNIQUE INDEX IF NOT EXISTS "users_email_lower" ON "things" ' \
           '((lower("email")))' in sql


def test_a_gin_index_can_choose_its_operator_class():
    sql = compile_pg(lambda t: (
        t.jsonb("payload"),
        t.gin_index("payload", ops="jsonb_path_ops", name="things_payload_gin"),
    ))

    assert 'USING gin ("payload" jsonb_path_ops)' in sql


def test_an_hnsw_index_carries_its_build_parameters():
    sql = compile_pg(lambda t: (
        t.vector("embedding", 1536),
        t.hnsw_index("embedding", name="things_embedding_hnsw"),
    ))

    assert 'USING hnsw ("embedding" vector_cosine_ops)' in sql
    assert "WITH (m = 16, ef_construction = 64)" in sql


def test_method_and_opclass_are_dropped_where_they_mean_nothing():
    """The index is still built — just plainly — so development keeps working."""
    blueprint = Blueprint("things")
    blueprint.jsonb("payload")
    blueprint.gin_index("payload", ops="jsonb_path_ops", name="p")
    sql = "\n".join(Grammar("sqlite").compile_create(blueprint))

    assert "USING" not in sql
    assert "jsonb_path_ops" not in sql
    assert 'CREATE INDEX IF NOT EXISTS "p" ON "things" ("payload")' in sql


def test_concurrently_is_emitted_only_on_postgres():
    sql = compile_pg(lambda t: (
        t.string("slug"),
        t.index_on(["slug"], name="c", concurrently=True),
    ))
    assert "CREATE INDEX CONCURRENTLY" in sql

    blueprint = Blueprint("things")
    blueprint.string("slug")
    blueprint.index_on(["slug"], name="c", concurrently=True)
    assert "CONCURRENTLY" not in "\n".join(Grammar("sqlite").compile_create(blueprint))


def test_an_index_name_cannot_smuggle_sql():
    with pytest.raises(ValueError):
        compile_pg(lambda t: (
            t.string("slug"),
            t.index_on(["slug"], name='x" ON t; DROP TABLE users; --'),  # nr02: hostile index name, refused before any SQL runs
        ))


def test_an_opclass_cannot_smuggle_sql():
    with pytest.raises(ValueError):
        compile_pg(lambda t: (
            t.jsonb("payload"),
            t.gin_index("payload", ops="a); DROP TABLE users; --", name="p"),  # nr02: hostile operator class, refused before any SQL runs
        ))


def test_indexes_are_still_added_on_an_existing_table():
    blueprint = Blueprint("things")
    blueprint.string("slug")
    blueprint.index_on(["slug"], name="things_slug_idx")
    statements = Grammar("postgresql").compile_add_columns(blueprint)

    assert any("ADD COLUMN" in s for s in statements)
    assert any("CREATE INDEX" in s for s in statements)


# -- constraints ---------------------------------------------------------------


def test_a_check_constraint_is_emitted():
    sql = compile_pg(lambda t: (
        t.integer("quantity"),
        t.check(Raw('"quantity" > 0'), name="things_quantity_positive"),
    ))

    assert 'CONSTRAINT "things_quantity_positive" CHECK ("quantity" > 0)' in sql


def test_check_refuses_a_bare_string():
    """A predicate is interpolated, so it must be visibly migration-authored."""
    with pytest.raises(TypeError):
        Blueprint("things").check('"quantity" > 0')


def test_an_exclusion_constraint_guards_double_booking():
    sql = compile_pg(lambda t: (
        t.big_integer("room_id"),
        t.tsrange("period"),
        t.exclude_with(("room_id", "="), ("period", "&&"), name="no_double_booking"),
    ))

    assert 'CONSTRAINT "no_double_booking" EXCLUDE USING gist ' \
           '("room_id" WITH =, "period" WITH &&)' in sql


def test_an_exclusion_operator_comes_from_a_fixed_set():
    with pytest.raises(ValueError, match="exclusion operator"):
        Blueprint("things").exclude_with(("room_id", "; DROP TABLE users --"))  # nr02: hostile column, refused before any SQL runs


def test_no_exclusion_is_faked_on_a_driver_that_lacks_it():
    """A UNIQUE in its place would enforce a different rule under the same name."""
    blueprint = Blueprint("things")
    blueprint.big_integer("room_id")
    blueprint.tsrange("period")
    blueprint.exclude_with(("room_id", "="), ("period", "&&"))

    assert "EXCLUDE" not in "\n".join(Grammar("sqlite").compile_create(blueprint))


# -- partitioning --------------------------------------------------------------


def test_a_range_partitioned_table_folds_the_key_into_the_primary_key():
    """Uniqueness cannot be enforced across partitions, so the key must contain it."""
    sql = compile_pg(lambda t: (
        t.big_increments("id"),
        t.timestamptz("occurred_at"),
        t.jsonb("payload"),
        t.partition_by_range("occurred_at"),
    ))

    assert 'PARTITION BY RANGE ("occurred_at")' in sql
    assert 'PRIMARY KEY ("id", "occurred_at")' in sql
    # The inline form is what PostgreSQL rejects on a partitioned table.
    assert '"id" BIGSERIAL PRIMARY KEY' not in sql
    assert '"id" BIGSERIAL' in sql


def test_list_partitioning_compiles():
    sql = compile_pg(lambda t: (
        t.id(type="integer"),
        t.string("region"),
        t.partition_by_list("region"),
    ))
    assert 'PARTITION BY LIST ("region")' in sql


def test_partitioning_is_not_attempted_where_it_does_not_exist():
    blueprint = Blueprint("things")
    blueprint.id(type="integer")
    blueprint.timestamp("occurred_at")
    blueprint.partition_by_range("occurred_at")

    sql = "\n".join(Grammar("sqlite").compile_create(blueprint))
    assert "PARTITION" not in sql
    assert "PRIMARY KEY AUTOINCREMENT" in sql


def test_a_range_partition_is_half_open():
    statement = Grammar("postgresql").compile_partition(
        "events", "events_2026_08",
        values_from="2026-08-01", values_to="2026-09-01",
    )

    assert 'PARTITION OF "events"' in statement
    # FROM inclusive, TO exclusive: consecutive months neither overlap nor gap.
    assert "FOR VALUES FROM ('2026-08-01') TO ('2026-09-01')" in statement


def test_a_default_partition_is_the_backstop():
    statement = Grammar("postgresql").compile_partition("events", "events_other", default=True)
    assert statement.endswith("DEFAULT")


def test_a_partition_name_cannot_smuggle_sql():
    with pytest.raises(ValueError):
        Grammar("postgresql").compile_partition("events", 'x"; DROP TABLE users; --')  # nr02: hostile partition name, refused before any SQL runs


def test_partitioning_refuses_a_driver_without_it(migrated_database):
    schema = SchemaBuilder(migrated_database.make("db"))
    if schema.db.dialect.supports("partitioning"):
        pytest.skip("this driver partitions; the refusal path needs one that cannot")

    with pytest.raises(RuntimeError, match="partitioning"):
        schema.partition("events", "events_2026_08", values_from="a", values_to="b")


# -- extensions ----------------------------------------------------------------


def test_only_known_extensions_may_be_installed():
    """CREATE EXTENSION takes an identifier, and installing one is privileged."""
    schema = SchemaBuilder(_NullDb())
    with pytest.raises(ValueError, match="Unknown extension"):
        schema.extension("definitely_not_an_extension")


def test_a_known_extension_compiles_to_an_idempotent_create():
    db = _RecordingDb()
    SchemaBuilder(db).extension("pg_trgm")

    assert db.statements == [
        'CREATE EXTENSION IF NOT EXISTS "pg_trgm" WITH SCHEMA "public"'
    ]


def test_installing_an_extension_is_a_no_op_without_extension_support():
    db = _RecordingDb(driver="sqlite")
    SchemaBuilder(db).extension("pg_trgm")
    assert db.statements == []


def test_every_known_extension_says_what_it_is_for():
    for name, purpose in SchemaBuilder.KNOWN_EXTENSIONS.items():
        assert purpose and isinstance(purpose, str), name


# -- transactional migrations --------------------------------------------------


def test_a_migration_is_applied_as_one_unit(migrated_database, tmp_path):
    """A half-applied migration with no ledger row is the worst outcome."""
    from craft.migrations.migrator import Migrator

    (tmp_path / "2026_08_20_120000_broken.py").write_text(
        "from craft.facades import Schema\n"
        "def up():\n"
        "    Schema.create_table('phase6_ok', lambda t: t.id(type='integer'))\n"
        "    raise RuntimeError('halfway')\n"
        "def down():\n"
        "    Schema.drop_table('phase6_ok')\n",  # nr02: down() of a temporary migration, never run: rollback is refused
        encoding="utf-8",
    )

    migrator = Migrator(migrated_database, path=str(tmp_path))
    db = migrated_database.make("db")

    with pytest.raises(RuntimeError, match="halfway"):
        migrator.run()

    # Neither the table nor a ledger row: the migration did not happen.
    assert db.table_exists("phase6_ok") is False
    assert "2026_08_20_120000_broken" not in migrator.applied()


def test_a_migration_can_opt_out_of_its_transaction(tmp_path):
    from craft.migrations.migrator import MigrationFile

    path = tmp_path / "2026_08_20_130000_concurrent.py"
    path.write_text(
        "transactional = False\n"
        "def up():\n    pass\n"
        "def down():\n    pass\n",
        encoding="utf-8",
    )
    assert MigrationFile(str(path)).transactional is False


def test_a_migration_is_transactional_by_default(tmp_path):
    from craft.migrations.migrator import MigrationFile

    path = tmp_path / "2026_08_20_140000_plain.py"
    path.write_text("def up():\n    pass\n", encoding="utf-8")
    assert MigrationFile(str(path)).transactional is True


# -- uuid keys -----------------------------------------------------------------


def test_a_uuid_primary_key_can_default_in_the_database():
    sql = compile_pg(lambda t: t.uuid_primary(default="gen_random_uuid()"))

    assert '"id" UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY' in sql


def test_new_uuid_is_time_ordered():
    """v7: a 48-bit millisecond prefix, so inserts append rather than scatter."""
    import time

    from craft.orm.model import Model

    first = Model.new_uuid()
    time.sleep(0.005)
    second = Model.new_uuid()

    assert first[14] == "7", "not a version 7 UUID"
    assert second > first, "v7 UUIDs must sort by creation time"
    # Still a valid, parseable UUID with the right variant bits.
    import uuid

    assert str(uuid.UUID(second)) == second


# -- helpers -------------------------------------------------------------------


class _NullDb:
    driver = "postgresql"

    from craft.orm.dialect import PostgresDialect

    dialect = PostgresDialect()

    def statement(self, *args, **kwargs):
        raise AssertionError("no statement should have been executed")


class _RecordingDb:
    def __init__(self, driver="postgresql"):
        from craft.orm.dialect import dialect_for

        self.driver = driver
        self.dialect = dialect_for(driver)
        self.statements = []

    def statement(self, sql, bindings=None, read=False):
        self.statements.append(sql)

        class _Result:
            @staticmethod
            def fetchall():
                return []

            @staticmethod
            def fetchone():
                return None

        return _Result()
