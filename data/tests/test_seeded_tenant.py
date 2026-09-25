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
from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from craft.facades import DB
from craft.orm.model import Model


@dataclass(frozen=True)
class TenantFixture:
    """The identifiers one test's tenant and users were created under."""

    id: str
    slug: str
    host: str
    tenant_user_email: str
    unscoped_user_email: str


@pytest.fixture
def tenant(migrated_database) -> TenantFixture:
    """A tenant, a user that belongs to it, and a user that belongs to none.

    Every identifier is fresh per test, so it never collides with whatever
    the application seeds or an earlier test left. NR-02: nothing is deleted
    afterwards; uniqueness is the isolation. The id is a version 7 UUID on
    purpose: PostgreSQL rejects a malformed value in a `uuid` column.
    """
    from tests.support.models import User

    suffix = uuid.uuid4().hex[:8]
    slug = f"tenancy-fixture-{suffix}"
    created = TenantFixture(
        id=Model.new_uuid(),
        slug=slug,
        host=f"{slug}.example.com",
        tenant_user_email=f"tenant-fixture-{suffix}@craft.local",
        unscoped_user_email=f"unscoped-fixture-{suffix}@craft.local",
    )
    now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    DB.statement(
        "INSERT INTO tenants (id, name, slug, is_active, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [created.id, "Tenancy Fixture", created.slug, True, now, now],
    )
    User.force_create({
        "name": "Tenant User",
        "email": created.tenant_user_email,
        "password": "s3cret",
        "type": "tenant",
        "tenant_id": created.id,
    })
    User.force_create({
        "name": "Unscoped User",
        "email": created.unscoped_user_email,
        "password": "s3cret",
        "type": "user",
    })
    return created


def _request_for(host: str):
    """A minimal request exposing only the header the middleware reads."""

    class _Request:
        @staticmethod
        def header(name):
            return host if name == "host" else None

    return _Request()


def test_the_tenant_user_belongs_to_its_tenant(tenant):
    row = DB.select_one(
        "SELECT type, tenant_id FROM users WHERE email = ?", [tenant.tenant_user_email]
    )
    assert row["type"] == "tenant"
    assert str(row["tenant_id"]) == tenant.id


def test_an_unscoped_account_belongs_to_no_tenant(tenant):
    """An operator and a plain user are not tenant-scoped, and must not be."""
    row = DB.select_one(
        "SELECT tenant_id FROM users WHERE email = ?", [tenant.unscoped_user_email]
    )
    assert row["tenant_id"] is None


def test_the_tenant_id_is_a_valid_uuid7(tenant):
    """A `uuid` column rejects a malformed literal on PostgreSQL."""
    parsed = uuid.UUID(tenant.id)
    assert parsed.version == 7
    assert str(parsed) == tenant.id


def test_the_tenant_resolves_by_subdomain(tenant, migrated_database):
    """End of the chain: the host `<slug>.example.com` finds this tenant."""
    from craft.http.middleware import ScopeTenant

    middleware = ScopeTenant(app=migrated_database, require_isolation=False)
    assert str(middleware.tenant_for_subdomain(tenant.slug)) == tenant.id


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
        assert middleware.handle(_request_for(tenant.host), _next) == "served"
        assert str(seen["bound"]) == tenant.id
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

    Tenant.bind(tenant.id)
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
            return User.query().where("email", tenant.tenant_user_email).first()

    class _Container:
        @staticmethod
        def make(key):
            return _Auth() if key == "auth" else migrated_database.make(key)

    middleware = ScopeTenant(app=migrated_database, require_isolation=False)
    resolved = middleware.resolve(_request_for("www.example.com"), _Container())
    assert str(resolved) == tenant.id


