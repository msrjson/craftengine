"""`data:audit` - rows that already break the schema's own promises."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import os
import uuid

import pytest
from typer.testing import CliRunner

from craft.cli import app as cli_module
from craft.support import doctor as checks

#: Read at import: `conftest` turns the suite's target from `CRAFT_TEST_DB`.
_IS_POSTGRES = os.environ.get("CRAFT_TEST_DB", "sqlite").lower() in (
    "pgsql", "postgres", "postgresql",
)

#: Nothing is dropped (NR-02), so the scratch tables carry this module's own
#: suffix and are built once.
_SUFFIX = uuid.uuid4().hex[:8]
PARENTS = f"audit_parents_{_SUFFIX}"
CHILDREN = f"audit_children_{_SUFFIX}"
ORPHANS = f"audit_orphans_{_SUFFIX}"
TENANTED = f"audit_tenanted_{_SUFFIX}"
_ABSENT_PARENT = 2_147_483_000


def _child_blueprint(table):
    def build(t):
        t.id()
        t.string("name").nullable()
        t.big_integer("parent_id").nullable().on(PARENTS)
        t.timestamps()
    return build


@pytest.fixture(scope="module", autouse=True)
def tables(migrated_database):
    schema = migrated_database.make("schema")
    schema.create_table(PARENTS, lambda t: (
        t.id(),
        t.string("name").nullable(),
        t.timestamps(),
    ))
    schema.create_table(CHILDREN, _child_blueprint(CHILDREN))
    schema.create_table(ORPHANS, _child_blueprint(ORPHANS))
    schema.create_table(TENANTED, lambda t: (
        t.id(),
        t.string("name").nullable(),
        t.uuid("tenant_id").nullable(),
        t.timestamps(),
    ))

    db = migrated_database.make("db")
    parent_id = db.table(PARENTS).insert({"name": "present"})
    db.table(CHILDREN).insert({"name": "valid", "parent_id": parent_id})
    db.table(TENANTED).insert({"name": "outside every tenant"})

    # An orphan cannot be inserted while the constraint is enforced, and
    # PostgreSQL offers no way to suspend one for a single statement. SQLite
    # does, on the connection the suite is using.
    if not _IS_POSTGRES:
        db.statement("PRAGMA foreign_keys = OFF")
        try:
            db.table(ORPHANS).insert({"name": "orphan", "parent_id": _ABSENT_PARENT})
        finally:
            db.statement("PRAGMA foreign_keys = ON")
    yield


def _findings(app):
    return list(checks.run_data_audit(app))


def _orphans(app, table):
    return [
        finding for finding in _findings(app)
        if finding.code == "FOREIGN_KEY_ORPHANED"
        and finding.where == f"{table}.parent_id"
    ]


def test_a_foreign_key_is_introspected(migrated_database):
    keys = migrated_database.make("schema").foreign_keys(CHILDREN)
    assert ("parent_id", PARENTS, "id") in keys


def test_a_child_whose_parent_exists_is_not_reported(migrated_database):
    """The audit runs its scan without flagging a row that has its parent."""
    assert _orphans(migrated_database, CHILDREN) == []


def test_an_orphaned_foreign_key_is_reported_once(migrated_database):
    if _IS_POSTGRES:
        pytest.skip("PostgreSQL cannot hold an orphan under an enforced constraint")
    orphans = _orphans(migrated_database, ORPHANS)
    assert len(orphans) == 1
    assert dict(orphans[0].params)["count"] == "1"
    assert orphans[0].level == checks.ERROR


def test_a_null_tenant_id_is_reported(migrated_database):
    nulls = [
        finding for finding in _findings(migrated_database)
        if finding.code == "TENANT_COLUMN_NULL" and finding.where == TENANTED
    ]
    assert len(nulls) == 1
    assert dict(nulls[0].params)["count"] == "1"


def test_a_table_without_a_tenant_column_is_never_flagged(migrated_database):
    where = {finding.where for finding in _findings(migrated_database)}
    assert PARENTS not in where
    assert CHILDREN not in where


def test_the_data_audit_cli_runs_and_summarises():
    result = CliRunner().invoke(cli_module.cli, ["data", "audit"])
    assert result.exit_code in (0, 1)
    assert "finding(s)" in result.output
