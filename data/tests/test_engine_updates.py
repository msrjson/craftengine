"""Tests for the engine update notice, the panel screen and its generator (ADR 0005).

The unit tests drive `EngineUpdates` against local release archives (see
`test_engine_lifecycle.py`). The journey generates a project, adds the admin
panel, and walks `/admin/engine` over HTTP as an administrator: check, review
and apply an update, with the alert showing on the other panel pages.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from test_agent_onboarding_journey import REPOSITORY_ROOT, run_console
from test_engine_lifecycle import Releases, python_command, refusal, vendored_project

from engine.cli import engine_panel_scaffolder
from engine.lifecycle import EngineLifecycle, EngineUpdates
from engine.lifecycle.lock import load_lock
from engine.lifecycle.updates import NOTICE_CACHE_KEY


class MemoryCache:
    """The cache contract `EngineUpdates` needs, in memory."""

    def __init__(self) -> None:
        self.values: dict[str, Any] = {}

    def get(self, key: str) -> Any:
        return self.values.get(key)

    def put(self, key: str, value: Any, ttl: int | None = None) -> None:
        self.values[key] = value

    def forget(self, key: str) -> None:
        self.values.pop(key, None)


@pytest.fixture
def releases(tmp_path: Path) -> Releases:
    """Releases 4.4.2, 4.4.3 and 4.5.0, as in the lifecycle tests."""
    repository = Releases(tmp_path / "releases")
    base = {"__init__.py": "version = 1\n", "http/response.py": "response = 1\n"}
    repository.publish("v4.4.2-r00024", base)
    repository.publish("v4.4.3-r00025", {**base, "http/response.py": "response = 2\n"})
    repository.publish("v4.5.0-r00026", {**base, "http/response.py": "response = 3\n"})
    return repository


def updates_for(root: Path, releases: Releases) -> EngineUpdates:
    """Return the update service of a vendored project pinned to v4.4.2."""
    root.mkdir(parents=True, exist_ok=True)
    files = {"__init__.py": "version = 1\n", "http/response.py": "response = 1\n"}
    return EngineUpdates(vendored_project(root, releases, files), MemoryCache())


class TestNotice:
    """Checking, caching and reading the update notice."""

    def test_check_caches_a_notice_the_page_reads_without_the_network(self, tmp_path: Path, releases: Releases) -> None:
        updates = updates_for(tmp_path / "project", releases)
        notice = updates.check()
        assert (notice.pinned, notice.update, notice.newest, notice.available) == (
            "v4.4.2-r00024", "v4.4.3-r00025", "v4.5.0-r00026", True)
        (releases.root / "tags.json").unlink()
        assert updates.notice() == notice

    def test_no_notice_before_the_first_check(self, tmp_path: Path, releases: Releases) -> None:
        assert updates_for(tmp_path / "project", releases).notice() is None

    def test_a_project_without_a_lock_records_the_refusal(self, tmp_path: Path) -> None:
        notice = EngineUpdates(EngineLifecycle(tmp_path, ("4.4.2", "r00024")), MemoryCache()).check()
        assert (notice.error, notice.available) == ("ENGINE_LOCK_MISSING", False)

    def test_an_unreachable_source_records_the_refusal(self, tmp_path: Path, releases: Releases) -> None:
        updates = updates_for(tmp_path / "project", releases)
        (releases.root / "tags.json").unlink()
        assert updates.check().error == "ENGINE_SOURCE_UNREACHABLE"

    def test_overview_lists_pin_patches_and_drift(self, tmp_path: Path, releases: Releases) -> None:
        updates = updates_for(tmp_path / "project", releases)
        (tmp_path / "project/engine/http/response.py").write_text("local\n", encoding="utf-8")
        overview = updates.overview()
        assert (overview["pinned"], overview["mode"], overview["drift"]) == ("v4.4.2-r00024", "vendored", ["http/response.py"])
        assert EngineUpdates(EngineLifecycle(tmp_path, ("4.4.2", "r00024")), MemoryCache()).overview() == {
            "error": "ENGINE_LOCK_MISSING"}


class TestMoves:
    """Review and apply, as the panel calls them."""

    def test_review_changes_nothing_and_apply_moves_and_clears_the_notice(self, tmp_path: Path, releases: Releases) -> None:
        updates = updates_for(tmp_path / "project", releases)
        updates.check()
        assert updates.review("update").applied is False
        assert load_lock(tmp_path / "project").ref == "v4.4.2-r00024"
        report = updates.apply("update", "ada@example.test")
        assert (report.applied, report.target.ref) == (True, "v4.4.3-r00025")
        assert NOTICE_CACHE_KEY not in updates.cache.values

    def test_a_release_tag_target_is_an_upgrade(self, tmp_path: Path, releases: Releases) -> None:
        report = updates_for(tmp_path / "project", releases).review("v4.5.0-r00026")
        assert report.target.ref == "v4.5.0-r00026"

    def test_apply_runs_the_lock_verification_command_and_rolls_back(self, tmp_path: Path, releases: Releases) -> None:
        updates = updates_for(tmp_path / "project", releases)
        updates.lifecycle.set_verify_command(python_command("raise SystemExit(4)"))
        assert refusal(lambda: updates.apply("update", "ada")) == "ENGINE_VERIFY_FAILED"
        assert load_lock(tmp_path / "project").ref == "v4.4.2-r00024"
        assert not (tmp_path / "project/craft-engine.busy").exists()

    def test_only_one_move_runs_at_a_time(self, tmp_path: Path, releases: Releases) -> None:
        updates = updates_for(tmp_path / "project", releases)
        (tmp_path / "project/craft-engine.busy").write_text("", encoding="utf-8")
        assert refusal(lambda: updates.apply("update", "ada")) == "ENGINE_MOVE_IN_PROGRESS"
        assert load_lock(tmp_path / "project").ref == "v4.4.2-r00024"


class TestGenerator:
    """`make:engine-panel`."""

    def test_it_needs_the_admin_panel_shell(self, tmp_path: Path) -> None:
        with pytest.raises(engine_panel_scaffolder.EnginePanelRequiresAdmin):
            engine_panel_scaffolder.build_engine_panel(str(tmp_path))

    def test_it_writes_the_screen_once_and_appends_the_routes_once(self, tmp_path: Path) -> None:
        shell = tmp_path / engine_panel_scaffolder.PANEL_SHELL
        shell.parent.mkdir(parents=True)
        shell.write_text("", encoding="utf-8")
        first = engine_panel_scaffolder.build_engine_panel(str(tmp_path))
        second = engine_panel_scaffolder.build_engine_panel(str(tmp_path))
        routes = (tmp_path / "routes/web.py").read_text(encoding="utf-8")
        assert "app/Http/Controllers/Admin/EngineUpdateController.py" in first["files"]
        assert second["already_configured"] is True
        assert routes.count(engine_panel_scaffolder.ROUTES_TOKEN) == 1

    def test_every_template_is_packaged(self) -> None:
        pyproject = (Path(REPOSITORY_ROOT) / "pyproject.toml").read_text(encoding="utf-8")
        assert '"engine_panel_templates/**/*"' in pyproject
        assert len(engine_panel_scaffolder.template_files()) == 5


#: Runs inside a generated project with make:auth, make:admin and a lock that
#: points at local releases. An admin walks the screen; a plain user is refused.
_ENGINE_PANEL_PROBE = """
import re, sys
sys.path[:0] = [%(project)r, %(repository)r]
from starlette.testclient import TestClient
from bootstrap.app import asgi_app
from app.Models.User import User
from app.Models.Role import Role
from craft.facades import DB

admin = User.create({"name": "Ada", "email": "ada@engine.test", "password": "correct-horse"})
User.create({"name": "Bob", "email": "bob@engine.test", "password": "correct-horse"})
role = Role.query().where("slug", "admin").first()
DB.table("role_user").insert({"user_id": admin.get_attribute("id"), "role_id": role.get_attribute("id")})
token = lambda html: re.search(r'name="_token" value="([^"]+)"', html).group(1)

def signed_in(email):
    client = TestClient(asgi_app)
    client.post("/login", data={"email": email, "password": "correct-horse", "_token": token(client.get("/login").text)})
    return client

ada = signed_in("ada@engine.test")
before = ada.get("/admin/roles").text
screen = ada.get("/admin/engine")
print("SCREEN", screen.status_code)
print("ALERT_BEFORE", 'href="/admin/engine"' in before)
check = ada.post("/admin/engine/check", data={"_token": token(screen.text)}, follow_redirects=False)
print("CHECK", check.status_code)
print("ALERT_AFTER", 'href="/admin/engine"' in ada.get("/admin/roles").text)
review = ada.get("/admin/engine/review?target=update")
print("REVIEW", review.status_code, "v4.4.3-r00025" in review.text)
applied = ada.post("/admin/engine/apply", data={"target": "update", "_token": token(review.text)})
print("APPLY", applied.status_code, "v4.4.3-r00025" in open("Dockerfile").read())
print("NO_CSRF", ada.post("/admin/engine/apply", data={"target": "update"}, follow_redirects=False).status_code)
print("PLAIN", signed_in("bob@engine.test").get("/admin/engine", follow_redirects=False).status_code)
print("ANON", TestClient(asgi_app).get("/admin/engine", follow_redirects=False).status_code)
"""


class TestPanelJourney:
    """The screen `make:admin` now generates, walked over HTTP."""

    def test_an_admin_checks_reviews_and_applies_an_update(self, tmp_path: Path, releases: Releases) -> None:
        run_console("new", "app", cwd=str(tmp_path), database=":memory:", console=os.path.join(REPOSITORY_ROOT, "dev.py"))
        project = tmp_path / "app"
        database = str(project / "storage" / "database.sqlite")
        for command in (("make:auth",), ("make:admin",), ("migrate",)):
            result = run_console(*command, cwd=str(project), database=database)
            assert result.returncode == 0, result.stdout + result.stderr
        (project / "Dockerfile").write_text("ARG CRAFT_ENGINE_REF=v4.4.2-r00024\n", encoding="utf-8")
        EngineLifecycle(project, ("4.4.2", "r00024")).adopt(
            "v4.4.2-r00024", "package", pin_files=["Dockerfile"], source=releases.source, force=True)

        environment = {**os.environ, "DB_CONNECTION": "sqlite", "DB_DATABASE": database}
        probe = _ENGINE_PANEL_PROBE % {"project": str(project), "repository": REPOSITORY_ROOT}
        result = subprocess.run([sys.executable, "-c", probe], cwd=project, env=environment,
                                capture_output=True, text=True, timeout=180)
        assert result.returncode == 0, result.stdout + result.stderr
        report = dict(line.split(" ", 1) for line in result.stdout.splitlines() if " " in line)

        assert report["SCREEN"] == "200", report
        assert report["ALERT_BEFORE"] == "False", report
        assert report["CHECK"] == "302", report
        assert report["ALERT_AFTER"] == "True", report
        assert report["REVIEW"] == "200 True", report
        assert report["APPLY"] == "200 True", report
        assert report["NO_CSRF"] == "419", report
        assert report["PLAIN"] == "403", report
        assert report["ANON"] == "302", report
