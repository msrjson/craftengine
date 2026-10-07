"""Storage keys are validated, and a tenant-scoped disk keeps tenants apart."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import uuid

import pytest

from craft.orm.tenancy import TenantManager, TenantNotBoundError
from craft.storage.drivers.local import LocalStorageDriver
from craft.storage.paths import TenantScopedStorage, normalize_key


@pytest.mark.parametrize("path", [
    "", "   ", "../secret", "a/../../b", "/etc/passwd/../../../x",
    "https://evil.example/x", "a\x00b",
])
def test_an_unsafe_key_is_refused(path):
    with pytest.raises(ValueError):
        normalize_key(path)


def test_a_safe_key_is_normalised():
    assert normalize_key("/documents/./hello.txt") == "documents/hello.txt"
    assert normalize_key("documents\\hello.txt") == "documents/hello.txt"


def test_the_local_url_refuses_a_traversal(tmp_path):
    driver = LocalStorageDriver(root=str(tmp_path / "app"), url="/storage")
    assert driver.url("documents/hello.txt") == "/storage/documents/hello.txt"
    with pytest.raises(ValueError):
        driver.url("../../etc/passwd")


def test_a_tenant_disk_needs_a_bound_tenant(tmp_path):
    driver = TenantScopedStorage(LocalStorageDriver(root=str(tmp_path / "app"), url="/storage"))
    TenantManager().bind(None)
    with pytest.raises(TenantNotBoundError):
        driver.put("hello.txt", "hi")


def test_one_tenant_never_reads_another_tenants_file(tmp_path):
    driver = TenantScopedStorage(LocalStorageDriver(root=str(tmp_path / "app"), url="/storage"))
    tenant_a, tenant_b = str(uuid.uuid4()), str(uuid.uuid4())

    TenantManager().bind(tenant_a)
    try:
        driver.put("hello.txt", "A's file")
        assert driver.get_text("hello.txt") == "A's file"
        assert (tmp_path / "app" / "tenants" / tenant_a / "hello.txt").exists()
    finally:
        TenantManager().bind(None)

    TenantManager().bind(tenant_b)
    try:
        # B asks for the same key and gets B's namespace, which is empty.
        assert driver.get("hello.txt") is None
        assert driver.exists("hello.txt") is False
        assert f"/tenants/{tenant_b}/hello.txt" in driver.url("hello.txt")
    finally:
        TenantManager().bind(None)


def test_the_manager_wraps_only_the_configured_disk(migrated_database):
    manager = migrated_database.make("storage")
    assert isinstance(manager.disk("tenant"), TenantScopedStorage)
    assert not isinstance(manager.disk("local"), TenantScopedStorage)
