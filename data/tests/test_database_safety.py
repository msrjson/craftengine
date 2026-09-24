"""NR-02: schema-wide destructive operations refuse permanent databases."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from types import SimpleNamespace
from typing import Any

import pytest

from craft.migrations.migrator import Migrator
from craft.migrations.safety import (
    DestructiveOperationRefused,
    assert_disposable,
    is_disposable_database,
)


class _Config:
    def __init__(self, values: dict[str, Any]) -> None:
        self._values = values

    def get(self, key: str, default: Any = None) -> Any:
        return self._values.get(key, default)


def _app(environment: str = "local", disposable: str = "") -> SimpleNamespace:
    config = _Config({"app.APP_ENV": environment, "database.disposable_databases": disposable})
    return SimpleNamespace(make=lambda key: config)


def _db(driver: str, database: str) -> SimpleNamespace:
    connection = SimpleNamespace(config={"database": database})
    return SimpleNamespace(driver=driver, write_connection=connection)


@pytest.mark.parametrize(
    ("driver", "database", "allowlist", "expected"),
    [
        ("sqlite", ":memory:", (), False),
        ("sqlite", "storage/database.sqlite", (), False),
        ("sqlite", "storage/app_test.sqlite", (), False),
        ("postgresql", "craft_db", (), False),
        ("postgresql", "craft_test", (), False),
        ("postgresql", "craft_testing", (), False),
        ("postgresql", "scratch", ("scratch",), False),
        ("postgresql", "scratch", (" ",), False),
    ],
)
def test_is_disposable_database(driver: str, database: str, allowlist: tuple[str, ...], expected: bool) -> None:
    assert is_disposable_database(driver, database, allowlist) is expected


def test_permanent_database_is_refused_with_code_and_key() -> None:
    with pytest.raises(DestructiveOperationRefused) as refused:
        assert_disposable(_app(), _db("postgresql", "craft_db"), "drop_all_tables")
    assert refused.value.code == "DATABASE_DESTRUCTIVE_OPERATION_REFUSED"
    assert refused.value.message_key == "database.safety.destructive_operation_refused"
    assert refused.value.params["database"] == "craft_db"


def test_production_refuses_even_a_test_database() -> None:
    with pytest.raises(DestructiveOperationRefused):
        assert_disposable(_app("production"), _db("postgresql", "craft_test"), "reset")


def test_allowlist_cannot_enable_destructive_operations() -> None:
    with pytest.raises(DestructiveOperationRefused):
        assert_disposable(_app(disposable="scratch, preview"), _db("postgresql", "preview"), "reset")


def test_migrator_fresh_never_touches_a_permanent_database() -> None:
    db = _db("postgresql", "craft_db")
    db.statement = lambda *args, **kwargs: pytest.fail("a statement ran against a permanent database")
    migrator = Migrator(SimpleNamespace(base_path=".", make=lambda key: db if key == "db" else _app().make(key)))
    for operation in (migrator.fresh, migrator.drop_all_tables, migrator.reset, migrator.refresh, migrator.rollback):
        with pytest.raises(DestructiveOperationRefused):
            operation()


def test_cli_wipe_exits_non_zero_on_a_permanent_database(monkeypatch: pytest.MonkeyPatch) -> None:
    from typer.testing import CliRunner

    from craft.cli import app as cli

    def refuse() -> None:
        raise DestructiveOperationRefused("drop_all_tables", "craft_db", "local")

    monkeypatch.setattr(cli, "get_migrator", lambda: SimpleNamespace(drop_all_tables=refuse))
    result = CliRunner().invoke(cli.cli, ["db", "wipe", "--force"])
    assert result.exit_code == 1
    assert "NR-02" in result.output
