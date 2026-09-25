"""BelongsToMany.attach/detach/sync respect a tenant column on the pivot table."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import uuid

import pytest

from craft.facades import Tenant
from craft.migrations.schema import SchemaBuilder
from craft.orm.model import Model
from craft.orm.tenant_scoped import TenantScoped

ACME = "11111111-1111-1111-1111-111111111111"
BETA = "22222222-2222-2222-2222-222222222222"

#: Pivot table names, read at call time. NR-02 forbids dropping the tables a
#: test used, so every test gets fresh ones under names of its own instead:
#: the fixtures fill this in and point the models' `__table__` at them.
PIVOTS = {"project_tag": "rel_project_tag", "widget_label": "rel_widget_label"}


class Project(TenantScoped, Model):
    __table__ = "rel_projects"
    fillable = ["name"]
    uses_uuid = False

    def tags(self):
        return self.belongs_to_many(Tag, pivot_table=PIVOTS["project_tag"])


class Tag(TenantScoped, Model):
    __table__ = "rel_tags"
    fillable = ["label"]
    uses_uuid = False

    def projects(self):
        return self.belongs_to_many(Project, pivot_table=PIVOTS["project_tag"])


class Widget(Model):
    __table__ = "rel_widgets"
    fillable = ["name"]
    uses_uuid = False

    def labels(self):
        return self.belongs_to_many(Label, pivot_table=PIVOTS["widget_label"])


class Label(Model):
    __table__ = "rel_labels"
    fillable = ["name"]
    uses_uuid = False


def _fresh(base: str) -> str:
    """A table name no earlier test or session has used."""
    return f"{base}_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def tenanted_pivot_tables(migrated_database, monkeypatch):
    """A fresh many-to-many pair whose pivot table carries tenant_id.

    Fresh per test, so ids restart at 1 in each table - the coincidence of
    matching foreign keys the detach test depends on.
    """
    schema = SchemaBuilder(migrated_database.make("db"))
    projects, tags, pivot = _fresh("rel_projects"), _fresh("rel_tags"), _fresh("rel_project_tag")
    schema.create_table(projects, lambda t: (
        t.id(type="integer"), t.string("name"), t.tenant_scoped(references=None), t.timestamps(),
    ))
    schema.create_table(tags, lambda t: (
        t.id(type="integer"), t.string("label"), t.tenant_scoped(references=None), t.timestamps(),
    ))
    schema.create_table(pivot, lambda t: (
        t.id(type="integer"),
        t.integer("project_id"),
        t.integer("tag_id"),
        t.tenant_scoped(references=None),
    ))
    monkeypatch.setattr(Project, "__table__", projects)
    monkeypatch.setattr(Tag, "__table__", tags)
    monkeypatch.setitem(PIVOTS, "project_tag", pivot)
    return pivot


@pytest.fixture
def untenanted_pivot_tables(migrated_database, monkeypatch):
    """A fresh many-to-many pair whose pivot table has no tenant column at all."""
    schema = SchemaBuilder(migrated_database.make("db"))
    widgets, labels, pivot = _fresh("rel_widgets"), _fresh("rel_labels"), _fresh("rel_widget_label")
    schema.create_table(widgets, lambda t: (t.id(type="integer"), t.string("name"), t.timestamps()))
    schema.create_table(labels, lambda t: (t.id(type="integer"), t.string("name"), t.timestamps()))
    schema.create_table(pivot, lambda t: (
        t.id(type="integer"), t.integer("widget_id"), t.integer("label_id"),
    ))
    monkeypatch.setattr(Widget, "__table__", widgets)
    monkeypatch.setattr(Label, "__table__", labels)
    monkeypatch.setitem(PIVOTS, "widget_label", pivot)
    return pivot


def test_attach_stamps_the_bound_tenant_on_the_pivot_row(tenanted_pivot_tables):
    with Tenant.scope(ACME):
        project = Project.create({"name": "P1"})
        tag = Tag.create({"label": "T1"})
        project.tags().attach(tag.id)

        from craft.facades import DB

        row = DB.table(tenanted_pivot_tables).where("project_id", project.id).first()
        assert row["tenant_id"] == ACME


def test_detach_never_reaches_another_tenants_pivot_row(tenanted_pivot_tables):
    with Tenant.scope(ACME):
        acme_project = Project.create({"name": "P-acme"})
        acme_tag = Tag.create({"label": "T-acme"})
        acme_project.tags().attach(acme_tag.id)

    with Tenant.scope(BETA):
        beta_project = Project.create({"name": "P-beta"})
        beta_tag = Tag.create({"label": "T-beta"})
        beta_project.tags().attach(beta_tag.id)

    from craft.facades import DB

    # BETA's detach() must not touch ACME's pivot row, even by coincidence of
    # matching foreign keys (both projects/tags start at id=1 in fresh tables).
    with Tenant.scope(BETA):
        beta_project.tags().detach(beta_tag.id)

    with Tenant.scope(ACME):
        surviving = DB.table(tenanted_pivot_tables).where("project_id", acme_project.id).first()
        assert surviving is not None


def test_sync_replaces_only_the_bound_tenants_pivot_rows(tenanted_pivot_tables):
    with Tenant.scope(ACME):
        project = Project.create({"name": "P2"})
        tag_a = Tag.create({"label": "A"})
        tag_b = Tag.create({"label": "B"})
        project.tags().attach(tag_a.id)

        project.tags().sync([tag_b.id])

        from craft.facades import DB

        rows = DB.table(tenanted_pivot_tables).where("project_id", project.id).get()
        assert [row["tag_id"] for row in rows] == [tag_b.id]
        assert all(row["tenant_id"] == ACME for row in rows)


def test_attach_and_detach_are_unchanged_when_the_pivot_has_no_tenant_column(
    untenanted_pivot_tables,
):
    """No tenant handling kicks in for a plain (non-tenant-scoped) pivot."""
    widget = Widget.create({"name": "W1"})
    label = Label.create({"name": "L1"})

    widget.labels().attach(label.id)

    from craft.facades import DB

    row = DB.table(untenanted_pivot_tables).where("widget_id", widget.id).first()
    assert row is not None
    assert "tenant_id" not in row

    widget.labels().detach(label.id)
    assert DB.table(untenanted_pivot_tables).where("widget_id", widget.id).first() is None
