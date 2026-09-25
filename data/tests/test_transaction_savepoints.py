"""A caught statement failure inside a transaction does not abort the transaction."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import uuid

import pytest

from craft.container.application import Container


@pytest.fixture
def probe() -> str:
    """A table name no other test or session uses.

    NR-02: the table is never dropped. A fresh name per test is what gives each
    test an empty table to assert on.
    """
    return f"savepoint_probe_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def db(migrated_database, is_postgres, probe):
    if not is_postgres:
        pytest.skip("PostgreSQL aborts a transaction on any failed statement; SQLite does not")
    manager = Container.getInstance().make("db")
    manager.statement(f"CREATE TABLE {probe} (code VARCHAR(10) PRIMARY KEY)")
    return manager


def _insert_ignoring_duplicates(manager, probe: str, code: str) -> None:
    try:
        manager.statement(f"INSERT INTO {probe} (code) VALUES (?)", [code])
    except Exception as exc:  # noqa: BLE001 - asserting the driver's unique violation
        assert "duplicate" in str(exc).lower() or "unique" in str(exc).lower()


def test_work_after_a_caught_failure_is_committed(db, probe) -> None:
    def work() -> None:
        _insert_ignoring_duplicates(db, probe, "A")
        _insert_ignoring_duplicates(db, probe, "A")
        _insert_ignoring_duplicates(db, probe, "B")

    db.transaction(work)
    rows = db.statement(f"SELECT code FROM {probe} ORDER BY code").fetchall()
    assert [row["code"] for row in rows] == ["A", "B"]


def test_a_select_inside_a_transaction_still_returns_its_rows(db, probe) -> None:
    def work() -> list:
        db.statement(f"INSERT INTO {probe} (code) VALUES (?)", ["C"])
        return db.statement(f"SELECT code FROM {probe}").fetchall()

    assert [row["code"] for row in db.transaction(work)] == ["C"]


def test_an_uncaught_failure_still_rolls_everything_back(db, probe) -> None:
    def work() -> None:
        db.statement(f"INSERT INTO {probe} (code) VALUES (?)", ["D"])
        db.statement(f"INSERT INTO {probe} (code) VALUES (?)", ["D"])

    with pytest.raises(Exception):  # noqa: B017 - any driver integrity error
        db.transaction(work)
    assert db.statement(f"SELECT code FROM {probe}").fetchall() == []
