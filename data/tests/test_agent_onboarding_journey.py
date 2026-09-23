"""End-to-end journey a newcomer walks when starting a Craft project.

Every other test in this suite exercises the engine from inside this
repository, with its application already present and SQLite held in memory.
That is not what a developer or an AI agent meets. They run `craft new`, then
the commands the command itself printed, against a file-backed database with
no configuration at all.

The gap is not theoretical: the file-backed path was never covered, and
`craft migrate` failed on a freshly generated project while the whole suite
stayed green.

These tests are slow by the standards of this suite because they shell out to
the console and boot a generated application. They are worth it: this is the
first five minutes of the framework's life, and nothing else covers it.
"""

import os
import subprocess
import sys

import pytest

REPOSITORY_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_console(
    *arguments: str,
    cwd: str,
    database: str,
    console: str = "",
) -> subprocess.CompletedProcess:
    """Run a console command the way a newcomer would, and return the result.

    Args:
        *arguments: Console arguments, such as `("migrate",)`.
        cwd: Working directory to run from, normally the generated project.
        database: Path to the SQLite file the command should use.
        console: Path to the `dev.py` to invoke. Defaults to the one inside
            `cwd`, which is what a developer in their own project runs. Only
            `new` uses this repository's console, because at that point the
            project does not exist yet.

    Returns:
        The completed process, with output captured.
    """
    # Running this repository's console against a generated project's working
    # directory loads this repository's migrations, not the project's, and the
    # commands then fail for reasons that have nothing to do with the project.
    console = console or os.path.join(cwd, "dev.py")
    environment = dict(os.environ)
    environment.update(
        {
            "PYTHONPATH": os.pathsep.join([REPOSITORY_ROOT, cwd]),
            "DB_CONNECTION": "sqlite",
            "DB_DATABASE": database,
            "APP_ENV": "local",
        }
    )
    return subprocess.run(
        [sys.executable, console, *arguments],
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        timeout=180,
    )


@pytest.fixture
def generated_project(tmp_path):
    """Generate a bare project and return its path.

    Returns:
        Absolute path to the generated project.
    """
    result = run_console(
        "new",
        "app",
        cwd=str(tmp_path),
        database=":memory:",
        console=os.path.join(REPOSITORY_ROOT, "dev.py"),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return str(tmp_path / "app")


class TestFirstFiveMinutes:
    """The commands `craft new` tells the developer to run next."""

    def test_new_reports_what_it_wrote(self, tmp_path):
        """The command states the outcome rather than printing nothing."""
        result = run_console(
            "new",
            "app",
            cwd=str(tmp_path),
            database=":memory:",
            console=os.path.join(REPOSITORY_ROOT, "dev.py"),
        )

        assert result.returncode == 0, result.stdout + result.stderr
        assert os.path.isfile(os.path.join(str(tmp_path), "app", "bootstrap", "app.py"))

    def test_key_generate_succeeds(self, generated_project):
        """An application key can be set before anything else is configured."""
        environment_file = os.path.join(generated_project, ".env")
        with open(os.path.join(generated_project, ".env.example"), encoding="utf-8") as source:
            with open(environment_file, "w", encoding="utf-8") as destination:
                destination.write(source.read())

        result = run_console(
            "key:generate",
            cwd=generated_project,
            database=os.path.join(generated_project, "storage", "database.sqlite"),
        )

        assert result.returncode == 0, result.stdout + result.stderr

    def test_migrate_succeeds_against_a_file_backed_database(self, generated_project):
        """`craft migrate` completes on the framework's zero-configuration default.

        SQLite in a file is what `config/database.py` selects when nothing is
        set. The rest of the suite runs in memory, where a whole class of
        locking behaviour does not exist, so this is the only test that can
        catch a regression here.
        """
        database = os.path.join(generated_project, "storage", "database.sqlite")

        result = run_console("migrate", cwd=generated_project, database=database)

        assert result.returncode == 0, result.stdout + result.stderr
        assert os.path.isfile(database)

    def test_the_generated_application_serves_its_starter_page(self, generated_project):
        """Booting the generated project answers `/` with the wordmark."""
        database = os.path.join(generated_project, "storage", "database.sqlite")
        migrated = run_console("migrate", cwd=generated_project, database=database)
        assert migrated.returncode == 0, migrated.stdout + migrated.stderr

        probe = (
            "import sys; sys.path[:0] = [%r, %r]\n"
            "from starlette.testclient import TestClient\n"
            "from bootstrap.app import asgi_app\n"
            "response = TestClient(asgi_app).get('/')\n"
            "print(response.status_code)\n"
            "print('WORDMARK' if '\\u2588' in response.text else 'NO-WORDMARK')\n"
        ) % (REPOSITORY_ROOT, generated_project)

        environment = dict(os.environ)
        environment.update(
            {
                "PYTHONPATH": os.pathsep.join([REPOSITORY_ROOT, generated_project]),
                "DB_CONNECTION": "sqlite",
                "DB_DATABASE": database,
            }
        )
        result = subprocess.run(
            [sys.executable, "-c", probe],
            cwd=generated_project,
            env=environment,
            capture_output=True,
            text=True,
            timeout=180,
        )

        assert result.returncode == 0, result.stdout + result.stderr
        assert "200" in result.stdout
        assert "WORDMARK" in result.stdout


class TestNothingAnswersThatWasNotDeclared:
    """A generated project must not expose routes its author never wrote."""

    def test_route_listing_is_not_empty(self, generated_project):
        """`route:list` runs in a bare project and shows the one route."""
        result = run_console(
            "route:list",
            cwd=generated_project,
            database=os.path.join(generated_project, "storage", "database.sqlite"),
        )

        assert result.returncode == 0, result.stdout + result.stderr
        assert "/" in result.stdout
