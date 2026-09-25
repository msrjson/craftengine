"""ScopeTenant.resolve() fails closed on an unrecognised, suspended, or
mismatched host instead of silently falling back to the authenticated user.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import uuid

import pytest

from craft.facades import DB
from craft.http.middleware import ScopeTenant
from craft.orm.model import Model
from craft.orm.tenancy import TenantHostMismatchError, TenantSuspendedError, UnboundTenantHostError


class _Request:
    def __init__(self, host: str) -> None:
        self._host = host

    def header(self, name: str):
        return self._host if name == "host" else None


def _container_for(migrated_database, user_tenant_id=None):
    class _User:
        @staticmethod
        def get_attribute(name):
            return user_tenant_id if name == "tenant_id" else None

    class _Auth:
        @staticmethod
        def user():
            return _User() if user_tenant_id is not None else None

    class _Container:
        @staticmethod
        def make(key):
            return _Auth() if key == "auth" else migrated_database.make(key)

    return _Container()


@pytest.fixture
def tenant_rows(migrated_database):
    """One active and one suspended tenant under slugs no other test uses.

    NR-02: the rows are kept. Unique slugs are what keep one test's tenants
    from answering another test's host.
    """
    suffix = uuid.uuid4().hex[:8]
    active_id = Model.new_uuid()
    suspended_id = Model.new_uuid()
    active_slug, suspended_slug = f"active-co-{suffix}", f"suspended-co-{suffix}"
    DB.table("tenants").insert(
        {"id": active_id, "name": "Active Co", "slug": active_slug, "status": "active"}
    )
    DB.table("tenants").insert(
        {"id": suspended_id, "name": "Suspended Co", "slug": suspended_slug, "status": "suspended"}
    )
    return {
        "active": active_id,
        "suspended": suspended_id,
        "active_host": f"{active_slug}.example.com",
        "suspended_host": f"{suspended_slug}.example.com",
    }


def test_an_unrecognised_subdomain_raises_404(migrated_database):
    middleware = ScopeTenant(app=migrated_database, require_isolation=False)
    with pytest.raises(UnboundTenantHostError) as excinfo:
        middleware.resolve(
            _Request(f"nobody-here-{uuid.uuid4().hex[:8]}.example.com"),
            _container_for(migrated_database),
        )
    assert excinfo.value.status_code == 404


def test_a_suspended_tenants_host_raises_403(tenant_rows, migrated_database):
    middleware = ScopeTenant(app=migrated_database, require_isolation=False)
    with pytest.raises(TenantSuspendedError) as excinfo:
        middleware.resolve(
            _Request(tenant_rows["suspended_host"]), _container_for(migrated_database)
        )
    assert excinfo.value.status_code == 403
    assert excinfo.value.params["tenant_id"] == tenant_rows["suspended"]


def test_an_active_tenants_host_resolves_normally(tenant_rows, migrated_database):
    middleware = ScopeTenant(app=migrated_database, require_isolation=False)
    resolved = middleware.resolve(
        _Request(tenant_rows["active_host"]), _container_for(migrated_database)
    )
    assert resolved == tenant_rows["active"]


def test_a_host_tenant_mismatched_with_the_session_raises_403(tenant_rows, migrated_database):
    """The host names one tenant; the signed-in session belongs to another."""
    middleware = ScopeTenant(app=migrated_database, require_isolation=False)
    other_tenant_id = "99999999-9999-9999-9999-999999999999"
    with pytest.raises(TenantHostMismatchError) as excinfo:
        middleware.resolve(
            _Request(tenant_rows["active_host"]),
            _container_for(migrated_database, user_tenant_id=other_tenant_id),
        )
    assert excinfo.value.status_code == 403
    assert excinfo.value.params["host_tenant_id"] == tenant_rows["active"]
    assert excinfo.value.params["session_tenant_id"] == other_tenant_id


def test_a_host_tenant_matching_the_session_resolves_normally(tenant_rows, migrated_database):
    middleware = ScopeTenant(app=migrated_database, require_isolation=False)
    resolved = middleware.resolve(
        _Request(tenant_rows["active_host"]),
        _container_for(migrated_database, user_tenant_id=tenant_rows["active"]),
    )
    assert resolved == tenant_rows["active"]


def test_a_reserved_subdomain_falls_back_to_the_session_tenant(migrated_database):
    """`www`/`app`/`api`/... never name a tenant - no 404 for those."""
    middleware = ScopeTenant(app=migrated_database, require_isolation=False)
    resolved = middleware.resolve(
        _Request("api.example.com"),
        _container_for(migrated_database, user_tenant_id="some-tenant-id"),
    )
    assert resolved == "some-tenant-id"


def test_a_single_segment_host_falls_back_to_the_session_tenant(migrated_database):
    """No subdomain at all (e.g. `localhost`) never raises."""
    middleware = ScopeTenant(app=migrated_database, require_isolation=False)
    resolved = middleware.resolve(_Request("localhost"), _container_for(migrated_database))
    assert resolved is None


@pytest.mark.parametrize("host", ["WWW.example.com", "Www.Example.Com", "API.example.com"])
def test_a_reserved_subdomain_is_matched_case_insensitively(host, migrated_database):
    """The Host header is case-insensitive (RFC 7230 Sec 5.4) - `WWW` must be
    treated the same as `www`, not fall through to the tenant lookup and 404.
    """
    middleware = ScopeTenant(app=migrated_database, require_isolation=False)
    resolved = middleware.resolve(
        _Request(host), _container_for(migrated_database, user_tenant_id="some-tenant-id")
    )
    assert resolved == "some-tenant-id"
