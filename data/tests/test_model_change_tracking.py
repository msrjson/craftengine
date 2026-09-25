"""Model.save writes only changed columns and never crosses the loaded tenant."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import uuid
from typing import Any

import pytest

from craft.container.application import Container
from craft.orm.model import Model
from craft.orm.tenancy import TenantManager
from craft.orm.tenant_scoped import TenantScoped


#: Nothing is dropped between tests (NR-02): the scratch tables carry a
#: suffix of this module's own and are built once.
_SUFFIX = uuid.uuid4().hex[:8]
TICKETS = f"tracking_tickets_{_SUFFIX}"
INVOICES = f"tracking_invoices_{_SUFFIX}"


class Ticket(Model):
    __table__ = TICKETS
    fillable = ["title", "status"]
    casts = {"meta": "json"}


class Invoice(TenantScoped, Model):
    __table__ = INVOICES
    fillable = ["number", "tenant_id"]


@pytest.fixture(scope="module", autouse=True)
def tables(migrated_database):
    schema = migrated_database.make("schema")
    schema.create_table(TICKETS, lambda t: (
        t.id(), t.string("title").nullable(), t.string("status").nullable(),
        t.text("meta").nullable(), t.timestamps(),
    ))
    schema.create_table(INVOICES, lambda t: (
        t.id(), t.string("number").nullable(), t.string("tenant_id").nullable(), t.timestamps(),
    ))


@pytest.fixture
def private_db():
    """Bind the container's `db` to a private in-memory SQLite for one test.

    The cross-tenant delete probe issues a real `DELETE`; if the guard ever
    regressed it would destroy a row, so it never runs on the shared database.
    """
    from craft.orm.db import DatabaseManager

    container = Container.getInstance()
    original = container.make("db")
    db = DatabaseManager(config={"driver": "sqlite", "database": ":memory:"})
    db.statement(
        f"CREATE TABLE {INVOICES} (id INTEGER PRIMARY KEY AUTOINCREMENT, number TEXT, "
        "tenant_id TEXT, created_at TEXT, updated_at TEXT)"
    )
    container.instance("db", db)
    try:
        yield db
    finally:
        container.instance("db", original)


def _capture_statements(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    manager = Container.getInstance().make("db")
    captured: list[str] = []
    original = manager.statement

    def spy(query: str, *args: Any, **kwargs: Any) -> Any:
        captured.append(query)
        return original(query, *args, **kwargs)

    monkeypatch.setattr(manager, "statement", spy)
    return captured


def test_concurrent_edits_to_different_columns_both_survive() -> None:
    created = Ticket.create({"title": "Draft", "status": "open"})
    first = Ticket.find(created.id)
    second = Ticket.find(created.id)
    first.set_attribute("title", "Final")
    second.set_attribute("status", "closed")
    first.save()
    second.save()
    reloaded = Ticket.find(created.id)
    assert (reloaded.title, reloaded.status) == ("Final", "closed")


def test_a_clean_model_issues_no_update(monkeypatch: pytest.MonkeyPatch) -> None:
    ticket = Ticket.find(Ticket.create({"title": "Draft"}).id)
    statements = _capture_statements(monkeypatch)
    ticket.save()
    assert not [query for query in statements if query.lstrip().upper().startswith("UPDATE")]


def test_dirty_state_resets_after_save() -> None:
    ticket = Ticket.find(Ticket.create({"title": "Draft"}).id)
    ticket.set_attribute("title", "Final")
    assert ticket.get_dirty() == {"title": "Final"}
    ticket.save()
    assert not ticket.is_dirty()


def test_in_place_mutation_of_a_cast_value_is_detected() -> None:
    ticket = Ticket.create({"title": "Draft"})
    ticket.set_attribute("meta", {"tags": []})
    ticket.save()
    ticket = Ticket.find(ticket.id)
    ticket.meta["tags"].append("urgent")
    assert "meta" in ticket.get_dirty()
    ticket.save()
    assert Ticket.find(ticket.id).meta == {"tags": ["urgent"]}


def test_update_never_reaches_a_row_of_another_tenant() -> None:
    with TenantManager().scope("tenant-b"):
        victim = Invoice.create({"number": "B-1"})
    with TenantManager().scope("tenant-a"):
        forged = Invoice({"id": victim.id, "number": "A-1", "tenant_id": "tenant-a"})
        forged.set_attribute("number", "HIJACKED")
        forged.save()
    with TenantManager().scope("tenant-b"):
        assert Invoice.find(victim.id).number == "B-1"


def test_delete_never_reaches_a_row_of_another_tenant(private_db: Any) -> None:
    with TenantManager().scope("tenant-b"):
        victim = Invoice.create({"number": "B-2"})
    with TenantManager().scope("tenant-a"):
        Invoice({"id": victim.id, "tenant_id": "tenant-a"}).delete()  # nr02: private in-memory SQLite, not the shared database
    with TenantManager().scope("tenant-b"):
        assert Invoice.find(victim.id) is not None
    assert private_db.statement(f"SELECT COUNT(*) AS n FROM {INVOICES}").fetchone()["n"] == 1
