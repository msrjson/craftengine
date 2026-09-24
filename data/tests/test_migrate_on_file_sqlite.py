"""`craft migrate` against a file-backed SQLite database in a generated project.

Every other suite runs on `:memory:`, where the whole application shares one
SQLite session and two connections can never contend. That is exactly why this
regression went unnoticed: the framework's zero-configuration default - a
freshly generated project on a database file - deadlocked itself, because the
console booted the application twice and the migration DDL went out on the
second application's connection while the migrator held its transaction on the
first one's.
"""

import json
import os
import subprocess
import sys

import pytest

import engine
from engine.cli import project_scaffolder

#: Directory holding the `engine` package, so a subprocess started in the
#: generated project can still import the framework under test.
ENGINE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(engine.__file__)))


def run_console(project: str, *arguments: str) -> subprocess.CompletedProcess:
    """Run the Craft console inside `project`, as a developer would.

    The defect lives in process-global bootstrap - the module-level
    application, the global container - so it only shows in a real console
    process, never in an in-process call.

    Args:
        project: Directory of the generated project.
        *arguments: Console arguments, e.g. `"migrate"`.

    Returns:
        The finished process, with output captured.
    """
    environment = dict(os.environ)
    environment.update(
        PYTHONPATH=ENGINE_PATH,
        APP_KEY="base64:" + "A" * 43 + "=",
        APP_ENV="testing",
        DB_CONNECTION="sqlite",
        DB_DATABASE=os.path.join(project, "storage", "database.sqlite"),
    )
    return subprocess.run(
        [sys.executable, "-c", "from engine.cli.app import main; main()", *arguments],
        cwd=project,
        env=environment,
        capture_output=True,
        text=True,
        timeout=180,
    )


@pytest.fixture()
def generated_project(tmp_path) -> str:
    """A bare project on disk, configured for a SQLite file."""
    target = str(tmp_path / "app")
    project_scaffolder.build_project(target)
    return target


class TestMigrateOnFileSqlite:
    """The zero-configuration path: a generated project on a SQLite file."""

    def test_migrate_applies_every_migration(self, generated_project):
        """`craft migrate` completes instead of failing "database is locked"."""
        result = run_console(generated_project, "migrate")

        assert result.returncode == 0, result.stdout + result.stderr
        assert "database is locked" not in result.stdout + result.stderr
        database = os.path.join(generated_project, "storage", "database.sqlite")
        assert os.path.isfile(database)

    def test_migrate_is_idempotent(self, generated_project):
        """A second run finds nothing pending, which proves the first committed."""
        run_console(generated_project, "migrate")

        result = run_console(generated_project, "migrate")

        assert result.returncode == 0, result.stdout + result.stderr
        assert "Nothing to migrate." in result.stdout

    def test_console_boots_one_application(self, generated_project):
        """Two applications mean two connections fighting over one file."""
        probe = (
            "import json;"
            "from engine.cli.app import get_app;"
            "import bootstrap.app as bootstrapped;"
            "print(json.dumps({"
            "'same_app': get_app() is bootstrapped.app,"
            "'same_db': get_app().make('db') is bootstrapped.app.make('db')}))"
        )
        environment = dict(os.environ)
        environment.update(PYTHONPATH=ENGINE_PATH, APP_ENV="testing", DB_CONNECTION="sqlite")

        result = subprocess.run(
            [sys.executable, "-c", probe],
            cwd=generated_project,
            env=environment,
            capture_output=True,
            text=True,
            timeout=180,
        )

        assert result.returncode == 0, result.stdout + result.stderr
        assert json.loads(result.stdout.strip().splitlines()[-1]) == {"same_app": True, "same_db": True}
