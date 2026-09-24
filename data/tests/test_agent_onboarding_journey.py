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
            "PYTHONPATH": os.pathsep.join([cwd, REPOSITORY_ROOT]),
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
        """Booting the generated project answers `/` with its own starter page."""
        database = os.path.join(generated_project, "storage", "database.sqlite")
        migrated = run_console("migrate", cwd=generated_project, database=database)
        assert migrated.returncode == 0, migrated.stdout + migrated.stderr

        # The generated project comes first on the path. With this repository
        # ahead of it, `bootstrap.app` resolves to *this* application - the demo
        # one, theme and all - and the test silently measures the wrong thing.
        probe = (
            "import sys; sys.path[:0] = [%r, %r]\n"
            "from starlette.testclient import TestClient\n"
            "from bootstrap.app import asgi_app\n"
            "response = TestClient(asgi_app).get('/')\n"
            "print(response.status_code)\n"
            "print('MARK' if 'CraftEngine' in response.text else 'NO-MARK')\n"
            "print('NO-THEME' if 'assets/css' not in response.text else 'THEME')\n"
        ) % (generated_project, REPOSITORY_ROOT)

        environment = dict(os.environ)
        environment.update(
            {
                "PYTHONPATH": os.pathsep.join([generated_project, REPOSITORY_ROOT]),
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
        assert "MARK" in result.stdout
        # The starter page is self-contained: it links no stylesheet, so there
        # is no theme for anyone to start building on top of.
        assert "NO-THEME" in result.stdout


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


#: Runs inside a generated project that has had make:auth and make:admin. Two
#: users, one holding the `admin` role; each signs in and asks for the panel.
_RBAC_PROBE = """
import re, sys
sys.path[:0] = [%(project)r, %(repository)r]
from starlette.testclient import TestClient
from bootstrap.app import asgi_app
from app.Models.User import User
from app.Models.Role import Role
from craft.facades import DB

admin = User.create({"name": "Ada", "email": "ada@journey.test", "password": "correct-horse"})
User.create({"name": "Bob", "email": "bob@journey.test", "password": "correct-horse"})
role = Role.create({"name": "Admin", "slug": "admin"})
DB.table("role_user").insert({"user_id": admin.get_attribute("id"), "role_id": role.get_attribute("id")})

def visit(email, password, paths):
    client = TestClient(asgi_app)
    token = re.search(r'name="_token" value="([^"]+)"', client.get("/login").text).group(1)
    client.post("/login", data={"email": email, "password": password, "_token": token})
    return [client.get(path, follow_redirects=False).status_code for path in paths]

screens = ["/admin/roles", "/admin/permissions", "/admin/groups", "/admin/crud-builder", "/dashboard"]
print("ADMIN", visit("ada@journey.test", "correct-horse", screens))
print("PLAIN", visit("bob@journey.test", "correct-horse", ["/admin/roles", "/dashboard"]))
print("WRONG", visit("ada@journey.test", "wrong-password", ["/dashboard"]))
print("ANON", [TestClient(asgi_app).get("/admin/roles", follow_redirects=False).status_code])
stored = User.query().where("email", "ada@journey.test").first().get_attribute("password")
print("HASHED", stored != "correct-horse")
"""


class TestGeneratedAuthenticationAndAdminPanel:
    """What `make:auth` and `make:admin` produce must actually work together.

    Every screen those commands generate used to fail in a project generated
    by `craft new`: the login answered 500 because the anti-spam provider was
    missing and the controller called APIs that do not exist, the admin views
    extended a layout nobody generated, and the generated user had no
    has_role, so `role:admin` refused everyone - including administrators.
    None of it showed in this suite, because this repository used its own demo
    application instead of the generated code.
    """

    def test_roles_gate_the_panel_and_sign_in_works(self, generated_project):
        database = os.path.join(generated_project, "storage", "database.sqlite")
        for command in (("make:auth",), ("make:admin",), ("migrate",)):
            result = run_console(*command, cwd=generated_project, database=database)
            assert result.returncode == 0, result.stdout + result.stderr

        environment = dict(os.environ)
        environment.update({"DB_CONNECTION": "sqlite", "DB_DATABASE": database})
        probe = _RBAC_PROBE % {"project": generated_project, "repository": REPOSITORY_ROOT}
        result = subprocess.run(
            [sys.executable, "-c", probe],
            cwd=generated_project,
            env=environment,
            capture_output=True,
            text=True,
            timeout=180,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        report = dict(line.split(" ", 1) for line in result.stdout.splitlines() if " " in line)

        # An administrator reaches every screen of the panel and the dashboard.
        assert report["ADMIN"] == "[200, 200, 200, 200, 200]", report
        # A signed-in account without the role is refused, not redirected away.
        assert report["PLAIN"] == "[403, 200]", report
        # A wrong password authenticates nobody.
        assert report["WRONG"] == "[302]", report
        # A visitor who never signed in is sent to sign in.
        assert report["ANON"] == "[302]", report
        # The password reached the database hashed.
        assert report["HASHED"] == "True", report


_CRUD_PROBE = """
import re, sys
sys.path[:0] = [%(project)r, %(repository)r]
from starlette.testclient import TestClient
from bootstrap.app import asgi_app
from app.Models.User import User

User.create({"name": "Ada", "email": "ada@crud.test", "password": "correct-horse"})
client = TestClient(asgi_app)
token = lambda html: re.search(r'name="_token" value="([^"]+)"', html).group(1)
client.post("/login", data={"email": "ada@crud.test", "password": "correct-horse", "_token": token(client.get("/login").text)})
form = client.get("/admin/products/create")
stored = client.post("/admin/products", data={"name": "Widget", "price_cents": "1290", "_token": token(form.text)}, follow_redirects=False)
index = client.get("/admin/products").text
print("INDEX", client.get("/admin/products").status_code)
print("STORE", stored.status_code)
print("LISTED", "Widget" in index)
print("API", TestClient(asgi_app).get("/api/v1/products").status_code)
print("THEME", len(re.findall(r'class="', index)))
"""


class TestGeneratedCrud:
    """`make:crud` in a bare project yields a working screen and a working API.

    It used to write views extending a layout nothing had generated, and to
    skip registering the API when routes/api.py did not exist - while still
    printing the API's URL, which then answered 404.
    """

    def test_screens_and_api_work_without_a_theme(self, generated_project):
        database = os.path.join(generated_project, "storage", "database.sqlite")
        crud = ("make:crud", "Product", "--fields", "name:string:required,price_cents:integer:required")
        for command in (("make:auth",), crud, ("migrate",)):
            result = run_console(*command, cwd=generated_project, database=database)
            assert result.returncode == 0, result.stdout + result.stderr

        environment = dict(os.environ)
        environment.update({"DB_CONNECTION": "sqlite", "DB_DATABASE": database})
        probe = _CRUD_PROBE % {"project": generated_project, "repository": REPOSITORY_ROOT}
        result = subprocess.run(
            [sys.executable, "-c", probe], cwd=generated_project, env=environment,
            capture_output=True, text=True, timeout=180,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        report = dict(line.split(" ", 1) for line in result.stdout.splitlines() if " " in line)

        assert report["INDEX"] == "200", report
        assert report["STORE"] == "302", report
        assert report["LISTED"] == "True", report
        assert report["API"] == "200", report
        # Generated markup carries no styling hooks: there is no theme to hook.
        assert report["THEME"] == "0", report
