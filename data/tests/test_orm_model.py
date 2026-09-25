"""Active Record model, relationships and soft deletes."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import uuid

import pytest

from craft.facades import DB
from craft.orm.model import Model
from craft.orm.exceptions import ModelNotFoundError
from craft.orm.relationships import BelongsTo, BelongsToMany, HasMany
from craft.orm.soft_deletes import SoftDeletes


#: Nothing is dropped or deleted between tests (NR-02), so the scratch tables
#: carry a suffix of this module's own and are built once, never torn down.
_SUFFIX = uuid.uuid4().hex[:8]
GADGETS = f"gadgets_{_SUFFIX}"
OWNERS = f"owners_{_SUFFIX}"
NOTES = f"notes_{_SUFFIX}"


class Gadget(Model):
    __table__ = GADGETS
    fillable = ["name", "price", "owner_id"]


class Owner(Model):
    __table__ = OWNERS
    fillable = ["name"]

    def gadgets(self):
        return self.has_many(Gadget, foreign_key="owner_id")


class Note(SoftDeletes, Model):
    """The mixin must come first so its query()/delete() win the MRO."""

    __table__ = NOTES
    fillable = ["body"]


@pytest.fixture(scope="module", autouse=True)
def tables(migrated_database):
    """Build the scratch tables once, with the framework's own schema builder.

    Using Schema rather than raw DDL keeps these tests dialect-agnostic, so the
    same suite runs on SQLite and PostgreSQL. The tables are never dropped:
    their names are unique to this module, and every assertion is scoped to
    the rows its own test wrote.
    """
    schema = migrated_database.make("schema")

    schema.create_table(OWNERS, lambda t: (
        t.id(),
        t.string("name").nullable(),
        t.timestamps(),
    ))
    schema.create_table(GADGETS, lambda t: (
        t.id(),
        t.string("name").nullable(),
        t.float("price").nullable(),
        t.big_integer("owner_id").nullable(),
        t.timestamps(),
    ))
    schema.create_table(NOTES, lambda t: (
        t.id(),
        t.text("body").nullable(),
        t.datetime("deleted_at").nullable(),
        t.timestamps(),
    ))


@pytest.fixture
def private_db():
    """Bind the container's `db` to a private in-memory SQLite for one test.

    A test whose subject is a physical `DELETE` must not run it against the
    shared database, so the model writes land here and vanish with it.
    """
    from craft.container.application import Container
    from craft.orm.db import DatabaseManager

    container = Container.getInstance()
    original = container.make("db")
    db = DatabaseManager(config={"driver": "sqlite", "database": ":memory:"})
    db.statement(
        f"CREATE TABLE {GADGETS} (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, "
        "price REAL, owner_id INTEGER, created_at TEXT, updated_at TEXT)"
    )
    db.statement(
        f"CREATE TABLE {NOTES} (id INTEGER PRIMARY KEY AUTOINCREMENT, body TEXT, "
        "deleted_at TEXT, created_at TEXT, updated_at TEXT)"
    )
    container.instance("db", db)
    try:
        yield db
    finally:
        container.instance("db", original)


def _count(table: str, row_id: int) -> int:
    """Count the rows of `table` with `row_id`, trashed ones included."""
    return DB.statement(
        f"SELECT COUNT(*) AS n FROM {table} WHERE id = ?", [row_id]
    ).fetchone()["n"]


class TestTableNaming:
    def test_explicit_table_wins(self):
        assert Gadget.get_table_name() == GADGETS

    def test_inferred_from_the_class_name(self):
        class Sprocket(Model):
            pass

        assert Sprocket.get_table_name() == "sprockets"

    @pytest.mark.parametrize("name,table", [
        ("Category", "categories"), ("BlogPost", "blog_posts"), ("Address", "addresses"),
    ])
    def test_inference_matches_the_generated_migration(self, name, table):
        from craft.cli.generators import table_for

        model = type(name, (Model,), {})
        assert model.get_table_name() == table == table_for(name)

    def test_a_table_under_the_legacy_name_is_still_found(self, migrated_database, caplog):
        schema = migrated_database.make("schema")
        schema.create_table("widgetcategorys", lambda t: (t.id(),))
        model = type("WidgetCategory", (Model,), {})
        with caplog.at_level("WARNING", logger="craft.orm"):
            assert model.get_table_name() == "widgetcategorys"
        assert "__table__" in caplog.text


class TestCreateAndRead:
    def test_create_assigns_an_id(self):
        gadget = Gadget.create({"name": "widget", "price": 9.99})
        assert gadget.get_attribute("id") is not None

    def test_create_stamps_timestamps(self):
        gadget = Gadget.create({"name": "widget"})
        assert gadget.get_attribute("created_at") is not None
        assert gadget.get_attribute("updated_at") is not None

    def test_defaults_are_applied(self):
        class Defaulted(Gadget):
            defaults = {"price": 1.0}

        assert Defaulted.create({"name": "x"}).get_attribute("price") == 1.0

    def test_explicit_values_beat_defaults(self):
        class Defaulted(Gadget):
            defaults = {"price": 1.0}

        assert Defaulted.create({"name": "x", "price": 5.0}).get_attribute("price") == 5.0

    def test_create_honours_fillable(self):
        # Mass input must not reach columns outside `fillable`.
        gadget = Gadget.create({"name": "widget", "created_by_admin": True})
        assert gadget.get_attribute("created_by_admin") is None

    def test_force_create_bypasses_fillable(self):
        gadget = Gadget.force_create({"name": "widget", "price": 2.0})
        assert gadget.get_attribute("price") == 2.0

    def test_find_by_id(self):
        created = Gadget.create({"name": "findable"})
        assert Gadget.find(created.get_attribute("id")).get_attribute("name") == "findable"

    def test_find_returns_none_when_missing(self):
        assert Gadget.find(999999) is None

    def test_find_or_fail_raises(self):
        with pytest.raises(ModelNotFoundError):
            Gadget.find_or_fail(999999)

    def test_all_returns_every_row(self):
        before = {row.get_attribute("id") for row in Gadget.all()}
        created = {
            Gadget.create({"name": "a"}).get_attribute("id"),
            Gadget.create({"name": "b"}).get_attribute("id"),
        }
        assert {row.get_attribute("id") for row in Gadget.all()} == before | created

    def test_where_shortcut(self):
        Gadget.create({"name": "target"})
        assert Gadget.where("name", "target").first() is not None

    def test_attribute_access_via_dot(self):
        assert Gadget.create({"name": "dotted"}).name == "dotted"

    def test_unknown_attribute_raises(self):
        with pytest.raises(AttributeError):
            Gadget.create({"name": "x"}).nonexistent


class TestUpdateAndDelete:
    def test_save_updates_an_existing_row(self):
        gadget = Gadget.create({"name": "before"})
        gadget.set_attribute("name", "after")
        gadget.save()
        assert Gadget.find(gadget.get_attribute("id")).get_attribute("name") == "after"

    def test_update_merges_and_persists(self):
        gadget = Gadget.create({"name": "x", "price": 1.0})
        gadget.update({"price": 2.0})
        assert Gadget.find(gadget.get_attribute("id")).get_attribute("price") == 2.0

    def test_delete_removes_the_row(self, private_db):
        gadget = Gadget.create({"name": "doomed"})
        assert private_db.statement(f"SELECT COUNT(*) AS n FROM {GADGETS}").fetchone()["n"] == 1
        assert gadget.delete() is True  # nr02: private in-memory SQLite, not the shared database
        assert Gadget.find(gadget.get_attribute("id")) is None

    def test_delete_on_an_unsaved_model_is_false(self, private_db):
        assert Gadget({"name": "unsaved"}).delete() is False  # nr02: private in-memory SQLite, not the shared database


class TestSerialization:
    def test_to_dict_exposes_attributes(self):
        assert Gadget.create({"name": "x"}).to_dict()["name"] == "x"

    def test_hidden_attributes_are_omitted(self):
        class Secretive(Gadget):
            hidden = ["price"]

        result = Secretive.create({"name": "x", "price": 1.0}).to_dict()
        assert "price" not in result and "name" in result


class TestRelationships:
    def test_has_many_returns_children(self):
        owner = Owner.create({"name": "Jane"})
        Gadget.create({"name": "a", "owner_id": owner.get_attribute("id")})
        Gadget.create({"name": "b", "owner_id": owner.get_attribute("id")})
        Gadget.create({"name": "c", "owner_id": 999})

        assert len(owner.gadgets().get()) == 2

    def test_has_many_is_a_relation_object(self):
        assert isinstance(Owner.create({"name": "x"}).gadgets(), HasMany)

    def test_relation_proxies_builder_methods(self):
        owner = Owner.create({"name": "Jane"})
        Gadget.create({"name": "cheap", "price": 1.0, "owner_id": owner.get_attribute("id")})
        Gadget.create({"name": "dear", "price": 99.0, "owner_id": owner.get_attribute("id")})

        assert len(owner.gadgets().where("price", ">", 50).get()) == 1

    def test_relation_count(self):
        owner = Owner.create({"name": "Jane"})
        Gadget.create({"name": "a", "owner_id": owner.get_attribute("id")})
        assert owner.gadgets().count() == 1

    def test_relation_create_sets_the_foreign_key(self):
        owner = Owner.create({"name": "Jane"})
        gadget = owner.gadgets().create({"name": "child"})
        assert gadget.get_attribute("owner_id") == owner.get_attribute("id")

    def test_belongs_to_resolves_the_parent(self):
        owner = Owner.create({"name": "Jane"})
        gadget = Gadget.create({"name": "a", "owner_id": owner.get_attribute("id")})
        relation = gadget.belongs_to(Owner, foreign_key="owner_id")

        assert isinstance(relation, BelongsTo)
        assert relation.first().get_attribute("name") == "Jane"

    def test_belongs_to_many_uses_the_pivot(self):
        from tests.support.models import Permission, Role, User

        suffix = uuid.uuid4().hex[:8]
        role_slug, permission_slug = f"editor-pivot-{suffix}", f"publish-pivot-{suffix}"
        user = User.create(
            {"name": "Pivot", "email": f"pivot-{suffix}@craft.local", "password": "x"}
        )
        role = Role.create({"name": role_slug, "slug": role_slug})
        permission = Permission.create({"name": permission_slug, "slug": permission_slug})

        relation = user.roles()
        assert isinstance(relation, BelongsToMany)

        relation.attach(role.get_attribute("id"))
        assert relation.count() == 1
        assert relation.first().get_attribute("slug") == role_slug

        role.permissions().attach(permission.get_attribute("id"))
        assert user.has_permission(permission_slug) is True
        assert user.has_permission("nope") is False

    def test_detach_removes_the_pivot_row(self):
        """`detach()` issues a physical `DELETE` on the pivot, so it runs on a
        private in-memory SQLite carrying the identity tables, never on the
        shared database (NR-02)."""
        from craft.container.application import Container
        from craft.migrations.schema import SchemaBuilder
        from craft.orm.db import DatabaseManager
        from tests.support.models import Role, User
        from tests.support.schema import IDENTITY_TABLES

        container = Container.getInstance()
        original = container.make("db")
        db = DatabaseManager(config={"driver": "sqlite", "database": ":memory:"})
        for name in ("users", "roles", "role_user"):
            SchemaBuilder(db).create_table(name, IDENTITY_TABLES[name])
        container.instance("db", db)
        try:
            user = User.create({"name": "Pivot", "email": "pivot@craft.local", "password": "x"})
            role = Role.create({"name": "Editor", "slug": "editor"})
            relation = user.roles()
            relation.attach(role.get_attribute("id"))
            assert relation.count() == 1

            relation.detach(role.get_attribute("id"))  # nr02: private in-memory SQLite, not the shared database
            assert relation.count() == 0
        finally:
            container.instance("db", original)


class TestSoftDeletes:
    """On a SoftDeletes model, delete only stamps `deleted_at` and keeps the row.

    Each test marks its notes with a body of its own and asks only about those,
    so rows other tests left behind never enter a count.
    """

    @pytest.fixture
    def marker(self) -> str:
        return uuid.uuid4().hex

    def test_delete_only_stamps_deleted_at(self):
        note = Note.create({"body": "keep me"})
        note.delete()  # nr02: soft delete, only stamps deleted_at
        assert note.trashed() is True
        assert _count(NOTES, note.get_attribute("id")) == 1

    def test_default_query_hides_trashed_rows(self, marker):
        Note.create({"body": marker})
        Note.create({"body": marker}).delete()  # nr02: soft delete, only stamps deleted_at
        assert len(Note.query().where("body", marker).get()) == 1

    def test_with_trashed_includes_them(self, marker):
        Note.create({"body": marker})
        Note.create({"body": marker}).delete()  # nr02: soft delete, only stamps deleted_at
        assert len(Note.with_trashed().where("body", marker).get()) == 2

    def test_only_trashed_excludes_live_rows(self, marker):
        Note.create({"body": marker})
        Note.create({"body": marker}).delete()  # nr02: soft delete, only stamps deleted_at
        assert len(Note.only_trashed().where("body", marker).get()) == 1

    def test_restore_brings_a_row_back(self, marker):
        note = Note.create({"body": marker})
        note.delete()  # nr02: soft delete, only stamps deleted_at
        note.restore()
        assert note.trashed() is False
        assert len(Note.query().where("body", marker).get()) == 1

    def test_force_delete_really_removes_the_row(self, private_db):
        note = Note.create({"body": "gone"})
        assert private_db.statement(f"SELECT COUNT(*) AS n FROM {NOTES}").fetchone()["n"] == 1
        note.force_delete()  # nr02: private in-memory SQLite, not the shared database
        count = private_db.statement(f"SELECT COUNT(*) AS n FROM {NOTES}").fetchone()["n"]
        assert count == 0


class TestPackageExports:
    """`documentation/orm.md` teaches `from craft.orm import Model`.

    The package `__init__` was empty, so every import taught by the docs raised
    ImportError — the one subpackage in the engine that exported nothing.
    """

    def test_package_root_exports_the_documented_names(self):
        import craft.orm as orm

        from craft.orm import Model as ExportedModel
        from craft.orm import ModelNotFoundError as ExportedNotFound
        from craft.orm import SoftDeletes as ExportedSoftDeletes

        assert ExportedModel is Model
        assert ExportedNotFound is ModelNotFoundError
        assert ExportedSoftDeletes is SoftDeletes
        # Every name promised by __all__ actually resolves.
        for name in orm.__all__:
            assert getattr(orm, name, None) is not None, name


class TestAttributeAssignment:
    """`model.column = value` must reach the database, not just the instance."""

    def test_assigning_an_attribute_is_saved(self):
        gadget = Gadget.create({"name": "before"})
        gadget.name = "after"
        gadget.save()
        assert Gadget.find(gadget.get_attribute("id")).get_attribute("name") == "after"

    def test_assignment_marks_the_model_dirty(self):
        gadget = Gadget.create({"name": "before"})
        gadget.price = 3.0
        assert gadget.get_dirty() == {"price": 3.0}

    def test_class_configuration_keeps_instance_semantics(self):
        gadget = Gadget({"name": "x"})
        gadget.fillable = ["name"]
        assert gadget.fillable == ["name"]
        assert "fillable" not in gadget.to_dict()

    def test_a_new_model_writes_explicitly_assigned_columns(self):
        class Locked(Gadget):
            fillable = []

        gadget = Locked()
        gadget.name = "assigned"
        gadget.save()
        assert Gadget.find(gadget.get_attribute("id")).get_attribute("name") == "assigned"

    def test_constructor_input_is_still_filtered_by_fillable(self, caplog):
        class Locked(Gadget):
            fillable = ["name"]

        with caplog.at_level("WARNING", logger="craft.orm"):
            gadget = Locked({"name": "bulk", "price": 9.0, "_token": "t"}).save()
        assert Gadget.find(gadget.get_attribute("id")).get_attribute("price") is None
        assert "discarded=['price']" in caplog.text
        assert "_token" not in caplog.text

    def test_create_warns_about_discarded_columns(self, caplog):
        with caplog.at_level("WARNING", logger="craft.orm"):
            Gadget.create({"name": "w", "created_by_admin": True})
        assert "mass_assignment_discarded" in caplog.text
        assert "created_by_admin" in caplog.text

    def test_a_misspelled_column_suggests_the_loaded_one(self):
        with pytest.raises(AttributeError, match=r"Closest: name[.]"):
            Owner.create({"name": "o"}).nmae
