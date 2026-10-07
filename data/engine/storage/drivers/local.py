"""Local Filesystem Storage Driver for Craft Framework."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import mimetypes
import os
import shutil
from pathlib import Path
from typing import Any, BinaryIO, Optional, Union

from engine.storage.paths import normalize_key


class LocalStorageDriver:
    """Storage driver for local and public filesystem disks."""

    def __init__(self, root: str, url: str = "/storage"):
        self.root = Path(root).resolve()
        self.base_url = url.rstrip("/")
        self.root.mkdir(parents=True, exist_ok=True)

    def _full_path(self, path: str) -> Path:
        full = (self.root / normalize_key(path)).resolve()
        if not str(full).startswith(str(self.root)):
            # `normalize_key` already refuses a `..` segment; this is the
            # second lock, for a symlink or a root that moved under us.
            raise ValueError(f"Path traversal detected: {path}")
        return full

    def put(self, path: str, contents: Union[str, bytes, BinaryIO], **kwargs: Any) -> bool:
        target = self._full_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)

        if hasattr(contents, "read") and callable(contents.read):
            raw = contents.read()
            if isinstance(raw, str):
                raw = raw.encode("utf-8")
        elif isinstance(contents, str):
            raw = contents.encode("utf-8")
        elif isinstance(contents, (bytes, bytearray)):
            raw = bytes(contents)
        else:
            raise TypeError(f"Unsupported contents type: {type(contents)}")

        with open(target, "wb") as f:
            f.write(raw)
        return True

    def get(self, path: str) -> Optional[bytes]:
        target = self._full_path(path)
        if not target.exists() or not target.is_file():
            return None
        with open(target, "rb") as f:
            return f.read()

    def get_text(self, path: str, encoding: str = "utf-8") -> Optional[str]:
        raw = self.get(path)
        return raw.decode(encoding) if raw is not None else None

    def exists(self, path: str) -> bool:
        target = self._full_path(path)
        return target.exists() and target.is_file()

    def delete(self, path: str) -> bool:
        target = self._full_path(path)
        if target.exists() and target.is_file():
            target.unlink()
            return True
        return False

    def size(self, path: str) -> int:
        target = self._full_path(path)
        return target.stat().st_size if target.exists() else 0

    def mime_type(self, path: str) -> str:
        target = self._full_path(path)
        mime, _ = mimetypes.guess_type(str(target))
        return mime or "application/octet-stream"

    def url(self, path: str) -> str:
        # The key is validated before it reaches a link: a `..` rendered into a
        # URL is a traversal a browser, not the filesystem, would resolve.
        return f"{self.base_url}/{normalize_key(path)}"

    def temporary_url(self, path: str, minutes: int = 5) -> str:
        # Local disks return standard URL (or signed token if configured)
        return self.url(path)
