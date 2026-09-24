"""A tenant account has to be a coherent account.

A user carrying `type = "tenant"` who belongs to no tenant is worse than no
user at all: every scoped query it makes raises `TenantNotBoundError`, and
nothing resolves a tenant for it, by host or by user. The tests below build
that account themselves and drive `ScopeTenant` end to end — resolution by
subdomain, binding for the length of a request, failing closed on an unknown
host, and the fallback to the authenticated user's own tenant.

The final class is the one thing here that is about the sample application's
seeder rather than about the engine, and is marked as such.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import uuid
from datetime import datetime, timezone

import pytest

from craft.facades import DB

#: A tenant owned by this file alone, so it never collides with whatever the
#: application seeds. Version 7 on purpose: PostgreSQL rejects a malformed
#: value in a `uuid` column, and the id is a literal that nothing generates.
TENANT_ID = "01930000-0000-7000-8000-00000000f001"
TENANT_SLUG = "tenancy-fixture"
TENANT_HOST = f"{TENANT_SLUG}.example.com"
TENANT_USER_EMAIL = "tenant-fixture@craft.local"
UNSCOPED_USER_EMAIL = "unscoped-fixture@craft.local"


@pytest.fixture
def tenant(migrated_database):
    """A tenant, a user that belongs to it, and a user that belongs to none."""
    from tests.support.models import User

    now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    _cleanup()
    DB.statement(
        "INSERT INTO tenants (id, name, slug, is_active, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [TENANT_ID, "Tenancy Fixture", TENANT_SLUG, True, now, now],
    )
    User.force_create({
        "name": "Tenant User",
        "email": TENANT_USER_EMAIL,
        "password": "s3cret",
        "type": "tenant",
        "tenant_id": TENANT_ID,
    })
    User.force_create({
        "name": "Unscoped User",
        "email": UNSCOPED_USER_EMAIL,
        "password": "s3cret",
        "type": "user",
    })

    yield TENANT_ID

    _cleanup()


def _cleanup() -> None:
    DB.statement(
        "DELETE FROM users WHERE email IN (?, ?)",
        [TENANT_USER_EMAIL, UNSCOPED_USER_EMAIL],
    )
    DB.statement("DELETE FROM tenants WHERE id = ?", [TENANT_ID])


def _request_for(host: str):
    """A minimal request exposing only the header the middleware reads."""

    class _Request:
        @staticmethod
        def header(name):
            return host if name == "host" else None

    return _Request()


def test_the_tenant_user_belongs_to_its_tenant(tenant):
    row = DB.select_one(
        "SELECT type, tenant_id FROM users WHERE email = ?", [TENANT_USER_EMAIL]
    )
    assert row["type"] == "tenant"
    assert str(row["tenant_id"]) == TENANT_ID


def test_an_unscoped_account_belongs_to_no_tenant(tenant):
    """An operator and a plain user are not tenant-scoped, and must not be."""
    row = DB.select_one(
        "SELECT tenant_id FROM users WHERE email = ?", [UNSCOPED_USER_EMAIL]
    )
    assert row["tenant_id"] is None


def test_the_tenant_id_is_a_valid_uuid7(tenant):
    """A `uuid` column rejects a malformed literal on PostgreSQL."""
    parsed = uuid.UUID(TENANT_ID)
    assert parsed.version == 7
    assert str(parsed) == TENANT_ID


def test_the_tenant_resolves_by_subdomain(tenant, migrated_database):
    """End of the chain: the host `<slug>.example.com` finds this tenant."""
    from craft.http.middleware import ScopeTenant

    middleware = ScopeTenant(app=migrated_database, require_isolation=False)
    assert str(middleware.tenant_for_subdomain(TENANT_SLUG)) == TENANT_ID


def test_a_request_on_the_tenant_host_binds_it_for_the_whole_request(
    tenant, migrated_database
):
    """The middleware's actual job, not just its resolver.

    Everything else here checks that a tenant can be *found*. This checks that
    handling a request leaves it *bound*, which is what every scoped query and
    every generated policy then reads.
    """
    from craft.facades import Tenant
    from craft.http.middleware import ScopeTenant

    Tenant.clear()
    seen = {}

    def _next(request):
        seen["bound"] = Tenant.id()
        return "served"

    middleware = ScopeTenant(app=migrated_database, require_isolation=False)
    try:
        assert middleware.handle(_request_for(TENANT_HOST), _next) == "served"
        assert str(seen["bound"]) == TENANT_ID
    finally:
        Tenant.clear()
        migrated_database.make("db").release()


def test_an_unknown_host_never_reaches_the_next_middleware(tenant, migrated_database):
    """Fail closed: an unrecognised host must not inherit whatever was bound.

    Raises before `next_callable` ever runs (Slice 1) - stronger than the
    previous behaviour of quietly leaving no tenant bound and letting the
    request proceed, which left the door open for a downstream handler to read
    `current_tenant_id()` as `None` and mistake that for "no isolation needed."
    """
    from craft.facades import Tenant
    from craft.http.middleware import ScopeTenant
    from craft.orm.tenancy import UnboundTenantHostError

    class _Container:
        @staticmethod
        def make(key):
            if key == "auth":
                raise KeyError("nobody is authenticated")
            return migrated_database.make(key)

    Tenant.bind(TENANT_ID)
    seen = {}
    middleware = ScopeTenant(app=migrated_database, require_isolation=False)
    middleware.resolve = lambda request, container: ScopeTenant.resolve(
        middleware, request, _Container()
    )
    try:
        with pytest.raises(UnboundTenantHostError):
            middleware.handle(
                _request_for("nobody.example.com"),
                lambda r: seen.setdefault("bound", Tenant.id()),
            )
        assert "bound" not in seen, "the next middleware must never run for an unbound host"
    finally:
        Tenant.clear()
        migrated_database.make("db").release()


def test_the_tenant_resolves_from_the_authenticated_user(tenant, migrated_database):
    """And the other half: no useful host, so fall back to the user's own tenant."""
    from craft.http.middleware import ScopeTenant
    from tests.support.models import User

    class _Auth:
        @staticmethod
        def user():
            return User.query().where("email", TENANT_USER_EMAIL).first()

    class _Container:
        @staticmethod
        def make(key):
            return _Auth() if key == "auth" else migrated_database.make(key)

    middleware = ScopeTenant(app=migrated_database, require_isolation=False)
    resolved = middleware.resolve(_request_for("www.example.com"), _Container())
    assert str(resolved) == TENANT_ID


class TestTheSampleApplicationSeedsItsOwnTenant:
    """DEMO-ONLY: about `database/seeders/UserSeeder.py` and the demo accounts
    it writes. The engine behaviour it used to cover is in the tests above;
    delete this class with the sample application's seeders."""

    @pytest.fixture
    def seeded(self, migrated_database):
        """Run the idempotent seeder without altering existing demo records."""
        from database.seeders.UserSeeder import UserSeeder

        UserSeeder().run()
        return UserSeeder

    def test_the_demo_tenant_is_seeded(self, seeded):
        row = DB.select_one(
            "SELECT name, slug, is_active FROM tenants WHERE id = ?",
            [seeded.DEMO_TENANT_ID],
        )
        assert row is not None, "the tenant user has nothing to belong to"
        assert row["slug"] == seeded.DEMO_TENANT_SLUG
        assert row["is_active"] in (True, 1)

    def test_the_demo_tenant_user_belongs_to_it(self, seeded):
        row = DB.select_one(
            "SELECT type, tenant_id FROM users WHERE email = ?", ["tenant@craft.local"]
        )
        assert row["type"] == "tenant"
        assert str(row["tenant_id"]) == seeded.DEMO_TENANT_ID

    def test_the_other_demo_accounts_belong_to_no_tenant(self, seeded):
        for email in ("user@craft.local", "admin@craft.local"):
            row = DB.select_one("SELECT tenant_id FROM users WHERE email = ?", [email])
            assert row["tenant_id"] is None, f"{email} should not belong to a tenant"

    def test_the_seeder_is_idempotent(self, seeded):
        """Seeding twice must not duplicate the tenant — re-seeding is routine."""
        seeded().seed_demo_tenant()
        seeded().seed_demo_tenant()

        row = DB.select_one(
            "SELECT COUNT(*) AS total FROM tenants WHERE id = ?", [seeded.DEMO_TENANT_ID]
        )
        assert int(row["total"]) == 1
