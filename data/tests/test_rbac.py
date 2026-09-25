"""RBAC enforcement — `has_role`, the Gate permission fallback, the
`role:<slug>`/`permission:<slug>` route middleware, and the seeded demo
accounts.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import uuid

import pytest
from starlette.testclient import TestClient

from bootstrap.app import app, asgi_app
from craft.facades import DB, Route

#: Nothing is deleted between tests (NR-02), so every role, permission and
#: user this module writes carries a suffix no other module or run shares.
_SUFFIX = uuid.uuid4().hex[:8]
ADMIN = f"admin-{_SUFFIX}"
EDITOR = f"editor-{_SUFFIX}"
EDIT_POSTS = f"edit-posts-{_SUFFIX}"


def _unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}@craft.local"


def _role(slug: str):
    """Return the role with `slug`, creating it on first use."""
    from tests.support.models import Role

    return Role.query().where("slug", slug).first() or Role.create({"name": slug, "slug": slug})


def _permission(slug: str):
    """Return the permission with `slug`, creating it on first use."""
    from tests.support.models import Permission

    return Permission.query().where("slug", slug).first() or Permission.create(
        {"name": slug, "slug": slug}
    )


@pytest.fixture
def rbac_user(migrated_database):
    from tests.support.models import User

    user = User.create(
        {"name": "RBAC", "email": _unique_email("rbac"), "password": "s3cret", "is_admin": False}
    )
    role = _role(EDITOR)
    permission = _permission(EDIT_POSTS)

    DB.statement(
        "INSERT INTO role_user (user_id, role_id) VALUES (:user, :role)",
        {"user": user.get_attribute("id"), "role": role.get_attribute("id")},
    )
    grant = {"role": role.get_attribute("id"), "perm": permission.get_attribute("id")}
    already_granted = DB.select(
        "SELECT 1 FROM permission_role WHERE role_id = :role AND permission_id = :perm", grant
    )
    if not already_granted:
        DB.statement(
            "INSERT INTO permission_role (role_id, permission_id) VALUES (:role, :perm)", grant
        )
    return user


class TestHasRole:
    def test_has_role_true_for_granted_role(self, rbac_user):
        assert rbac_user.has_role(EDITOR) is True

    def test_has_role_false_for_ungranted_role(self, rbac_user):
        assert rbac_user.has_role(ADMIN) is False


class TestGatePermissionFallback:
    def test_gate_falls_back_to_the_permission_system(self, rbac_user):
        from craft.auth.gate import GateManager

        gate = GateManager()
        # No ability closure, no policy registered for "edit-posts" — the
        # RBAC permission fallback must still grant it.
        assert gate.allows(EDIT_POSTS, rbac_user) is True

    def test_gate_still_denies_unknown_abilities_by_default(self, rbac_user):
        from craft.auth.gate import GateManager

        gate = GateManager()
        assert gate.allows("nonexistent-ability", rbac_user) is False

    def test_ability_closures_still_take_priority(self, rbac_user):
        from craft.auth.gate import GateManager

        gate = GateManager()
        gate.define(EDIT_POSTS, lambda user: False)
        # Even though the user *has* the permission, an explicit closure wins.
        assert gate.allows(EDIT_POSTS, rbac_user) is False

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

    Route.get("/t/rbac/admin-only", only_admins).middleware(f"role:{ADMIN}").name("t.rbac.admin")
    Route.get("/t/rbac/edit-posts-only", only_editors).middleware(
        f"permission:{EDIT_POSTS}"
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
        login(client, rbac_user.get_attribute("email"), "s3cret")
        response = client.get(
            "/t/rbac/admin-only", headers={"Accept": "application/json"}
        )
        assert response.status_code == 403

    def test_user_with_the_role_is_allowed(self, client, migrated_database):
        from tests.support.models import User

        email = _unique_email("rbac-admin")
        user = User.create(
            {"name": "RBAC Admin", "email": email, "password": "s3cret", "is_admin": False}
        )
        role = _role(ADMIN)
        DB.statement(
            "INSERT INTO role_user (user_id, role_id) VALUES (:user, :role)",
            {"user": user.get_attribute("id"), "role": role.get_attribute("id")},
        )

        login(client, email, "s3cret")
        response = client.get("/t/rbac/admin-only")
        assert response.status_code == 200


class TestRequirePermissionMiddleware:
    def test_user_with_the_permission_is_allowed(self, client, rbac_user):
        login(client, rbac_user.get_attribute("email"), "s3cret")
        response = client.get("/t/rbac/edit-posts-only")
        assert response.status_code == 200

    def test_user_without_the_permission_is_forbidden(self, client, migrated_database):
        from tests.support.models import User

        email = _unique_email("rbac-nobody")
        User.create({"name": "Nobody", "email": email, "password": "s3cret", "is_admin": False})
        login(client, email, "s3cret")
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
        """Build the three tiers with slugs and addresses unique to this test."""
        from tests.support.models import Permission, Role, User

        suffix = uuid.uuid4().hex[:8]
        slugs = {
            "plain": f"user-{suffix}", "manager": f"tenant-manager-{suffix}",
            "boss": f"admin-{suffix}", "permission": f"manage-users-{suffix}",
        }
        users = {
            tier: User.force_create({
                "name": tier, "email": f"{tier}-{suffix}@ladder.local",
                "password": "s3cret", "type": tier,
            })
            for tier in ("plain", "manager", "boss")
        }
        roles = {
            tier: Role.create({"name": slugs[tier], "slug": slugs[tier]}) for tier in users
        }
        for tier, user in users.items():
            DB.statement(
                "INSERT INTO role_user (user_id, role_id) VALUES (:user, :role)",
                {"user": user.get_attribute("id"), "role": roles[tier].get_attribute("id")},
            )

        manage = Permission.create({"name": slugs["permission"], "slug": slugs["permission"]})
        for tier in ("manager", "boss"):
            DB.statement(
                "INSERT INTO permission_role (role_id, permission_id) VALUES (:role, :perm)",
                {"role": roles[tier].get_attribute("id"), "perm": manage.get_attribute("id")},
            )

        return {"users": users, "slugs": slugs}

    def test_every_tier_carries_its_own_role(self, ladder):
        users, slugs = ladder["users"], ladder["slugs"]
        assert users["plain"].has_role(slugs["plain"]) is True
        assert users["manager"].has_role(slugs["manager"]) is True
        assert users["boss"].has_role(slugs["boss"]) is True

    def test_a_permission_reaches_only_the_tiers_it_was_granted_to(self, ladder):
        users, manage = ladder["users"], ladder["slugs"]["permission"]
        assert users["manager"].has_permission(manage) is True
        assert users["boss"].has_permission(manage) is True
        assert users["plain"].has_permission(manage) is False


class TestUserModelWithoutAuthorization:
    """A user model that cannot answer a role check must say so, not deny everyone."""

    class _PlainUser:
        pass

    @pytest.mark.parametrize("alias", ["role:admin", "permission:manage-users", "group:support"])
    def test_the_middleware_names_the_missing_mixin(self, alias):
        from craft.exceptions import MisconfigurationError
        from craft.http.kernel import Kernel

        [instance] = Kernel(app).resolve_route_middleware([alias])

        class _Auth:
            def user(self):
                return TestUserModelWithoutAuthorization._PlainUser()

        instance.app = type("_App", (), {"make": lambda self, key: _Auth()})()
        with pytest.raises(MisconfigurationError, match="AuthorizableMixin"):
            instance.handle(object(), lambda request: "passed")
