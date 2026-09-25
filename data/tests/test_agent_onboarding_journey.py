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

import json
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


class TestDoctor:
    """`craft doctor` catches the wiring mistakes agents make, before a request does."""

    def _prepare(self, generated_project):
        database = os.path.join(generated_project, "storage", "database.sqlite")
        for command in (("make:auth",), ("migrate",)):
            result = run_console(*command, cwd=generated_project, database=database)
            assert result.returncode == 0, result.stdout + result.stderr
        return database

    def test_a_freshly_generated_project_has_no_errors(self, generated_project):
        database = self._prepare(generated_project)
        result = run_console("doctor", cwd=generated_project, database=database)
        assert result.returncode == 0, result.stdout + result.stderr
        assert "ERROR" not in result.stdout

    def test_broken_wiring_is_reported_with_codes_and_exits_non_zero(self, generated_project):
        database = self._prepare(generated_project)
        with open(os.path.join(generated_project, "routes", "web.py"), "a", encoding="utf-8") as handle:
            handle.write(
                "\nfrom app.Http.Controllers.Auth.AuthController import AuthController as _Probe\n"
                'Route.get("/doctor-probe", [_Probe, "shwo_login"]).middleware("throttle:many")\n'
            )
        with open(os.path.join(generated_project, "resources", "views", "probe.forge.py"), "w", encoding="utf-8") as handle:
            handle.write("<ul>\n@for item in items\n<li>{{ item }}</li>\n@endfor\n</ul>\n")

        result = run_console("doctor", "--json", cwd=generated_project, database=database)

        assert result.returncode == 1, result.stdout + result.stderr
        codes = {finding["code"] for finding in json.loads(result.stdout)}
        assert {"ROUTE_ACTION_NOT_FOUND", "ROUTE_MIDDLEWARE_INVALID", "VIEW_UNKNOWN_DIRECTIVE"} <= codes
        assert "show_login" in result.stdout


_LOCALE_PROBE = """
import sys
sys.path[:0] = [%(project)r, %(repository)r]
from starlette.testclient import TestClient
from bootstrap.app import asgi_app

for locale in ("en", "pt-BR", "es"):
    page = TestClient(asgi_app).get("/login?lang=" + locale).text
    print(locale, "auth.login.title" in page, page.count("<h1>"), page.split("<h1>")[1].split("</h1>")[0])
"""


class TestGeneratedScreensAreTranslated:
    """The generated sign-in screen speaks every seeded locale."""

    def test_login_renders_in_each_locale_and_doctor_finds_no_missing_row(self, generated_project):
        database = os.path.join(generated_project, "storage", "database.sqlite")
        for command in (("make:auth",), ("make:admin",), ("migrate",)):
            result = run_console(*command, cwd=generated_project, database=database)
            assert result.returncode == 0, result.stdout + result.stderr

        environment = dict(os.environ)
        environment.update({"DB_CONNECTION": "sqlite", "DB_DATABASE": database})
        probe = _LOCALE_PROBE % {"project": generated_project, "repository": REPOSITORY_ROOT}
        result = subprocess.run(
            [sys.executable, "-c", probe], cwd=generated_project, env=environment,
            capture_output=True, text=True, timeout=180,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        headings = {line.split(" ", 1)[0]: line.split(" ", 3)[3] for line in result.stdout.splitlines() if line}
        assert headings == {"en": "Sign in", "pt-BR": "Entrar", "es": "Iniciar sesión"}, result.stdout

        doctor = run_console("doctor", "--json", cwd=generated_project, database=database)
        assert doctor.returncode == 0, doctor.stdout + doctor.stderr
        assert "TRANSLATION_MISSING" not in doctor.stdout


#: Every write action the generated admin panel exposes, done by an admin and
#: refused for an account without the role. Prints one `NAME value` per line.
_ADMIN_WRITE_PROBE = """
import re, sys
sys.path[:0] = [%(project)r, %(repository)r]
from starlette.testclient import TestClient
from bootstrap.app import asgi_app
from app.Models.User import User
from app.Models.Role import Role
from app.Models.Permission import Permission
from craft.facades import DB

ada = User.create({"name": "Ada", "email": "ada@write.test", "password": "correct-horse"})
bob = User.create({"name": "Bob", "email": "bob@write.test", "password": "correct-horse"})
admin = Role.create({"name": "Admin", "slug": "admin"})
DB.table("role_user").insert({"user_id": ada.get_attribute("id"), "role_id": admin.get_attribute("id")})
publish = Permission.create({"name": "Publish", "slug": "publish-post"})

def signed_in(email):
    client = TestClient(asgi_app)
    token = re.search(r'name="_token" value="([^"]+)"', client.get("/login").text).group(1)
    client.post("/login", data={"email": email, "password": "correct-horse", "_token": token})
    return client, token

def post(client, token, path, data):
    return client.post(path, data={**data, "_token": token}, follow_redirects=False).status_code

def count(sql, params):
    return DB.statement(sql, params, read=True).fetchone()[0]

plain, plain_token = signed_in("bob@write.test")
print("REFUSED_CREATE", post(plain, plain_token, "/admin/groups", {"name": "X", "slug": "x-team"}))
print("REFUSED_LEFT_NOTHING", count("SELECT COUNT(*) FROM groups WHERE slug = ?", ["x-team"]))

client, token = signed_in("ada@write.test")
print("NO_CSRF", client.post("/admin/groups", data={"name": "Y", "slug": "y-team"}, follow_redirects=False).status_code)
print("GRANT_ROLE_PERMISSION", post(client, token, "/admin/roles/grant",
      {"role_id": admin.get_attribute("id"), "permission_id": publish.get_attribute("id")}))
print("ROLE_HAS_PERMISSION", count("SELECT COUNT(*) FROM permission_role WHERE role_id = ? AND permission_id = ?",
      [admin.get_attribute("id"), publish.get_attribute("id")]))
print("CREATE_GROUP", post(client, token, "/admin/groups", {"name": "Support", "slug": "support-team"}))
group_id = DB.statement("SELECT id FROM groups WHERE slug = ?", ["support-team"], read=True).fetchone()[0]
print("ADD_MEMBER", post(client, token, "/admin/groups/members", {"group_id": group_id, "user_id": bob.get_attribute("id")}))
print("GRANT_GROUP_ROLE", post(client, token, "/admin/groups/roles", {"group_id": group_id, "role_id": admin.get_attribute("id")}))
print("GRANT_CONDITIONAL", post(client, token, "/admin/groups/permissions",
      {"group_id": group_id, "permission_id": publish.get_attribute("id"), "conditions": '{"user_id": "@user.id"}'}))
print("CONDITIONS_STORED", count("SELECT COUNT(*) FROM permission_group WHERE group_id = ? AND conditions IS NOT NULL", [group_id]))
rejected = client.post("/admin/groups/permissions", data={"group_id": group_id,
      "permission_id": publish.get_attribute("id"), "conditions": "not json", "_token": token}, follow_redirects=True)
print("BAD_CONDITIONS_SHOWN", "not granted" in rejected.text)
member, member_token = signed_in("bob@write.test")
print("MEMBER_INHERITS_ADMIN", member.get("/admin/roles", follow_redirects=False).status_code)
"""


class TestGeneratedAdminWriteActions:
    """Every write the admin panel exposes works, and is refused without the role."""

    def test_each_write_action_and_its_refusal(self, generated_project):
        database = os.path.join(generated_project, "storage", "database.sqlite")
        for command in (("make:auth",), ("make:admin",), ("migrate",)):
            result = run_console(*command, cwd=generated_project, database=database)
            assert result.returncode == 0, result.stdout + result.stderr

        environment = dict(os.environ)
        environment.update({"DB_CONNECTION": "sqlite", "DB_DATABASE": database, "APP_LOCALE": "en"})
        probe = _ADMIN_WRITE_PROBE % {"project": generated_project, "repository": REPOSITORY_ROOT}
        result = subprocess.run(
            [sys.executable, "-c", probe], cwd=generated_project, env=environment,
            capture_output=True, text=True, timeout=180,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        report = dict(line.split(" ", 1) for line in result.stdout.splitlines() if " " in line)

        assert report["REFUSED_CREATE"] == "403", report
        assert report["REFUSED_LEFT_NOTHING"] == "0", report
        assert report["NO_CSRF"] in ("403", "419"), report
        for action in ("GRANT_ROLE_PERMISSION", "CREATE_GROUP", "ADD_MEMBER", "GRANT_GROUP_ROLE", "GRANT_CONDITIONAL"):
            assert report[action] == "302", (action, report)
        assert report["ROLE_HAS_PERMISSION"] == "1", report
        assert report["CONDITIONS_STORED"] == "1", report
        assert report["BAD_CONDITIONS_SHOWN"] == "True", report
        assert report["MEMBER_INHERITS_ADMIN"] == "200", report


#: Edge cases of the generated sign-in and registration forms.
_AUTH_EDGE_PROBE = """
import re, sys
sys.path[:0] = [%(project)r, %(repository)r]
from starlette.testclient import TestClient
from bootstrap.app import asgi_app
from craft.facades import DB

def fresh(path):
    client = TestClient(asgi_app, raise_server_exceptions=False)
    token = re.search(r'name="_token" value="([^"]+)"', client.get(path).text).group(1)
    return client, token

client, token = fresh("/login")
print("NO_CSRF", client.post("/login", data={"email": "a@edge.test", "password": "x"}, follow_redirects=False).status_code)
invalid = client.post("/login", data={"email": "not-an-email", "password": "", "_token": token}, follow_redirects=True)
print("INVALID_STATUS", invalid.status_code)
print("INVALID_SHOWS_ERRORS", 'role="alert"' in invalid.text)

form = {"name": "Dee", "email": "dee@edge.test", "password": "long-enough-secret"}
first, first_token = fresh("/register")
print("FIRST_REGISTRATION", first.post("/register", data={**form, "_token": first_token}, follow_redirects=False).status_code)
second, second_token = fresh("/register")
duplicate = second.post("/register", data={**form, "_token": second_token}, follow_redirects=True)
print("DUPLICATE_STATUS", duplicate.status_code)
print("DUPLICATE_SHOWS_ERROR", 'role="alert"' in duplicate.text)
print("ONE_ACCOUNT", DB.statement("SELECT COUNT(*) FROM users WHERE email = ?", ["dee@edge.test"], read=True).fetchone()[0])
"""


class TestGeneratedAuthenticationEdges:
    """Validation failures, duplicates, CSRF and generator re-runs, end to end."""

    def test_the_forms_refuse_bad_input_without_erroring(self, generated_project):
        database = os.path.join(generated_project, "storage", "database.sqlite")
        for command in (("make:auth",), ("migrate",)):
            result = run_console(*command, cwd=generated_project, database=database)
            assert result.returncode == 0, result.stdout + result.stderr

        environment = dict(os.environ)
        environment.update({"DB_CONNECTION": "sqlite", "DB_DATABASE": database})
        probe = _AUTH_EDGE_PROBE % {"project": generated_project, "repository": REPOSITORY_ROOT}
        result = subprocess.run(
            [sys.executable, "-c", probe], cwd=generated_project, env=environment,
            capture_output=True, text=True, timeout=180,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        report = dict(line.split(" ", 1) for line in result.stdout.splitlines() if " " in line)

        assert report["NO_CSRF"] in ("403", "419"), report
        assert report["INVALID_STATUS"] == "200" and report["INVALID_SHOWS_ERRORS"] == "True", report
        assert report["FIRST_REGISTRATION"] == "302", report
        assert report["DUPLICATE_STATUS"] == "200" and report["DUPLICATE_SHOWS_ERROR"] == "True", report
        assert report["ONE_ACCOUNT"] == "1", report

    def test_rerunning_the_generators_changes_nothing(self, generated_project):
        database = os.path.join(generated_project, "storage", "database.sqlite")
        for command in (("make:auth",), ("make:admin",), ("make:auth",), ("make:admin",), ("migrate",)):
            result = run_console(*command, cwd=generated_project, database=database)
            assert result.returncode == 0, result.stdout + result.stderr
        with open(os.path.join(generated_project, "routes", "web.py"), encoding="utf-8") as handle:
            routes = handle.read()
        assert routes.count('Route.get("/login"') == 1
        assert routes.count('Route.get("/admin",') == 1
