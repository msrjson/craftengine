"""UUID as the framework's public identifier, alongside the integer key."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import re
import uuid as uuid_module

import pytest

from craft.facades import DB
from craft.orm.exceptions import ModelNotFoundError
from craft.orm.model import Model

#: Version 7, RFC 4122 variant. The framework moved off version 4 because a
#: uniformly random key scatters every insert across the whole index, while a
#: v7's 48-bit millisecond prefix keeps them appending to one side of it — same
#: opacity in a URL, materially cheaper to index. The version digit is asserted
#: rather than wildcarded so a silent regression back to v4 fails here.
UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


class Widget(Model):
    """Has the public uuid column."""

    __table__ = "uuid_widgets"
    fillable = ["name"]


class Legacy(Model):
    """No uuid column — the framework must leave it alone."""

    __table__ = "uuid_legacy"
    fillable = ["name"]


class OptedOut(Model):
    """Table has a nullable uuid column, but the model declines to fill it."""

    __table__ = "uuid_optional"
    fillable = ["name"]
    uses_uuid = False


class UuidKeyed(Model):
    """The UUID *is* the primary key."""

    __table__ = "uuid_keyed"
    fillable = ["name"]
    key_type = "uuid"


@pytest.fixture(autouse=True)
def tables(migrated_database):
    schema = migrated_database.make("schema")
    names = ["uuid_widgets", "uuid_legacy", "uuid_keyed", "uuid_optional"]
    for name in names:
        schema.drop_table(name)

    schema.create_table("uuid_widgets", lambda t: (
        t.id(),
        t.uuid_key(),
        t.string("name").nullable(),
        t.timestamps(),
    ))
    schema.create_table("uuid_legacy", lambda t: (
        t.id(),
        t.string("name").nullable(),
        t.timestamps(),
    ))
    schema.create_table("uuid_keyed", lambda t: (
        t.uuid_primary(),
        t.string("name").nullable(),
        t.timestamps(),
    ))
    schema.create_table("uuid_optional", lambda t: (
        t.id(),
        t.uuid("uuid").nullable(),
        t.string("name").nullable(),
        t.timestamps(),
    ))
    migrated_database.make("db").forget_schema_cache()

    yield

    for name in names:
        schema.drop_table(name)
    migrated_database.make("db").forget_schema_cache()


class TestSchemaBuilder:
    def test_uuid_key_is_unique(self, migrated_database):
        from craft.migrations.schema import Blueprint, Grammar

        blueprint = Blueprint("t")
        blueprint.uuid_key()
        sql = Grammar("postgresql").compile_create(blueprint)[0]
        assert "UNIQUE" in sql

    def test_uuid_key_uses_the_native_type_on_postgres(self):
        from craft.migrations.schema import Blueprint, Grammar

        blueprint = Blueprint("t")
        blueprint.uuid_key()
        assert "UUID" in Grammar("postgresql").compile_create(blueprint)[0]

    def test_uuid_key_falls_back_to_varchar_elsewhere(self):
        from craft.migrations.schema import Blueprint, Grammar

        blueprint = Blueprint("t")
        blueprint.uuid_key()
        assert "VARCHAR(36)" in Grammar("sqlite").compile_create(blueprint)[0]

    def test_uuid_primary_is_the_key(self):
        from craft.migrations.schema import Blueprint, Grammar

        blueprint = Blueprint("t")
        blueprint.uuid_primary()
        assert "PRIMARY KEY" in Grammar("sqlite").compile_create(blueprint)[0]


class TestAutomaticUuid:
    def test_create_fills_the_uuid(self):
        widget = Widget.create({"name": "first"})
        assert UUID_RE.match(widget.get_attribute("uuid"))

    def test_the_integer_key_is_still_assigned(self):
        widget = Widget.create({"name": "first"})
        assert isinstance(widget.get_attribute("id"), int)

    def test_the_uuid_reaches_the_database(self):
        widget = Widget.create({"name": "persisted"})
        row = DB.statement(
            "SELECT uuid FROM uuid_widgets WHERE id = ?",
            [widget.get_attribute("id")],
            read=True,
        ).fetchone()
        assert row["uuid"] == widget.get_attribute("uuid")

    def test_each_record_gets_a_different_uuid(self):
        first = Widget.create({"name": "a"})
        second = Widget.create({"name": "b"})
        assert first.get_attribute("uuid") != second.get_attribute("uuid")

    def test_an_explicit_uuid_is_respected(self):
        given = str(uuid_module.uuid4())
        widget = Widget.create({"name": "given", "uuid": given})
        assert widget.get_attribute("uuid") == given

    def test_a_table_without_the_column_is_untouched(self):
        # Nothing may be inserted that the schema does not declare.
        legacy = Legacy.create({"name": "old"})
        assert legacy.get_attribute("id") is not None
        assert legacy.get_attribute("uuid") is None

    def test_opting_out_skips_generation(self):
        record = OptedOut.create({"name": "no-uuid"})
        assert record.get_attribute("uuid") is None


class TestLookup:
    def test_find_by_uuid(self):
        widget = Widget.create({"name": "findable"})
        found = Widget.find_by_uuid(widget.get_attribute("uuid"))
        assert found.get_attribute("id") == widget.get_attribute("id")

    def test_find_by_uuid_returns_none_when_absent(self):
        assert Widget.find_by_uuid(str(uuid_module.uuid4())) is None

    def test_find_by_uuid_or_fail_raises(self):
        with pytest.raises(ModelNotFoundError):
            Widget.find_by_uuid_or_fail(str(uuid_module.uuid4()))

    def test_find_still_works_on_the_integer_key(self):
        widget = Widget.create({"name": "by-id"})
        assert Widget.find(widget.get_attribute("id")) is not None

    def test_find_automatically_resolves_uuid_string(self):
        widget = Widget.create({"name": "by-uuid-string"})
        found = Widget.find(widget.get_attribute("uuid"))
        assert found is not None
        assert found.get_attribute("id") == widget.get_attribute("id")



class TestRouteKey:
    def test_route_key_is_the_uuid(self):
        widget = Widget.create({"name": "routed"})
        assert widget.route_key() == widget.get_attribute("uuid")

    def test_route_key_falls_back_to_the_id(self):
        legacy = Legacy.create({"name": "old"})
        assert legacy.route_key() == legacy.get_attribute("id")

    def test_find_by_route_key_resolves_a_uuid(self):
        widget = Widget.create({"name": "routed"})
        found = Widget.find_by_route_key(widget.route_key())
        assert found.get_attribute("id") == widget.get_attribute("id")

    def test_find_by_route_key_resolves_an_integer(self):
        legacy = Legacy.create({"name": "old"})
        assert Legacy.find_by_route_key(legacy.get_attribute("id")) is not None

    def test_find_by_route_key_rejects_sequential_integer_for_uuid_model(self):
        widget = Widget.create({"name": "routed-seq"})
        assert Widget.find_by_route_key(widget.get_attribute("id")) is None
        assert Widget.find_by_route_key(str(widget.get_attribute("id"))) is None

    def test_find_by_uuid_rejects_sequential_integer(self):
        widget = Widget.create({"name": "uuid-seq"})
        assert Widget.find_by_uuid(str(widget.get_attribute("id"))) is None


class TestUuidPrimaryKey:
    def test_the_primary_key_is_a_uuid(self):
        record = UuidKeyed.create({"name": "keyed"})
        assert UUID_RE.match(str(record.get_attribute("id")))

    def test_it_can_be_found_by_that_key(self):
        record = UuidKeyed.create({"name": "keyed"})
        assert UuidKeyed.find(record.get_attribute("id")) is not None


class TestSchemaCache:
    def test_the_cache_is_scoped_to_the_connection(self, migrated_database):
        # Caching this on the model class meant swapping to a database whose
        # table had no uuid column still reported that it did.
        db = migrated_database.make("db")
        assert db.table_has_column("uuid_widgets", "uuid") is True
        assert db.table_has_column("uuid_legacy", "uuid") is False

    def test_forgetting_the_cache_rereads_the_schema(self, migrated_database):
        db = migrated_database.make("db")
        schema = migrated_database.make("schema")
        assert db.table_has_column("uuid_widgets", "uuid") is True

        # Build through the schema builder, not raw DDL — this test runs on
        # SQLite and PostgreSQL alike.
        schema.drop_table("uuid_widgets")
        db.forget_schema_cache()
        assert db.table_has_column("uuid_widgets", "uuid") is False

        schema.create_table("uuid_widgets", lambda t: (
            t.id(),
            t.uuid_key(),
            t.string("name").nullable(),
            t.timestamps(),
        ))
        db.forget_schema_cache()
        assert db.table_has_column("uuid_widgets", "uuid") is True


class TestFrameworkTables:
    """The shipped migration puts a uuid on the framework's own tables."""

    def test_users_have_a_uuid_column(self, migrated_database):
        assert migrated_database.make("db").table_has_column("users", "uuid")

    def test_a_new_user_gets_one(self, migrated_database):
        from tests.support.models import User

        DB.statement("DELETE FROM users WHERE email = 'uuid@craft.local'")
        user = User.create(
            {"name": "UUID", "email": "uuid@craft.local", "password": "secret"}
        )
        assert UUID_RE.match(user.get_attribute("uuid"))
