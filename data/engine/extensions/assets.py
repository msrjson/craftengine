"""Serve each extension's `assets/` under `/extensions/<slug>/`.

One mount for every extension, asking the manager on each request: an
extension that is deactivated stops serving its files at once, in every
worker, with no route table to rebuild.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from starlette.responses import PlainTextResponse

from engine.http.static_files import CachedStaticFiles

#: URL prefix the mount answers on.
PREFIX = "/extensions"


class AssetSource(Protocol):
    """What the mount needs from the manager."""

    def assets_directory(self, slug: str) -> str | None:
        """Return the assets directory of a serving extension, else None."""


class ExtensionAssets:
    """ASGI application serving `<slug>/<path>` from that extension's `assets/`.

    Args:
        source: Returns the current asset source (the extension manager),
            resolved per request so a replaced manager is always the one asked.
    """

    def __init__(self, source: Callable[[], AssetSource]) -> None:
        self._source = source
        self._servers: dict[str, CachedStaticFiles] = {}

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        """Route the request to the extension's static server, or answer 404."""
        root_path = scope.get("root_path", "")
        path = scope.get("path", "")
        relative = path[len(root_path):] if root_path and path.startswith(root_path) else path
        slug, _, rest = relative.lstrip("/").partition("/")
        directory = self._source().assets_directory(slug) if slug and rest else None
        if directory is None:
            await PlainTextResponse("", status_code=404)(scope, receive, send)
            return
        server = self._servers.get(directory) or self._servers.setdefault(directory, CachedStaticFiles(directory=directory))
        await server({**scope, "root_path": f"{root_path}/{slug}" if root_path else f"{PREFIX}/{slug}", "path": path}, receive, send)


__all__ = ["ExtensionAssets", "PREFIX"]
