"""A seeder declaring `SEED_ONCE` runs exactly once per node, through the ledger."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from engine.seeding import Seeder
from engine.seeding.ledger import SeedLedger, once_key


def _app():
    from bootstrap.app import app

    return app


def test_once_key_is_none_for_a_plain_seeder():
    class Plain(Seeder):
        pass

    assert once_key(Plain) is None


def test_once_key_keys_on_the_class_name_or_the_declared_string():
    class Once(Seeder):
        SEED_ONCE = True

    class Keyed(Seeder):
        SEED_ONCE = "catalog"

    assert once_key(Once) == f"{Once.__module__}.{Once.__name__}"
    assert once_key(Keyed) == "catalog"


def test_a_once_seeder_runs_only_once(migrated_database):
    runs = []

    class Counting(Seeder):
        SEED_ONCE = "test:counting:once"

        def run(self) -> None:
            runs.append(1)

    root = Seeder(_app())
    root.call([Counting])
    root.call([Counting])

    assert len(runs) == 1
    assert SeedLedger(_app()).has("test:counting:once") is True


def test_a_plain_seeder_runs_every_time(migrated_database):
    runs = []

    class Always(Seeder):
        def run(self) -> None:
            runs.append(1)

    root = Seeder(_app())
    root.call([Always])
    root.call([Always])

    assert len(runs) == 2


def test_the_ledger_records_what_ran(migrated_database):
    ledger = SeedLedger(_app())
    assert ledger.record("test:append", note="first") is True
    assert ledger.has("test:append") is True

    row = _app().make("db").statement(
        'SELECT "key", note FROM seed_ledger WHERE "key" = ?', ["test:append"], read=True
    ).fetchone()
    assert row["note"] == "first"
