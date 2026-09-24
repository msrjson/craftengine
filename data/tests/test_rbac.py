"""RBAC enforcement — `has_role`, the Gate permission fallback, the
`role:<slug>`/`permission:<slug>` route middleware, and the seeded demo
accounts.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest
from starlette.testclient import TestClient

from bootstrap.app import app, asgi_app
from craft.facades import DB, Route


def _reset_rbac_tables():
    DB.statement("DELETE FROM permission_role")
    DB.statement("DELETE FROM role_user")
    DB.statement("DELETE FROM permissions")
    DB.statement("DELETE FROM roles")


@pytest.fixture
def rbac_user(migrated_database):
    from tests.support.models import Permission, Role, User

    DB.statement("DELETE FROM users WHERE email = 'rbac@craft.local'")
    _reset_rbac_tables()

    user = User.create(
        {"name": "RBAC", "email": "rbac@craft.local", "password": "s3cret", "is_admin": False}
    )
    role = Role.create({"name": "Editor", "slug": "editor"})
    permission = Permission.create({"name": "Edit Posts", "slug": "edit-posts"})

    DB.statement(
        "INSERT INTO role_user (user_id, role_id) VALUES (:user, :role)",
        {"user": user.get_attribute("id"), "role": role.get_attribute("id")},
    )
    DB.statement(
        "INSERT INTO permission_role (role_id, permission_id) VALUES (:role, :perm)",
        {"role": role.get_attribute("id"), "perm": permission.get_attribute("id")},
    )
    return user


class TestHasRole:
    def test_has_role_true_for_granted_role(self, rbac_user):
        assert rbac_user.has_role("editor") is True

    def test_has_role_false_for_ungranted_role(self, rbac_user):
        assert rbac_user.has_role("admin") is False


class TestGatePermissionFallback:
    def test_gate_falls_back_to_the_permission_system(self, rbac_user):
        from craft.auth.gate import GateManager

        gate = GateManager()
        # No ability closure, no policy registered for "edit-posts" — the
        # RBAC permission fallback must still grant it.
        assert gate.allows("edit-posts", rbac_user) is True

    def test_gate_still_denies_unknown_abilities_by_default(self, rbac_user):
        from craft.auth.gate import GateManager

        gate = GateManager()
        assert gate.allows("nonexistent-ability", rbac_user) is False

    def test_ability_closures_still_take_priority(self, rbac_user):
        from craft.auth.gate import GateManager

        gate = GateManager()
        gate.define("edit-posts", lambda user: False)
        # Even though the user *has* the permission, an explicit closure wins.
        assert gate.allows("edit-posts", rbac_user) is False

    def test_gate_tolerates_users_without_has_permission(self):
        from craft.auth.gate import GateManager

        gate = GateManager()
        assert gate.allows("edit-posts", object()) is False


class TestKernelAliasResolution:
    def test_role_alias_resolves_with_its_parameter(self):
        from craft.http.kernel import Kernel
        from craft.http.middleware import RequireRole

        kernel = Kernel(app)
        [instance] = kernel.resolve_route_middleware(["role:admin"])
        assert isinstance(instance, RequireRole)
        assert instance.role == "admin"

    def test_permission_alias_resolves_with_its_parameter(self):
        from craft.http.kernel import Kernel
        from craft.http.middleware import RequirePermission

        kernel = Kernel(app)
        [instance] = kernel.resolve_route_middleware(["permission:manage-users"])
        assert isinstance(instance, RequirePermission)
        assert instance.permission == "manage-users"

    def test_bare_alias_without_parameter_still_works(self):
        from craft.http.kernel import Kernel
        from craft.http.middleware import RequireAuth

        kernel = Kernel(app)
        [instance] = kernel.resolve_route_middleware(["auth"])
        assert isinstance(instance, RequireAuth)

    def test_unknown_alias_raises(self):
        from craft.http.kernel import Kernel

        kernel = Kernel(app)
        with pytest.raises(KeyError):
            kernel.resolve_route_middleware(["role"])  # no ":" separator, not a bare alias

        with pytest.raises(KeyError):
            kernel.resolve_route_middleware(["totally-unknown:param"])


@pytest.fixture(scope="module", autouse=True)
def rbac_routes(migrated_database):
    def only_admins(request):
        return {"ok": True}

    def only_editors(request):
        return {"ok": True}

    def token(request):
        return {"token": request.session().token()}

    def do_login(request):
        auth = app.make("auth")
        ok = auth.attempt(
            {"email": request.input("email"), "password": request.input("password")}
        )
        return {"ok": ok}

    Route.get("/t/rbac/admin-only", only_admins).middleware("role:admin").name("t.rbac.admin")
    Route.get("/t/rbac/edit-posts-only", only_editors).middleware(
        "permission:edit-posts"
    ).name("t.rbac.permission")
    Route.get("/t/rbac/token", token).name("t.rbac.token")
    Route.post("/t/rbac/login", do_login).name("t.rbac.login")
    yield


@pytest.fixture
def client():
    return TestClient(asgi_app)


def login(client, email: str, password: str) -> None:
    token = client.get("/t/rbac/token").json()["token"]
    client.post(
        "/t/rbac/login",
        data={"email": email, "password": password, "_token": token},
    )


class TestRequireRoleMiddleware:
    def test_guest_is_redirected(self, client):
        response = client.get("/t/rbac/admin-only", follow_redirects=False)
        assert response.status_code == 302

    def test_guest_gets_403_json_when_json_is_expected(self, client):
        response = client.get(
            "/t/rbac/admin-only", headers={"Accept": "application/json"}
        )
        assert response.status_code == 403

    def test_user_without_the_role_is_forbidden(self, client, rbac_user):
        login(client, "rbac@craft.local", "s3cret")
        response = client.get(
            "/t/rbac/admin-only", headers={"Accept": "application/json"}
        )
        assert response.status_code == 403

    def test_user_with_the_role_is_allowed(self, client, migrated_database):
        from tests.support.models import Role, User

        DB.statement("DELETE FROM users WHERE email = 'rbac-admin@craft.local'")
        user = User.create(
            {
                "name": "RBAC Admin",
                "email": "rbac-admin@craft.local",
                "password": "s3cret",
                "is_admin": False,
            }
        )
        role = Role.query().where("slug", "admin").first() or Role.create(
            {"name": "Administrator", "slug": "admin"}
        )
        DB.statement(
            "INSERT INTO role_user (user_id, role_id) VALUES (:user, :role)",
            {"user": user.get_attribute("id"), "role": role.get_attribute("id")},
        )

        login(client, "rbac-admin@craft.local", "s3cret")
        response = client.get("/t/rbac/admin-only")
        assert response.status_code == 200


class TestRequirePermissionMiddleware:
    def test_user_with_the_permission_is_allowed(self, client, rbac_user):
        login(client, "rbac@craft.local", "s3cret")
        response = client.get("/t/rbac/edit-posts-only")
        assert response.status_code == 200

    def test_user_without_the_permission_is_forbidden(self, client, migrated_database):
        from tests.support.models import User

        DB.statement("DELETE FROM users WHERE email = 'rbac-nobody@craft.local'")
        User.create(
            {
                "name": "Nobody",
                "email": "rbac-nobody@craft.local",
                "password": "s3cret",
                "is_admin": False,
            }
        )
        login(client, "rbac-nobody@craft.local", "s3cret")
        response = client.get(
            "/t/rbac/edit-posts-only", headers={"Accept": "application/json"}
        )
        assert response.status_code == 403


class TestPrivilegeLadder:
    """Three tiers, built by the test itself: a role each, and a permission
    that reaches the middle tier without reaching the bottom one.

    This is what the seeded demo accounts used to prove. The ladder is the
    engine behaviour — the resolver reading `role_user` and `permission_role`
    — so the test now builds it instead of depending on an application's
    seeder for its subjects.
    """

    @pytest.fixture
    def ladder(self, migrated_database):
        from tests.support.models import Permission, Role, User

        emails = ("plain@ladder.local", "manager@ladder.local", "boss@ladder.local")
        for email in emails:
            DB.statement("DELETE FROM users WHERE email = ?", [email])
        _reset_rbac_tables()

        users = {
            tier: User.force_create(
                {"name": tier, "email": email, "password": "s3cret", "type": tier}
            )
            for tier, email in zip(("plain", "manager", "boss"), emails, strict=True)
        }
        roles = {
            tier: Role.create({"name": tier.title(), "slug": slug})
            for tier, slug in (
                ("plain", "user"), ("manager", "tenant-manager"), ("boss", "admin")
            )
        }
        for tier, user in users.items():
            DB.statement(
                "INSERT INTO role_user (user_id, role_id) VALUES (:user, :role)",
                {"user": user.get_attribute("id"), "role": roles[tier].get_attribute("id")},
            )

        manage = Permission.create({"name": "Manage Users", "slug": "manage-users"})
        for tier in ("manager", "boss"):
            DB.statement(
                "INSERT INTO permission_role (role_id, permission_id) VALUES (:role, :perm)",
                {"role": roles[tier].get_attribute("id"), "perm": manage.get_attribute("id")},
            )

        yield users

        _reset_rbac_tables()
        for email in emails:
            DB.statement("DELETE FROM users WHERE email = ?", [email])

    def test_every_tier_carries_its_own_role(self, ladder):
        assert ladder["plain"].has_role("user") is True
        assert ladder["manager"].has_role("tenant-manager") is True
        assert ladder["boss"].has_role("admin") is True

    def test_a_permission_reaches_only_the_tiers_it_was_granted_to(self, ladder):
        assert ladder["manager"].has_permission("manage-users") is True
        assert ladder["boss"].has_permission("manage-users") is True
        assert ladder["plain"].has_permission("manage-users") is False


class TestSeededDemoAccountsHaveRoles:
    """DEMO-ONLY: about `database/seeders/UserSeeder.py` and the accounts it
    writes, not about the engine. `TestPrivilegeLadder` above covers the
    behaviour; delete this class with the sample application's seeders."""

    def test_all_three_demo_users_have_a_role(self, migrated_database):
        from database.seeders.UserSeeder import UserSeeder
        from database.seeders.FrameworkSeeder import FrameworkSeeder
        from tests.support.models import User

        UserSeeder().run()
        FrameworkSeeder().run()

        plain_user = User.query().where("email", "user@craft.local").first()
        tenant_user = User.query().where("email", "tenant@craft.local").first()
        admin_user = User.query().where("email", "admin@craft.local").first()

        assert plain_user.has_role("user") is True
        assert tenant_user.has_role("tenant-manager") is True
        assert admin_user.has_role("admin") is True

        # The ladder: tenant-manager sits strictly between user and admin.
        assert tenant_user.has_permission("manage-users") is True
        assert plain_user.has_permission("manage-users") is False

    def test_demo_users_get_their_privilege_columns(self, migrated_database):
        """`type` and `is_admin` are excluded from `User.fillable`, so seeding
        through `create()` drops them silently and yields three identical
        non-admin accounts. The seeder must use the trusted `force_create`
        path. Roles alone passing is not enough — `TenantMiddleware` keys off
        `type`, and `is_admin` gates the admin surface independently.
        """
        from database.seeders.UserSeeder import UserSeeder
        from tests.support.models import User

        UserSeeder().run()

        expected = {
            "user@craft.local": ("user", False),
            "tenant@craft.local": ("tenant", False),
            "admin@craft.local": ("admin", True),
        }
        for email, (user_type, is_admin) in expected.items():
            user = User.query().where("email", email).first()
            assert user is not None, f"{email} was not seeded"
            assert user.get_attribute("type") == user_type
            assert bool(user.get_attribute("is_admin")) is is_admin
            # The documented demo password must actually authenticate.
            assert user.check_password("craft") is True
            assert user.check_password("wrong") is False
