# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest
from craft.facades import DB, Config, Queue, Route
from craft.orm.model import Model
from craft.queue import Job
from starlette.testclient import TestClient

from tests.support.models import User
from bootstrap.app import app, asgi_app

# Global variable to test job execution
JOB_EXECUTED_VAL = None


@pytest.fixture(scope="module", autouse=True)
def framework_routes(migrated_database):
    """Throwaway routes, so the HTTP tests own what they request.

    The suite exercises the engine's HTTP stack, which must hold up in a
    project that declares no page of its own. Anything asserted against a
    route the sample application happens to publish is asserting the sample
    application.
    """
    from craft.http.response import JsonResponse

    def status(request):
        return JsonResponse({"status": "ok"})

    def plain(request):
        return "served"

    Route.get("/t/framework/status", status).name("t.framework.status")
    Route.get("/t/framework/plain", plain).name("t.framework.plain")
    Route.get("/t/framework/guarded", plain).middleware("auth").name("t.framework.guarded")
    yield


class TestJob(Job):
    def __init__(self, val=None):
        self.val = val

    def handle(self):
        global JOB_EXECUTED_VAL
        JOB_EXECUTED_VAL = self.val


def test_container_singleton():
    app.singleton("test.service", lambda c: object())
    inst1 = app.make("test.service")
    inst2 = app.make("test.service")
    assert inst1 is inst2


def test_config_repository():
    config = app.make("config")
    assert config.get("app.name", "Craft") == "Craft"


def test_validation():
    from craft.validation.validator import Validator

    rules = {"name": ["required", "string"], "age": ["required", "integer"]}

    # Valid data
    data1 = {"name": "Alice", "age": 30}
    validator1 = Validator(data1, rules)
    assert validator1.passes() is True

    # Invalid data
    data2 = {"name": "Bob", "age": "not-an-integer"}
    validator2 = Validator(data2, rules)
    assert validator2.passes() is False
    assert "age" in validator2.errors


def test_activerecord_and_relations():
    class Post(Model):
        __table__ = "posts"
        fillable = ["title", "body", "user_id", "published"]

        def user(self):
            return self.belongs_to(User, foreign_key="user_id")

        @classmethod
        def scope_published(cls, query):
            return query.where("published", True)

    from craft.migrations import Schema

    if not Schema.has_table("posts"):
        Schema.create(
            "posts",
            lambda t: (
                t.increments("id"),
                t.string("title"),
                t.text("body"),
                t.integer("user_id"),
                t.boolean("published").default(False),
                t.timestamps(),
            ),
        )

    # Clean up previous records if any (sqlite in-memory or storage)
    DB.statement("DELETE FROM posts")

    DB.statement("DELETE FROM users")

    # 1. Create a user
    user = User.create(
        {"name": "Jane Doe", "email": "jane@example.com", "password": "secret_password", "is_admin": False}
    )
    assert user.get_attribute("id") is not None
    assert user.get_attribute("name") == "Jane Doe"

    user.posts = lambda: user.has_many(Post, foreign_key="user_id")

    # 2. Create posts for user
    post1 = Post.create(
        {
            "title": "First Title",
            "body": "This is the post body content",
            "user_id": user.get_attribute("id"),
            "published": True,
        }
    )
    post2 = Post.create(
        {"title": "Second Title", "body": "Short text", "user_id": user.get_attribute("id"), "published": False}
    )

    # 3. Test HasMany Relationship
    user_posts = user.posts().get()
    assert len(user_posts) == 2
    assert any(p.get_attribute("title") == "First Title" for p in user_posts)

    # 4. Test BelongsTo Relationship
    author = post1.user().first()
    assert author is not None
    assert author.get_attribute("email") == "jane@example.com"

    # 5. Test ORM Scopes
    published_posts = Post.query().scope("published").get()
    assert len(published_posts) == 1
    assert published_posts[0].get_attribute("title") == "First Title"


def test_http_routes_are_served():
    client = TestClient(asgi_app)

    response = client.get("/t/framework/plain")
    assert response.status_code == 200
    assert response.text == "served"


def test_json_responses_carry_the_json_content_type():
    client = TestClient(asgi_app)

    response = client.get("/t/framework/status", headers={"Accept": "application/json"})
    assert response.status_code == 200
    assert "application/json" in response.headers.get("content-type", "")
    assert response.json()["status"] == "ok"


def test_the_sample_application_pages_render():
    """DEMO-ONLY: asserts the pages under `resources/views/` that ship with the
    sample application, not engine behaviour. Delete with the sample."""
    client = TestClient(asgi_app)

    assert client.get("/").status_code == 200

    response = client.get("/home")
    assert response.status_code == 200
    # Assert on structure, not on copy. The landing page is translatable, so its
    # visible text depends on the active locale and on seeded translations —
    # while the section itself is what proves the view rendered.
    assert 'id="features"' in response.text
    assert "<footer" in response.text

    assert client.get("/login").status_code == 200


def test_queue_json_serialization():
    global JOB_EXECUTED_VAL
    JOB_EXECUTED_VAL = None

    # Clear jobs table
    DB.statement("DELETE FROM jobs")

    # Set queue driver config to database dynamically
    config = app.make("config")
    original_driver = config.get("queue.connections.default.driver")
    config.set("queue.connections.default.driver", "database")

    try:
        # Push job to database queue
        job = TestJob(999)
        Queue.push(job)

        # Check that it is inserted in the jobs database table
        result = DB.statement("SELECT * FROM jobs")
        rows = result.fetchall()
        assert len(rows) == 1

        # Verify it has JSON payload (non-pickle)
        payload = rows[0].payload
        assert "job_class" in payload
        assert "TestJob" in payload
        assert "999" in payload  # checks val: 999 is stored

        # Run queue worker to process the job
        queue_mgr = app.make("queue")
        processed = queue_mgr.work("default")
        assert processed is True

        # Verify job was executed
        assert JOB_EXECUTED_VAL == 999

        # Verify job was deleted after execution
        result_after = DB.statement("SELECT COUNT(*) FROM jobs")
        assert result_after.fetchone()[0] == 0

    finally:
        # Restore original driver config
        config.set("queue.connections.default.driver", original_driver)


def test_queue_pop_reserves_the_job():
    # A claimed job must not be handed to a second worker, and a failed one
    # must come back with its claim released.
    DB.statement("DELETE FROM jobs")
    config = app.make("config")
    original_driver = config.get("queue.connections.default.driver")
    config.set("queue.connections.default.driver", "database")

    try:
        Queue.push(TestJob(1))
        queue_mgr = app.make("queue")

        record = queue_mgr.pop("default")
        assert record is not None
        assert record["attempts"] == 1
        assert queue_mgr.pop("default") is None  # reserved — not re-claimable

        # Releasing the reservation makes it claimable again.
        DB.statement("UPDATE jobs SET reserved_at = NULL WHERE id = ?", [record["id"]])
        again = queue_mgr.pop("default")
        assert again is not None
        assert again["attempts"] == 2
    finally:
        DB.statement("DELETE FROM jobs")
        config.set("queue.connections.default.driver", original_driver)


def _restore_translations_and_modules_schema(app):
    """Rebuild `translations`/`modules` to the real migrated shape.

    `test_ai_native_subsystems` replaces both tables with ad-hoc, reduced
    schemas to exercise DB-driven behavior in isolation. The shared in-memory
    database is session-scoped, so leaving them reduced broke every later
    test expecting the real schema — `test_subsystems_persistence.py` worked
    around this for its own `modules` usage with an identical rebuild, but
    anything running between this test and that one (alphabetically) still
    saw the reduced table. Fix at the source instead of adding another
    downstream workaround.
    """
    schema = app.make("schema")
    for table in ("translations", "modules"):
        DB.statement(f"DROP TABLE IF EXISTS {table}")
    schema.create_table(
        "translations",
        lambda t: (
            t.id(),
            t.string("key"),
            t.string("locale"),
            t.text("value"),
            t.timestamps(),
        ),
    )
    schema.create_table(
        "modules",
        lambda t: (
            t.id(),
            t.string("name"),
            t.string("slug").unique(),
            t.boolean("enabled").default(True),
            t.timestamps(),
        ),
    )


def test_ai_native_subsystems():
    from craft.facades import DB, Route
    from craft.support import __

    # Drop existing tables to avoid test contamination from global seeders
    DB.statement("DROP TABLE IF EXISTS translations")
    DB.statement("DROP TABLE IF EXISTS modules")

    try:
        _test_ai_native_subsystems_body(__, Config, DB, Route)
    finally:
        _restore_translations_and_modules_schema(app)


def _test_ai_native_subsystems_body(__, Config, DB, Route):
    # 1. Test Bilingual dynamic DB and config translations
    assert __("greeting") == "greeting"

    # Config is shared for the whole session, so anything set here has to be
    # cleared again — leaving `lang.pt.greeting` behind made every later test
    # that reads a pt translation see this value instead of the real one.
    Config.set("lang.pt.greeting", "Ola")
    try:
        assert __("greeting", "pt") == "Ola"
    finally:
        Config.set("lang.pt.greeting", None)

    # Create dummy translations table
    DB.statement("CREATE TABLE translations (key text, locale text, value text)")
    DB.statement("INSERT INTO translations (key, locale, value) VALUES ('welcome', 'en', 'Welcome to Craft')")
    DB.statement("INSERT INTO translations (key, locale, value) VALUES ('welcome', 'es', 'Bienvenido a Craft')")

    assert __("welcome", "en") == "Welcome to Craft"
    assert __("welcome", "es") == "Bienvenido a Craft"

    # 2. Test Dynamic Start/Stop Modules Routing
    # Register a new route dynamically under a module
    Route.get("/test-dynamic-module", lambda: "active").module("inventory")

    client = TestClient(asgi_app)

    # By default, modules.inventory.enabled defaults to True (config check fallback)
    response = client.get("/test-dynamic-module")
    assert response.status_code == 200
    assert response.text == "active"

    # Disable module via config
    Config.set("modules.inventory.enabled", False)
    response = client.get("/test-dynamic-module")
    assert response.status_code == 404

    # Re-enable module via config
    Config.set("modules.inventory.enabled", True)
    response = client.get("/test-dynamic-module")
    assert response.status_code == 200

    # Create modules table to test DB-driven start/stop
    DB.statement("DROP TABLE IF EXISTS modules")
    DB.statement("CREATE TABLE modules (slug text, enabled integer)")
    DB.statement("INSERT INTO modules (slug, enabled) VALUES ('inventory', 0)")

    # The router reads module state through the ModuleManager, which caches it
    # for `cache_ttl` seconds. Writing the table with raw SQL goes behind the
    # manager's back — exactly the "another process changed it" case — so the
    # cache has to be dropped explicitly. `enable()`/`disable()` do it on their
    # own.
    modules = app.make("module")
    modules.forget_cached_state("inventory")

    # Disabled in DB
    response = client.get("/test-dynamic-module")
    assert response.status_code == 404

    # Enabled in DB
    DB.statement("UPDATE modules SET enabled = 1 WHERE slug = 'inventory'")
    modules.forget_cached_state("inventory")
    response = client.get("/test-dynamic-module")
    assert response.status_code == 200
    assert response.text == "active"


def test_rbac_relationships_and_permissions():
    from craft.facades import DB

    from tests.support.models import Permission, Role, User

    # Clean tables
    DB.statement("DELETE FROM permission_role")
    DB.statement("DELETE FROM role_user")
    DB.statement("DELETE FROM permissions")
    DB.statement("DELETE FROM roles")
    DB.statement("DELETE FROM users")

    # Create admin user
    user = User.create(
        {"name": "Super User", "email": "superuser@example.com", "password": "secret_password", "is_admin": False}
    )

    # Create role
    admin_role = Role.create({"name": "Administrator", "slug": "admin"})

    # Create permission
    manage_users = Permission.create({"name": "Manage Users", "slug": "manage-users"})

    # Associate role to user
    DB.statement(
        "INSERT INTO role_user (user_id, role_id) VALUES (:user, :role)",
        {"user": user.get_attribute("id"), "role": admin_role.get_attribute("id")},
    )

    # Associate permission to role
    DB.statement(
        "INSERT INTO permission_role (role_id, permission_id) VALUES (:role, :perm)",
        {"role": admin_role.get_attribute("id"), "perm": manage_users.get_attribute("id")},
    )

    # Verify relationships
    user_roles = user.roles().get()
    assert user_roles.count() == 1
    assert user_roles.first().get_attribute("slug") == "admin"

    role_perms = user_roles.first().permissions().get()
    assert role_perms.count() == 1
    assert role_perms.first().get_attribute("slug") == "manage-users"

    # Verify user has permission check
    assert user.has_permission("manage-users") is True
    assert user.has_permission("non-existing-permission") is False


def test_post_quantum_security():
    import secrets

    from craft.facades import PQC
    from craft.security.pqc import WOTS

    # 1. Test WOTS post-quantum signature verification
    seed = secrets.token_bytes(32)
    wots = WOTS(seed)
    pub_key = wots.get_public_key()

    message = b"Securing critical system transaction data"
    signature = wots.sign(message)

    # Valid signature checks out
    assert WOTS.verify(message, signature, pub_key) is True

    # Modified message fails validation
    assert WOTS.verify(b"tampered", signature, pub_key) is False

    # 2. Test Facade Hybrid classic + PQC token signatures
    secret_key = "classical_super_secret"
    payload = '{"user_id":123,"role":"admin"}'

    # Sign a hybrid token (Classical HMAC + WOTS post-quantum hash-based)
    token = PQC.sign_token(payload, secret_key, seed)

    # Valid token passes verification
    assert PQC.verify_token(token, secret_key, pub_key) is True

    # Tampering with payload fails validation
    parts = token.split(".")
    tampered_token = f"{parts[0] + 'extra'}.{parts[1]}.{parts[2]}"
    assert PQC.verify_token(tampered_token, secret_key, pub_key) is False

    # Tampering with classical signature fails validation
    tampered_classic = f"{parts[0]}.wrong_signature.{parts[2]}"
    assert PQC.verify_token(tampered_classic, secret_key, pub_key) is False

    # Tampering with post-quantum signature fails validation
    tampered_pqc = f"{parts[0]}.{parts[1]}.{'f' * len(parts[2])}"
    assert PQC.verify_token(tampered_pqc, secret_key, pub_key) is False


def test_captcha_security():
    from craft.facades import Captcha
    from craft.security.captcha import Captcha as CaptchaClass

    # Mock Session and Request to test generation and validation isolation
    class MockSession(dict):
        def put(self, key, value):
            self[key] = value

        def forget(self, key):
            if key in self:
                del self[key]

    class MockRequest:
        def __init__(self):
            self._session = MockSession()

        def session(self):
            return self._session

    request = MockRequest()

    # Generate CAPTCHA
    code = Captcha.generate(request)
    assert len(code) == 5
    assert request.session().get("captcha_code") == code

    # The legacy helper renders an image: the code is never readable from markup
    html = CaptchaClass.get_obfuscated_html(code)
    assert html.startswith("<img") and "data:image/png;base64," in html
    assert code not in html

    # Valid validation resolves to true and clears key to prevent reuse
    assert Captcha.validate(request, code) is True
    assert request.session().get("captcha_code") is None

    # Invalid input is rejected
    code2 = Captcha.generate(request)
    assert Captcha.validate(request, "WRONG") is False
    assert request.session().get("captcha_code") is None  # cleared on validation attempt


def test_a_guest_is_redirected_away_from_a_guarded_route():
    from craft.facades import Auth

    Auth.logout()

    client = TestClient(asgi_app)
    response = client.get("/t/framework/guarded", follow_redirects=False)

    assert response.status_code == 302
    assert "/login" in response.headers.get("location", "")


def test_tenant_service_autowired_injection():
    """DEMO-ONLY: the three tenants asserted here are static data inside the
    sample application's `TenantService`. Container autowiring itself is
    covered by `tests/test_container.py`."""
    from app.Services.Tenant.TenantService import TenantService

    # Resolve service directly from the container via autowiring
    service = app.make(TenantService)

    assert isinstance(service, TenantService)
    assert len(service.get_active_tenants()) == 3
    assert service.get_active_tenants()[0]["name"] == "Acme Global Corporation"


def test_database_logging_middleware():
    """DEMO-ONLY: `DatabaseLoggingMiddleware` lives in the sample application
    (`app/Http/Middleware/`) and is wired in `bootstrap/app.py`; the engine
    ships no such middleware."""
    from tests.support.models import SystemLog

    # 1. Clean existing logs
    SystemLog.query().delete()

    # 2. Make an HTTP request to populate a connection log
    client = TestClient(asgi_app)
    response = client.get("/t/framework/plain")
    assert response.status_code == 200

    # 3. Retrieve system logs and verify a connection entry exists
    logs = SystemLog.query().get()
    assert len(logs) >= 1
    assert "Connection established" in logs[0].get_attribute("message")
    assert "GET" in logs[0].get_attribute("message")
    assert "/t/framework/plain" in logs[0].get_attribute("message")


def test_query_splitting_read_write_replicas():
    import os

    from craft.orm.db import DatabaseManager

    from tests.support.models import User

    # 1. Setup temporary sqlite files
    write_db = "storage/test_write.sqlite"
    read_db = "storage/test_read.sqlite"

    # Clean up any leftover files
    for db_file in [write_db, read_db]:
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
            except Exception:
                pass

    config = app.make("config")

    # Save original database connection config
    orig_default = config.get("database.default")

    # Configure test connection
    config.set(
        "database.connections.test_split",
        {
            "driver": "sqlite",
            "write": {
                "database": write_db,
            },
            "read": {
                "database": read_db,
            },
        },
    )

    config.set("database.default", "test_split")

    # Instantiate and boot a custom DatabaseManager
    db_mgr = DatabaseManager(app)
    db_mgr.boot()

    # Create users table in both databases
    create_sql = """
    CREATE TABLE users (
        id TEXT PRIMARY KEY,
        name TEXT,
        email TEXT,
        password TEXT,
        is_admin BOOLEAN,
        created_at TEXT,
        updated_at TEXT
    )
    """
    db_mgr.statement(create_sql, read=False)  # write db
    db_mgr.statement(create_sql, read=True)  # read db

    # Swap the container's "db" resolution and DB facade cache to our db_mgr
    orig_db = app.make("db")
    app.instance("db", db_mgr)
    DB._swap(db_mgr)

    try:
        # Create a user via Active Record (routes to write db)
        user = User.create(
            {
                "name": "Replica Test User",
                "email": "replica@example.com",
                "password": "secretpassword",
                "is_admin": False,
            }
        )

        # Verify it was written successfully
        assert user.get_attribute("id") is not None

        # Verify read operations (via QueryBuilder or User.query().get()) route to read replica (which is empty)
        read_users = User.query().get()
        assert len(read_users) == 0

        # Verify read operations (via User.find(id)) route to read replica (returns None)
        assert User.find(user.get_attribute("id")) is None

        # Insert same user record explicitly into read db to verify the model does find it if present
        # Using raw statement with read=True to seed the read DB
        db_mgr.statement(
            "INSERT INTO users (id, name, email, password, is_admin) VALUES (:id, :name, :email, :password, :is_admin)",
            {
                "id": user.get_attribute("id"),
                "name": "Replica Test User",
                "email": "replica@example.com",
                "password": "secretpassword",
                "is_admin": False,
            },
            read=True,
        )

        # Now querying read database should return the user
        read_users_after = User.query().get()
        assert len(read_users_after) == 1
        assert read_users_after[0].get_attribute("name") == "Replica Test User"

        # Querying by find should now return the user from read db
        found_user = User.find(user.get_attribute("id"))
        assert found_user is not None
        assert found_user.get_attribute("name") == "Replica Test User"

    finally:
        # Restore app container, facade cache, and config
        app.instance("db", orig_db)
        DB._clear_resolved()
        config.set("database.default", orig_default)
        # Clean up database files
        for db_file in [write_db, read_db]:
            if os.path.exists(db_file):
                try:
                    os.remove(db_file)
                except Exception:
                    pass


def test_framework_subsystems_modules_plugins_settings():
    from craft.facades import Module, Plugin, Setting

    # 1. Test ModuleManager
    Module.register("billing", "Billing Module", "Manages payments and invoices", "2.0.0")
    assert Module.is_enabled("billing") is True
    Module.disable("billing")
    assert Module.is_enabled("billing") is False
    Module.enable("billing")
    assert Module.is_enabled("billing") is True

    # 2. Test PluginManager
    hook_triggered = []
    Plugin.register("stripe_gateway", {"version": "1.5"})
    assert Plugin.is_active("stripe_gateway") is True
    Plugin.add_hook("payment_processed", lambda amount: hook_triggered.append(amount))
    Plugin.trigger_hook("payment_processed", 150.00)
    assert hook_triggered == [150.00]

    # 3. Test SettingManager
    assert Setting.get("FRAMEWORK_NAME", "Craft") == "Craft"
    Setting.set("site_title", "My Craft Application")
    assert Setting.get("site_title") == "My Craft Application"


def test_route_parameter_binding():
    from craft.exceptions import NotFoundHttpException
    from craft.http.response import Response

    def show_item(request, id=None):
        if id == "42":
            return Response("Item Show Test: 42")
        raise NotFoundHttpException("Item not found")

    Route.get("/test-param-binding/{id}", show_item)

    client = TestClient(asgi_app, raise_server_exceptions=False)
    res = client.get("/test-param-binding/42")
    assert res.status_code == 200
    assert "Item Show Test: 42" in res.text

    res_404 = client.get("/test-param-binding/999999")
    assert res_404.status_code == 404
