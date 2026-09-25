"""Second round of placebo regressions — ORM, schema and view helpers.

Same theme as `test_placebo_regressions.py`: code that looked implemented from
the outside and quietly did something else, or nothing.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import uuid

import pytest
from craft.migrations.schema import Blueprint, Grammar
from craft.orm.model import Model
from craft.orm.soft_deletes import SoftDeletes


class TestViewHelperDoesNotFakeSuccess:
    def test_a_broken_template_raises_instead_of_returning_200(self, migrated_database):
        """`craft.support.view()` caught every exception and returned
        `"View x rendered"` with HTTP 200, so a missing template, a syntax
        error or an undefined variable all looked like a successful page."""
        from craft.support import view

        with pytest.raises(Exception) as excinfo:
            view("this.template.does.not.exist")

        assert "rendered" not in str(excinfo.value).lower()


class TestAggregatesValidateTheirColumn:
    """Aggregates interpolated the column straight into SQL — the one hole in
    an identifier allowlist the rest of the query builder applies everywhere."""

    @pytest.mark.parametrize("method", ["sum", "avg", "max", "min"])
    def test_an_injected_column_is_rejected(self, migrated_database, method):
        from tests.support.models import User

        builder = User.query()
        with pytest.raises(Exception):
            getattr(builder, method)("id) FROM users; DROP TABLE users --")  # nr02: hostile payload, rejected before any SQL runs

    def test_count_star_still_works(self, migrated_database):
        from tests.support.models import User

        assert isinstance(User.query().count(), int)

    def test_count_rejects_an_injected_column(self, migrated_database):
        from tests.support.models import User

        with pytest.raises(Exception):
            User.query().count("*) FROM users; DROP TABLE users --")  # nr02: hostile payload, rejected before any SQL runs


class TestRbacLivesOnTheRightModels:
    """`roles()`/`permissions()`/`has_role()`/`has_permission()` sat on the base
    `Model`, hardwired to `role_user.user_id` — so `Post.find(1).roles()`
    returned the roles of *user* 1, with no error."""

    def test_a_plain_model_does_not_answer_rbac_questions(self):
        from craft.orm.model import Model

        class PlainItem(Model):
            __table__ = "plain_items"

        assert not hasattr(PlainItem, "roles")
        assert not hasattr(PlainItem, "has_role")
        assert not hasattr(PlainItem, "has_permission")

    def test_the_configured_user_model_still_does(self, migrated_database):
        """Read through the registry rather than importing a model directly:
        what has to answer RBAC is whichever class the project configured."""
        from craft.auth.registry import model_for

        user_model = model_for("user", migrated_database.make("config"))

        assert hasattr(user_model, "roles")
        assert hasattr(user_model, "has_role")
        assert hasattr(user_model, "has_permission")

    def test_permissions_belongs_to_the_configured_role_model(self, migrated_database):
        from craft.auth.registry import model_for

        assert hasattr(model_for("role", migrated_database.make("config")), "permissions")

    def test_the_engine_no_longer_imports_application_models(self):
        """The base model importing `app.Models.Role` pointed the framework at
        the application it is supposed to be independent of.

        Parsed rather than grepped: a comment explaining the old coupling is
        not the coupling.
        """
        import ast
        import inspect

        import craft.orm.model as model_module

        tree = ast.parse(inspect.getsource(model_module))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
            elif isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)

        assert not [name for name in imported if name.startswith("app.")]


class TestSoftDeletesRefusesTheBrokenBaseOrder:
    def test_listing_the_mixin_after_model_is_an_error(self):
        """With `class X(Model, SoftDeletes)` the MRO gives the base `Model.delete`,
        so rows are destroyed by a call the developer believes is reversible."""
        with pytest.raises(TypeError) as excinfo:

            class Wrong(Model, SoftDeletes):
                __table__ = "wrong"

        assert "SoftDeletes" in str(excinfo.value)

    def test_the_correct_order_is_accepted(self):
        class Right(SoftDeletes, Model):
            __table__ = "right_order"

        assert Right.__table__ == "right_order"


class TestSchemaCompilesWhatItAccepts:
    def test_adding_a_column_also_creates_its_index(self):
        """`Schema.table()` compiled only the ADD COLUMN, so `.indexed()` and
        `unique_index()` were accepted and silently discarded."""
        blueprint = Blueprint("widgets")
        blueprint.string("code").indexed()
        blueprint.unique_index(["code"], name="uniq_widgets_code")

        statements = Grammar("sqlite").compile_add_columns(blueprint)

        assert any("ADD COLUMN" in s for s in statements)
        assert any("CREATE UNIQUE INDEX" in s for s in statements)

    def test_enum_emits_a_check_constraint(self):
        """`enum()` stored its values in `Column.comment`, which no grammar
        reads — the column was a plain VARCHAR accepting anything."""
        blueprint = Blueprint("orders")
        blueprint.enum("status", ["pending", "paid"])

        sql = " ".join(Grammar("sqlite").compile_create(blueprint))

        assert "CHECK" in sql
        assert "'pending'" in sql and "'paid'" in sql

    def test_enum_escapes_quotes_in_values(self):
        blueprint = Blueprint("orders")
        blueprint.enum("label", ["it's"])

        sql = " ".join(Grammar("sqlite").compile_create(blueprint))

        assert "'it''s'" in sql

    def test_enum_rejects_an_empty_value_list(self):
        with pytest.raises(ValueError):
            Blueprint("orders").enum("status", [])


class TestColumnProbeFailureIsNotCached:
    def test_a_failed_probe_can_be_retried(self, migrated_database):
        """Caching the failure as "this table has no columns" switched off every
        column-conditional feature for the life of the process — including the
        public UUID the ORM advertises."""
        from craft.container.application import Container

        db = Container.getInstance().make("db")
        db.forget_schema_cache()

        assert db.table_has_column("no_such_table_at_all", "whatever") is False
        # The failure must not be memoised, so a real table still resolves.
        assert db.table_has_column("users", "email") is True


class TestSettingsReportWhetherTheyPersisted:
    def test_set_returns_true_when_it_reaches_the_database(self, migrated_database):
        """It returned `None` whether the write landed or fell through to an
        in-memory dict that dies with the process."""
        from craft.support.settings import SettingManager

        key = f"placebo_check_key_{uuid.uuid4().hex[:8]}"
        assert SettingManager.set(key, "value") is True
        assert SettingManager.get(key) == "value"
