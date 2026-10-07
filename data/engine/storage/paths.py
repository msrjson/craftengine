"""Safe storage keys and the tenant-scoped disk decorator.

Category: Core Framework (Storage).
Relations:
  - Used by the local and S3 drivers and by `engine/storage/manager.py`.
References:
  - Guide: `documentation/storage.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

from typing import Any, Optional


def normalize_key(path: str) -> str:
    """Return the safe, relative storage key for `path`.

    A key that reaches a URL is rendered into a link, and a key that reaches a
    filesystem becomes a path; both allow a `..` or an absolute component to
    escape the directory the disk is meant to stay inside. Rejecting the unsafe
    shapes here - one place, used by every driver - is what keeps a stored
    filename from becoming a traversal.

    Raises:
        ValueError: `path` is empty, carries a scheme, a NUL byte, or a `..`
            segment.
    """
    if not isinstance(path, str) or not path.strip():
        raise ValueError("A storage path must be a non-empty string.")
    if "\x00" in path:
        raise ValueError("A storage path may not contain a NUL byte.")
    candidate = path.replace("\\", "/").strip()
    if "://" in candidate:
        raise ValueError(f"A storage path must be relative, not a URL: {path!r}.")
    segments = [segment for segment in candidate.split("/") if segment not in ("", ".")]
    if ".." in segments:
        raise ValueError(f"Path traversal detected: {path!r}.")
    return "/".join(segments)


class TenantScopedStorage:
    """Prefix every key with the bound tenant, so tenants share no namespace.

    A disk with `"tenant_scoped": true` keeps each tenant's files under
    `tenants/<tenant_id>/`. The path a caller passes is relative to the
    tenant's own directory, so tenant A cannot name tenant B's file, and a call
    with no tenant bound raises `TenantNotBoundError` rather than writing to a
    shared root - the same refusal a tenant-scoped query makes.
    """

    def __init__(self, driver: Any, prefix: str = "tenants") -> None:
        self.driver = driver
        self.prefix = prefix.strip("/")

    def _key(self, path: str) -> str:
        from engine.orm.tenancy import TenantManager

        tenant = TenantManager().id_or_fail()
        return "/".join(part for part in (self.prefix, tenant, normalize_key(path)) if part)

    def put(self, path: str, contents: Any, **kwargs: Any) -> bool:
        return self.driver.put(self._key(path), contents, **kwargs)

    def get(self, path: str) -> Optional[bytes]:
        return self.driver.get(self._key(path))

    def get_text(self, path: str, encoding: str = "utf-8") -> Optional[str]:
        raw = self.get(path)
        return raw.decode(encoding) if raw is not None else None

    def exists(self, path: str) -> bool:
        return self.driver.exists(self._key(path))

    def delete(self, path: str) -> bool:
        return self.driver.delete(self._key(path))

    def url(self, path: str) -> str:
        return self.driver.url(self._key(path))

    def temporary_url(self, path: str, minutes: int = 5) -> str:
        return self.driver.temporary_url(self._key(path), minutes=minutes)

    def size(self, path: str) -> int:
        return self.driver.size(self._key(path))

    def mime_type(self, path: str) -> str:
        return self.driver.mime_type(self._key(path))


__all__ = ["TenantScopedStorage", "normalize_key"]
