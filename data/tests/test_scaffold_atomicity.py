"""Generators are all-or-nothing: a failure never leaves half a scaffold behind.

v4.4.0 shipped without the layout template. `make admin` copied the whole panel,
then failed on the layout, and every later run refused to overwrite what it had
left: the project could not get an admin panel without `--force`. Found by the
CRM demo rehearsal.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import os

import pytest

from engine.cli import admin_scaffolder, auth_scaffolder, layout_scaffolder


def _files(root) -> list:
    return sorted(str(path.relative_to(root)) for path in root.rglob("*") if path.is_file())


@pytest.fixture
def project(tmp_path):
    (tmp_path / "routes").mkdir()
    (tmp_path / "routes" / "web.py").write_text("")
    return tmp_path


@pytest.fixture
def no_layout_template(monkeypatch, tmp_path_factory):
    monkeypatch.setattr(layout_scaffolder, "SHARED_TEMPLATE_ROOT", str(tmp_path_factory.mktemp("empty")))


@pytest.mark.parametrize("build", [admin_scaffolder.build_admin, auth_scaffolder.build_auth])
def test_a_missing_template_writes_nothing(project, no_layout_template, build):
    before = _files(project)
    with pytest.raises(FileNotFoundError):
        build(str(project))
    assert _files(project) == before


def test_a_conflict_anywhere_writes_nothing(project):
    last = sorted(admin_scaffolder._template_files())[-1][: -len(admin_scaffolder.STUB_SUFFIX)]
    os.makedirs(os.path.dirname(project / last), exist_ok=True)
    (project / last).write_text("mine")
    before = _files(project)
    with pytest.raises(FileExistsError):
        admin_scaffolder.build_admin(str(project))
    assert _files(project) == before
    assert (project / last).read_text() == "mine"


def test_auth_then_admin_both_succeed_on_a_fresh_project(project):
    auth_scaffolder.build_auth(str(project))
    result = admin_scaffolder.build_admin(str(project))
    assert result["already_configured"] is False


class _FakeTable:
    """A `roles` table double: just enough query builder for the seed migration."""

    def __init__(self, rows: list) -> None:
        self.rows, self._slug = rows, None

    def where(self, column: str, value: str) -> "_FakeTable":
        self._slug = value
        return self

    def first(self) -> dict | None:
        return next((row for row in self.rows if row["slug"] == self._slug), None)

    def insert(self, row: dict) -> None:
        self.rows.append(row)


def test_make_admin_ships_the_admin_role_it_tells_you_to_assign(project, monkeypatch):
    import importlib.util

    result = admin_scaffolder.build_admin(str(project))
    seed = next(path for name, path in result["files"].items() if name.endswith("seed_admin_role.py"))
    spec = importlib.util.spec_from_file_location("seed_admin_role", seed)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rows: list = []
    monkeypatch.setattr(module, "DB", type("FakeDB", (), {"table": staticmethod(lambda name: _FakeTable(rows))}))
    module.up()
    module.up()
    assert [row["slug"] for row in rows] == ["admin"]
