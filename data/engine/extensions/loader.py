"""Load and unload one extension's contributions into the running application.

Loading imports the extension's own files - never another extension's - and
hands each the extension's context:

- `provider.py` exposes `register(context)`: bindings, listeners, filters,
  proxy exposures;
- `routes.py` exposes `register(router)`: its routes, each tagged with the
  extension's slug so the kernel can refuse them while it cannot serve;
- `views/` becomes the `slug::` view namespace, or a theme layer for a theme.

The file locations come from the manifest the application's configured roots
produced; the engine never names an application package.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import importlib
import os
import sys
from types import ModuleType
from typing import Any

from engine.extensions.context import ExtensionContext, Guard
from engine.extensions.errors import ExtensionError
from engine.extensions.manifest import ExtensionKind, Manifest


class ExtensionLoader:
    """Wire extensions into the container, router, events, proxy and views.

    Args:
        app: The application container.
        guard: The error boundary handed to every context.
    """

    def __init__(self, app: Any, guard: Guard) -> None:
        self.app = app
        self._guard = guard
        self._contexts: dict[str, ExtensionContext] = {}
        self._routes_loaded: set[str] = set()

    def is_loaded(self, slug: str) -> bool:
        """Return whether the extension's contributions are live in this process."""
        return slug in self._contexts

    def load(self, manifest: Manifest) -> ExtensionContext:
        """Register every contribution of `manifest`; undo them all on failure.

        Raises:
            ExtensionError: `EXTENSION_BOOT_FAILED`, chained to what the
                extension raised.
        """
        context = ExtensionContext(self.app, manifest, self._guard)
        try:
            self._register_views(manifest, context)
            self._call_entry(manifest, "provider", context)
            self._register_routes(manifest)
        except Exception as error:  # noqa: BLE001 - any failure of third-party code
            context.unload()
            raise ExtensionError("EXTENSION_BOOT_FAILED", manifest.slug, type(error).__name__) from error
        self._contexts[manifest.slug] = context
        return context

    def unload(self, slug: str) -> None:
        """Revert the contributions of `slug`. Its routes stay registered but refused."""
        context = self._contexts.pop(slug, None)
        if context is not None:
            context.unload()

    def _register_views(self, manifest: Manifest, context: ExtensionContext) -> None:
        """Expose `views/` as a namespace, or as a theme layer for a theme."""
        if not manifest.has("views"):
            return
        view = self.app.make("view")
        directory = manifest.file("views")
        if manifest.kind is ExtensionKind.THEME:
            view.add_theme(manifest.slug, directory)
            context.on_unload(lambda: view.remove_theme(manifest.slug))
            return
        view.add_namespace(manifest.slug, directory)
        context.on_unload(lambda: view.remove_namespace(manifest.slug))

    def _call_entry(self, manifest: Manifest, name: str, context: ExtensionContext) -> None:
        """Call `register(context)` of the extension's `provider.py`, when it has one."""
        if not manifest.has(f"{name}.py"):
            return
        register = getattr(self._import(manifest, name), "register", None)
        if not callable(register):
            raise ExtensionError("EXTENSION_ENTRY_POINT_MISSING", manifest.slug, f"{name}.register")
        register(context)

    def _register_routes(self, manifest: Manifest) -> None:
        """Load `routes.py` once per process and tag every route it adds."""
        if manifest.slug in self._routes_loaded or not manifest.has("routes.py"):
            return
        register = getattr(self._import(manifest, "routes"), "register", None)
        if not callable(register):
            raise ExtensionError("EXTENSION_ENTRY_POINT_MISSING", manifest.slug, "routes.register")
        router = self.app.make("router")
        first_new = len(router.routes)
        register(router)
        for route in router.routes[first_new:]:
            route.module(manifest.slug)
        self._routes_loaded.add(manifest.slug)

    def _import(self, manifest: Manifest, name: str) -> ModuleType:
        """Import one of the extension's own files.

        Under the application root it is imported by its package path. Elsewhere
        (a vendored extension, a fixture) its directory becomes the package
        `craft_extensions.<slug>`. Either way the extension can import its own
        submodules, relatively or absolutely.
        """
        relative = os.path.relpath(manifest.file(name), self.app.base_path)
        parts = relative.split(os.sep)
        if parts[0] != ".." and all(part.isidentifier() for part in parts):
            return importlib.import_module(".".join(parts))
        return importlib.import_module(f"{_synthetic_package(manifest)}.{name}")


def _synthetic_package(manifest: Manifest) -> str:
    """Register the extension directory as the package `craft_extensions.<slug>`."""
    root = sys.modules.setdefault("craft_extensions", _package("craft_extensions", []))
    package = f"craft_extensions.{manifest.slug}"
    if package not in sys.modules:
        sys.modules[package] = _package(package, [manifest.path])
        setattr(root, manifest.slug, sys.modules[package])
    return package


def _package(name: str, path: list[str]) -> ModuleType:
    """Return an empty package module searching `path` for submodules."""
    module = ModuleType(name)
    module.__path__ = path
    return module


__all__ = ["ExtensionLoader"]
