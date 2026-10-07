"""Storage Manager for Craft Framework.

Category: Core Framework (Storage).
Relations:
  - Backs `craft.facades.Storage`.
  - Configured by `config/storage.py`.
References:
  - Guide: `documentation/storage.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

from typing import Any, BinaryIO, Dict, Optional, Union

from engine.storage.contracts import StorageDriver
from engine.storage.drivers.local import LocalStorageDriver
from engine.storage.drivers.s3 import S3StorageDriver
from engine.storage.paths import TenantScopedStorage


class StorageManager:
    """Storage filesystem manager resolving local and cloud disks."""

    def __init__(self, app: Optional[Any] = None):
        self.app = app
        self._disks: Dict[str, StorageDriver] = {}

    def _get_config(self) -> Dict[str, Any]:
        if self.app:
            try:
                cfg = self.app.make("config")
                return {
                    "default": cfg.get("storage.default", "local"),
                    "disks": cfg.get("storage.disks", {}),
                }
            except Exception:
                pass
        return {
            "default": "local",
            "disks": {
                "local": {"driver": "local", "root": "storage/app", "url": "/storage"},
                "public": {"driver": "local", "root": "storage/app/public", "url": "/storage"},
            },
        }

    def disk(self, name: Optional[str] = None) -> StorageDriver:
        """Resolve a storage disk driver by name or default."""
        cfg = self._get_config()
        disk_name = name or cfg.get("default", "local")

        if disk_name in self._disks:
            return self._disks[disk_name]

        disk_cfg = cfg.get("disks", {}).get(disk_name, {})
        driver_type = disk_cfg.get("driver", "local")

        if driver_type == "s3":
            instance = S3StorageDriver(disk_cfg)
        else:
            root = disk_cfg.get("root", "storage/app")
            url = disk_cfg.get("url", "/storage")
            instance = LocalStorageDriver(root=root, url=url)

        if disk_cfg.get("tenant_scoped"):
            # Wrap after the driver is built: the tenant prefix is a concern of
            # the disk, and it applies to local and S3 alike.
            instance = TenantScopedStorage(instance, prefix=disk_cfg.get("prefix", "tenants"))

        self._disks[disk_name] = instance
        return instance

    def set_disk(self, name: str, driver: StorageDriver) -> None:
        """Register a custom disk driver instance."""
        self._disks[name] = driver

    # Forward common operations to the default disk
    def put(self, path: str, contents: Union[str, bytes, BinaryIO], disk: Optional[str] = None, **kwargs: Any) -> bool:
        return self.disk(disk).put(path, contents, **kwargs)

    def get(self, path: str, disk: Optional[str] = None) -> Optional[bytes]:
        return self.disk(disk).get(path)

    def get_text(self, path: str, disk: Optional[str] = None, encoding: str = "utf-8") -> Optional[str]:
        d = self.disk(disk)
        if hasattr(d, "get_text"):
            return d.get_text(path, encoding=encoding)
        raw = d.get(path)
        return raw.decode(encoding) if raw is not None else None

    def exists(self, path: str, disk: Optional[str] = None) -> bool:
        return self.disk(disk).exists(path)

    def delete(self, path: str, disk: Optional[str] = None) -> bool:
        return self.disk(disk).delete(path)

    def url(self, path: str, disk: Optional[str] = None) -> str:
        return self.disk(disk).url(path)

    def temporary_url(self, path: str, minutes: int = 5, disk: Optional[str] = None) -> str:
        return self.disk(disk).temporary_url(path, minutes=minutes)

    def size(self, path: str, disk: Optional[str] = None) -> int:
        return self.disk(disk).size(path)

    def mime_type(self, path: str, disk: Optional[str] = None) -> str:
        return self.disk(disk).mime_type(path)
